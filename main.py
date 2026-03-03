# main.py
import os
import time
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
    start = now - timedelta(days=20) 
    start_dt = to_dt_str(start)
    end_dt = to_dt_str(now)

    items = fetch_bid_list(api_key, start_dt, end_dt)
    print("TOTAL ITEMS:", len(items))

    filtered = []
    skipped_ai = 0
    keyword_passed = 0
    koica_passed = 0

    for it in items:
        title = it.get("bidNtceNm", "")
        org = str(it.get("dminsttNm", ""))
        url = it.get("bidNtceDtlUrl", "")

        # 1. 한국국제협력단 무조건 통과
        if "한국국제협력단" in org:
            it["_ai_reason"] = "🌟 한국국제협력단(KOICA) 자동 통과"
            filtered.append(it)
            koica_passed += 1
            continue

        # 2. 1차 키워드 필터
        if not keyword_match(title):
            continue
        
        keyword_passed += 1

        # API 한도 초과 에러를 막기 위해 4초 대기 (1분에 15건 속도 제한 맞춤)
        print(f"[{keyword_passed}번째 항목 검사 중...] 4초 대기...")
        time.sleep(4)

        # 3. 2차 Gemini 필터
        is_oda, reason = gemini_is_oda(title, org, url)
        if is_oda:
            it["_ai_reason"] = f"✅ [AI 합격] {reason}"
            filtered.append(it)
        else:
            skipped_ai += 1
            print(f"[AI 제외] {title[:30]}... | 사유: {reason}")

    # 요약 메시지 텍스트
    ai_passed = keyword_passed - skipped_ai
    summary_text = (
        f"- 조회기간: {start_dt} ~ {end_dt} (최근 20일)\n"
        f"- 전체 공고: {len(items)}건\n"
        f"- 1차 키워드 통과: {keyword_passed}건 (KOICA {koica_passed}건 별도)\n"
        f"- 2차 AI 통과: {ai_passed}건 (AI 제외 {skipped_ai}건)"
    )

    if not filtered:
        send_discord(
            webhook_url,
            content=f"📢 ODA 입찰공고 알림(일일 요약)\n{summary_text}\n오늘은 조건에 맞는 공고가 없습니다.",
            embeds=None
        )
        return

    # 10개씩 묶어서 디스코드로 전송
    chunk_size = 10
    chunks = [filtered[i:i+chunk_size] for i in range(0, len(filtered), chunk_size)]

    for i, chunk in enumerate(chunks, start=1):
        if not chunk:
            continue
        embeds = [build_embed(it) for it in chunk]
        
        content_msg = f"📢 신규 ODA 관련 입찰공고 알림 ({i}/{len(chunks)})"
        if i == 1:
            content_msg = f"📢 **ODA 입찰공고 알림(일일 요약)**\n{summary_text}\n\n{content_msg}"

        send_discord(
            webhook_url,
            content=content_msg,
            embeds=embeds
        )

if __name__ == "__main__":
    main()
