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
    return dt.strftime("%Y%m%d%H%M")

def build_embed(item: dict) -> dict:
    title = item.get("bidNtceNm", "(제목 없음)")
    org = item.get("dminsttNm", "-")
    deadline = item.get("bidQlfctRgstDt", "-")
    budget = item.get("asignBdgtAmt", "-")
    url = item.get("bidNtceDtlUrl", "")
    ai_reason = item.get("_ai_reason")

    fields = [
        {"name": "수요기관", "value": str(org), "inline": True},
        {"name": "입찰참가신청마감", "value": str(deadline), "inline": True},
        {"name": "예산금액", "value": str(budget), "inline": False},
    ]
    if url:
        fields.append({"name": "링크", "value": url, "inline": False})
    if ai_reason:
        fields.append({"name": "AI 판별 근거", "value": str(ai_reason), "inline": False})

    return {"title": title, "fields": fields}

def main():
    api_key = os.environ["G2B_API_KEY"].strip()
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"].strip()

    now = datetime.now(KST)
    start = now - timedelta(days=1)
    start_dt = to_dt_str(start)
    end_dt = to_dt_str(now)

    items = fetch_bid_list(api_key, start_dt, end_dt)
    print("TOTAL ITEMS:", len(items))

    # 1차 키워드 필터
    stage1 = []
    for it in items:
        title = it.get("bidNtceNm", "")
        if keyword_match(title):
            stage1.append(it)

    # 2차 Gemini 필터
    filtered = []
    skipped_ai = 0

    for it in stage1:
        title = it.get("bidNtceNm", "")
        org = it.get("dminsttNm", "")
        url = it.get("bidNtceDtlUrl", "")

        is_oda, reason = gemini_is_oda(title, org, url)
        if is_oda:
            it["_ai_reason"] = reason
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
                f"- 1차 키워드 통과: {len(stage1)}건\n"
                f"- 2차 AI 통과: 0건 (AI 제외 {skipped_ai}건)\n"
                "오늘은 조건에 맞는 공고가 없습니다."
            ),
            embeds=None
        )
        return

    # 디스코드는 메시지/임베드 제한이 있어서 chunk로 나눔
    chunk_size = 10
    chunks = [filtered[i:i+chunk_size] for i in range(0, min(len(filtered), 20), chunk_size)]

    for i, chunk in enumerate(chunks, start=1):
        if not chunk:
            continue
        embeds = [build_embed(it) for it in chunk]
        send_discord(
            webhook_url,
            content=f"📢 신규 ODA 관련 입찰공고 알림 ({i}/{len(chunks)})",
            embeds=embeds
        )

if __name__ == "__main__":
    main()
