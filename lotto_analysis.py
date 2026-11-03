
import json
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime

API = "https://www.dhlottery.co.kr/lt645/selectPstLt645Info.do"


def fetch_draw(round_no=None):
    url = API
    if round_no is not None:
        url += "?" + urllib.parse.urlencode({
            "srchLtEpsd": round_no
        })

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)

    rows = data.get("data", {}).get("list", [])
    if not rows:
        raise RuntimeError(f"회차 데이터 없음: {round_no}")

    row = rows[0]
    actual_round = int(row["ltEpsd"])

    if round_no is not None and actual_round != round_no:
        raise RuntimeError("요청 회차와 응답 회차가 다릅니다.")

    numbers = [int(row[f"tm{i}WnNo"]) for i in range(1, 7)]
    bonus = int(row["bnsWnNo"])

    if len(set(numbers + [bonus])) != 7:
        raise RuntimeError("당첨번호 중복 오류")

    if not all(1 <= n <= 45 for n in numbers + [bonus]):
        raise RuntimeError("당첨번호 범위 오류")

    return {
        "round": actual_round,
        "date": str(row["ltRflYmd"]),
        "numbers": sorted(numbers),
        "bonus": bonus
    }


def main():
    latest = fetch_draw()
    draws = [latest]

    for round_no in range(
        latest["round"] - 1,
        latest["round"] - 20,
        -1
    ):
        draws.append(fetch_draw(round_no))

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

    with open("lotto_report.html", "w", encoding="utf-8") as file:
        file.write("\n".join(html))

    print("최근 20회 분석 성공")
    print("최신 회차:", latest["round"])
    print("분석 회차 수:", len(draws))


if __name__ == "__main__":
    main()
