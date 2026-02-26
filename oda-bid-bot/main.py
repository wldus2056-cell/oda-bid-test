# PR 테스트용 수정

# main.py
import os
from datetime import datetime, timedelta, timezone

from g2b import fetch_bid_list
from filters import keyword_match
from discord_notify import send_discord

KST = timezone(timedelta(hours=9))

print("MAIN.PY TOP LOADED")

def to_dt_str(dt: datetime) -> str:
    # 나라장터 예시 코드에서 쓰던 포맷과 동일 계열: YYYYMMDDHHMM :contentReference[oaicite:14]{index=14}
    return dt.strftime("%Y%m%d%H%M")

def build_embed(item: dict) -> dict:
    title = item.get("bidNtceNm", "(제목 없음)")
    org = item.get("dminsttNm", "-")
    deadline = item.get("bidQlfctRgstDt", "-")
    budget = item.get("asignBdgtAmt", "-")
    url = item.get("bidNtceDtlUrl", "")

    fields = [
        {"name": "수요기관", "value": str(org), "inline": True},
        {"name": "입찰참가신청마감", "value": str(deadline), "inline": True},
        {"name": "예산금액", "value": str(budget), "inline": False},
    ]
    if url:
        fields.append({"name": "링크", "value": url, "inline": False})

    return {
        "title": title,
        "fields": fields,
    }

def main():
    api_key = os.environ["G2B_API_KEY"]
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"]

    now = datetime.now(KST)
    start = now - timedelta(days=1)  # 최근 24시간
    start_dt = to_dt_str(start)
    end_dt = to_dt_str(now)

    items = fetch_bid_list(api_key, start_dt, end_dt)
    print(len(items))

    # 1차 키워드 필터
    filtered = []
    for it in items:
        title = it.get("bidNtceNm", "")
        if keyword_match(title):
            filtered.append(it)

    # (선택) 여기서 2차 AI 필터를 붙일 자리 :contentReference[oaicite:15]{index=15}

    if not filtered:
        return  # 아무것도 없으면 조용히 종료

    chunks = [filtered[:10], filtered[10:20]]
    for i, chunk in enumerate(chunks, start=1):
        embeds = [build_embed(it) for it in chunk]
        send_discord(
            webhook_url,
            content=f"📢 신규 ODA 관련 입찰공고 알림 ({i}/2)",
            embeds=embeds
        )

if __name__ == "__main__":

    main()
