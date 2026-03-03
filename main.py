# main.py
import os
from datetime import datetime, timedelta, timezone

from g2b import fetch_bid_list
from filters import keyword_match
from discord_notify import send_discord
from ai_filter import gemini_is_oda

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
    ai_reason = item.get("_ai_reason")
    if ai_reason:
        fields.append({"name": "AI 판별 근거", "value": str(ai_reason), "inline": False})

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

    # 2차 Gemini 필터
    filtered = []
    skipped_ai = 0
    for it in stage1:
        title = it.get("bidNtceNm", "")
        org = it.get("dminsttNm", "")
        url = it.get("bidNtceDtlUrl", "")

        is_oda, reason = gemini_is_oda(title, org, url)
        if is_oda:
            it["_ai_reason"] = reason  # 디스코드 표시용
            filtered.append(it)
        else:
            skipped_ai += 1

    if not filtered:
        send_discord(
            webhook_url,
            content=(
                "📢 ODA 입찰공고 알림(일일 요약)\n"
                f"- 조회기간: {start_dt} ~ {end_dt}\n"
                f"- 전체 공고: {len(items)}건\n"
                f"- ODA 후보(필터 통과): 0건\n"
                "오늘은 조건에 맞는 공고가 없습니다."
            ),
            embeds=None
        )
        return

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