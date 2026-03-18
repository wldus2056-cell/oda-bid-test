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
    
    # 💡 예산금액 1000단위 콤마(,) 및 '원' 단위 추가 처리
    raw_budget = item.get("asignBdgtAmt")
    if raw_budget and str(raw_budget).isdigit():
        budget = f"{int(raw_budget):,}원"
    else:
        budget = str(raw_budget) if raw_budget else "-"

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
        fields.append({"name": "필터링 근거", "value": str(ai_reason), "inline": False})

    return {"title": title, "fields": fields}

def main():
    api_key = os.environ["G2B_API_KEY"].strip()
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"].strip()

    now = datetime.now(KST)
    start = now - timedelta(days=10) 
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

        # 2. 1차 키워드 필터 (filters.py)
        if not keyword_match(title):
            
            print(f"[1차탈락] {title}") # ← 추가
            
            continue
            
        print(f"[1차통과] {title}") # ← 추가
        
        keyword_passed += 1

        # 3. 2차 하이브리드 필터 (ai_filter.py)
        is_oda, reason = gemini_is_oda(title, org, url)
        if is_oda:
            # 💡 [AI 합격] 같은 텍스트를 강제로 붙이지 않고, ai_filter.py가 주는 값(reason)을 그대로 씁니다.
            it["_ai_reason"] = reason
            filtered.append(it)
        else:
            skipped_ai += 1
            print(f"[제외] {title[:30]}... | 사유: {reason}")
        if not is_oda:
            print(f"[2차탈락] {title} | {reason}")  # ← 추가
        
    ai_passed = keyword_passed - skipped_ai
    
    display_start = start.strftime("%m월 %d일 %H:%M")
    display_end = now.strftime("%m월 %d일 %H:%M")
    
    summary_text = (
        f"- 조회기간: {display_start} ~ {display_end} (최근 2일)\n"
        f"- 전체 공고: {len(items)}건\n"
        f"- 1차 키워드 통과: {keyword_passed}건\n"
        f"- 2차 AI 필터링 통과: {ai_passed}건 (제외 {skipped_ai}건)"
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
