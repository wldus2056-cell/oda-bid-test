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
    start = now - timedelta(days=30) #테스트: 조회 기간을 1일에서 30일로 늘림
    start_dt = to_dt_str(start)
    end_dt = to_dt_str(now)

    items = fetch_bid_list(api_key, start_dt, end_dt)
    print("TOTAL ITEMS:", len(items))

    filtered = []
    skipped_ai = 0
    keyword_passed = 0
    koica_passed = 0

#수정됨: 1차, 2차 필터를 하나의 반복문으로 합치고 KOICA 무조건 통과 추가
for it in items:
        title = it.get("bidNtceNm", "")
        org = str(it.get("dminsttNm", "")) # 안전하게 문자열로 처리
        url = it.get("bidNtceDtlUrl", "")

        # 1. 수요기관이 "한국국제협력단"인 경우 필터 무시하고 무조건 통과
        if "한국국제협력단" in org:
            it["_ai_reason"] = "🌟 한국국제협력단(KOICA) 자동 통과"
            filtered.append(it)
            koica_passed += 1
            continue

        # 2. 1차 키워드 필터
        if not keyword_match(title):
            continue
        
        keyword_passed += 1

        # 3. 2차 Gemini 필터
        is_oda, reason = gemini_is_oda(title, org, url)
        if is_oda:
            it["_ai_reason"] = reason
            filtered.append(it)
        else:
            skipped_ai += 1
            # 💡 추가됨: GitHub Actions 로그에서 AI가 왜 탈락시켰는지 확인용 출력
            print(f"[AI 제외] {title[:30]}... | 기관: {org} | 사유: {reason}")

# 요약 메시지 내용 갱신
    summary_text = (
        f"- 조회기간: {start_dt} ~ {end_dt} (최근 30일)\n"
        f"- 전체 공고: {len(items)}건\n"
        f"- KOICA 자동 통과: {koica_passed}건\n"
        f"- 키워드 통과 후 AI 검사: {keyword_passed}건\n"
        f"- 2차 AI 제외: {skipped_ai}건"
    )

    if not filtered:
        send_discord(
            webhook_url,
            content=f"📢 ODA 입찰공고 알림(테스트 요약)\n{summary_text}\n오늘은 조건에 맞는 공고가 없습니다.",
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
        
        # 첫 번째 메시지에만 요약 정보 포함
        content_msg = f"📢 신규 ODA 관련 입찰공고 알림 ({i}/{len(chunks)})"
        if i == 1:
            content_msg = f"📢 **ODA 입찰공고 알림(테스트 요약)**\n{summary_text}\n\n{content_msg}"

        send_discord(
            webhook_url,
            content=content_msg,
            embeds=embeds
        )

if __name__ == "__main__":
    main()
