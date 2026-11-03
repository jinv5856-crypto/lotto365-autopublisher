
import json
import time
import random
import urllib.parse
import urllib.request
import urllib.error
from collections import Counter
from pathlib import Path

API = "https://www.dhlottery.co.kr/lt645/selectPstLt645Info.do"
CACHE = Path("lotto_draws.json")
REPORT = Path("lotto_report.html")
RETRIES = 3


def validate_draw(draw):
    round_no = int(draw["round"])
    numbers = sorted(int(n) for n in draw["numbers"])
    bonus = int(draw["bonus"])

    if round_no < 1:
        raise ValueError("잘못된 회차")

    if len(numbers) != 6:
        raise ValueError("당첨번호 개수 오류")

    if len(set(numbers + [bonus])) != 7:
        raise ValueError("당첨번호 중복 오류")

    if not all(1 <= n <= 45 for n in numbers + [bonus]):
        raise ValueError("당첨번호 범위 오류")

    return {
        "round": round_no,
        "date": str(draw["date"]),
        "numbers": numbers,
        "bonus": bonus
    }


def request_json(round_no=None):
    url = API

    if round_no is not None:
        url += "?" + urllib.parse.urlencode({
            "srchLtEpsd": round_no
        })

    for attempt in range(1, RETRIES + 1):
        try:
            print(
                f"서버 요청: {round_no or '최신'} "
                f"({attempt}/{RETRIES})",
                flush=True
            )

            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json"
                }
            )

            with urllib.request.urlopen(
                request, timeout=15
            ) as response:
                return json.load(response)

        except (
            urllib.error.URLError,
            TimeoutError,
            OSError
        ) as error:
            print(f"연결 실패: {error}", flush=True)

            if attempt == RETRIES:
                raise RuntimeError(
                    "동행복권 서버 연결 실패"
                ) from error

            time.sleep(attempt * 3 + random.random())


def fetch_draw(round_no=None):
    data = request_json(round_no)

    rows = data.get("data", {}).get("list", [])

    if not rows:
        raise RuntimeError(
            f"회차 데이터 없음: {round_no}"
        )

    row = rows[0]

    draw = validate_draw({
        "round": row["ltEpsd"],
        "date": row["ltRflYmd"],
        "numbers": [
            row[f"tm{i}WnNo"]
            for i in range(1, 7)
        ],
        "bonus": row["bnsWnNo"]
    })

    if round_no is not None:
        if draw["round"] != round_no:
            raise RuntimeError(
                "요청 회차와 응답 회차 불일치"
            )

    return draw


def load_cache():
    if not CACHE.exists():
        return {}

    with CACHE.open(encoding="utf-8") as file:
        data = json.load(file)

    result = {}

    for item in data:
        draw = validate_draw(item)
        result[draw["round"]] = draw

    return result


def save_cache(cache):
    data = [
        cache[key]
        for key in sorted(cache, reverse=True)
    ]

    with CACHE.open("w", encoding="utf-8") as file:
        json.dump(
            data, file,
            ensure_ascii=False,
            indent=2
        )


def collect_draws():
    cache = load_cache()

    try:
        latest = fetch_draw()
        cache[latest["round"]] = latest

    except Exception as error:
        print(f"최신 회차 조회 실패: {error}")

        if not cache:
            raise RuntimeError(
                "서버 접속 실패 및 저장 데이터 없음. "
                "분석과 발행을 중단합니다."
            ) from error

        raise RuntimeError(
            "최신 회차 확인 실패. "
            "오래된 분석의 자동 발행을 방지합니다."
        ) from error

    latest_round = latest["round"]
    draws = []

    for round_no in range(
        latest_round,
        latest_round - 20,
        -1
    ):
        if round_no in cache:
            draws.append(cache[round_no])
            continue

        time.sleep(1.5)

        draw = fetch_draw(round_no)
        cache[round_no] = draw
        draws.append(draw)

    if len(draws) != 20:
        raise RuntimeError("20회 데이터 부족")

    save_cache(cache)

    return draws


def main():
    draws = collect_draws()
    latest = draws[0]

    counts = Counter(
        number
        for draw in draws
        for number in draw["numbers"]
    )

    ranking = sorted(
        range(1, 46),
        key=lambda n: (-counts[n], n)
    )

    odd = sum(
        number % 2
        for draw in draws
        for number in draw["numbers"]
    )
    even = 120 - odd

    html = [
        "<meta charset='utf-8'>",
        "<h1>로또통계365 최신 당첨번호 분석</h1>",
        f"<h2>{latest['round']}회 당첨번호</h2>",
        f"<p>당첨번호: {', '.join(map(str, latest['numbers']))}</p>",
        f"<p>보너스 번호: {latest['bonus']}</p>",
        "<h2>최근 20회 출현 빈도 TOP 10</h2>",
        "<ol>"
    ]

    for number in ranking[:10]:
        html.append(
            f"<li>{number}번 - {counts[number]}회</li>"
        )

    html.extend([
        "</ol>",
        "<h2>홀짝 통계</h2>",
        f"<p>홀수: {odd}개 / 짝수: {even}개</p>",
        "<h2>번호별 출현 횟수</h2>",
        "<table border='1' cellpadding='8'>",
        "<tr><th>번호</th><th>출현 횟수</th></tr>"
    ])

    for number in range(1, 46):
        html.append(
            f"<tr><td>{number}</td><td>{counts[number]}</td></tr>"
        )

    html.extend([
        "</table>",
        "<p>과거 통계는 미래 당첨을 보장하지 않습니다.</p>"
    ])

    REPORT.write_text(
        "\n".join(html),
        encoding="utf-8"
    )

    print("최근 20회 분석 성공")
    print("최신 회차:", latest["round"])
    print("분석 회차 수:", len(draws))


if __name__ == "__main__":
    main()
