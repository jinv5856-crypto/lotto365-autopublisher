print("Lotto365 Analysis Ready")

import json
import urllib.request
from collections import Counter
from datetime import date, timedelta
from html import escape

API = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo="


def fetch_draw(round_no):
    request = urllib.request.Request(
        API + str(round_no),
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.load(response)

    if data.get("returnValue") != "success":
        return None

    numbers = [int(data[f"drwtNo{i}"]) for i in range(1, 7)]
    bonus = int(data["bnusNo"])

    if len(set(numbers + [bonus])) != 7:
        raise ValueError("Duplicate numbers")

    if not all(1 <= n <= 45 for n in numbers + [bonus]):
        raise ValueError("Invalid numbers")

    return {
        "round": round_no,
        "date": data["drwNoDate"],
        "numbers": sorted(numbers),
        "bonus": bonus
    }


def main():
    first_draw = date(2002, 12, 7)
    today = date.today()
    estimate = (today - first_draw).days // 7 + 1

    latest = None
    for round_no in range(estimate, max(0, estimate - 12), -1):
        latest = fetch_draw(round_no)
        if latest:
            break

    if not latest:
        raise RuntimeError("최신 당첨번호 조회 실패")

    draws = []
    for round_no in range(latest["round"], latest["round"] - 20, -1):
        draw = fetch_draw(round_no)
        if not draw:
            raise RuntimeError(f"{round_no}회 데이터 조회 실패")
        draws.append(draw)

    counts = Counter(
        n for draw in draws for n in draw["numbers"]
    )

    ranking = sorted(
        range(1, 46),
        key=lambda n: (-counts[n], n)
    )

    odd = sum(n % 2 for draw in draws for n in draw["numbers"])
    even = 120 - odd

    lines = [
        "<h2>로또통계365 최신 당첨번호 분석</h2>",
        f"<p>최신 회차: {latest['round']}회</p>",
        f"<p>추첨일: {escape(latest['date'])}</p>",
        f"<p>당첨번호: {', '.join(map(str, latest['numbers']))}</p>",
        f"<p>보너스 번호: {latest['bonus']}</p>",
        "<h3>최근 20회 출현 빈도 TOP 10</h3>",
        "<ol>"
    ]

    for n in ranking[:10]:
        lines.append(f"<li>{n}번: {counts[n]}회</li>")

    lines.extend([
        "</ol>",
        f"<p>홀수 {odd}개 / 짝수 {even}개</p>",
        "<p>과거 통계는 다음 추첨의 당첨을 보장하지 않습니다.</p>"
    ])

    with open("lotto_report.html", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("로또 분석 완료")
    print("최신 회차:", latest["round"])
    print("결과 파일: lotto_report.html")


if __name__ == "__main__":
    main()
