
import json
import urllib.request

URL = "https://www.dhlottery.co.kr/lt645/selectPstLt645Info.do"

request = urllib.request.Request(
    URL,
    headers={"User-Agent": "Mozilla/5.0"}
)

with urllib.request.urlopen(request, timeout=20) as response:
    data = json.load(response)

draw = data["data"]["list"][0]

numbers = [
    draw[f"tm{i}WnNo"]
    for i in range(1, 7)
]

print("회차:", draw["ltEpsd"])
print("당첨번호:", numbers)
print("보너스:", draw["bnsWnNo"])

with open("lotto_report.html", "w", encoding="utf-8") as file:
    file.write(
        f"<h2>로또 {draw['ltEpsd']}회 당첨번호</h2>"
        f"<p>당첨번호: {numbers}</p>"
        f"<p>보너스: {draw['bnsWnNo']}</p>"
    )

print("분석 결과 파일 생성 완료")
