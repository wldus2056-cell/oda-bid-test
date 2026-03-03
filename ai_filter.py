# ai_filter.py
import os
import json
import time
import requests

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def gemini_is_oda(title: str, org: str = "", url: str = "") -> tuple[bool, str]:
    """
    반환: (is_oda, reason)
    - is_oda: ODA 관련이면 True
    - reason: 짧은 판단 근거(디스코드에 표시용)
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return (False, "GEMINI_API_KEY 없음")

    prompt = f"""
너는 입찰공고 문맥을 보고 ODA 관련 공고인지 판별하는 분류기다.

판단 기준:
- ODA, 국제개발협력, 개발협력, 공적개발원조, 수원국 지원, 개발도상국 대상 사업, 해외 원조성 사업, 국제기구 협력, KOICA/EDCF 성격이면 ODA 관련으로 본다.
- 단순 해외 진출, 수출, 박람회, 단순 국제 행사, 국내 시설공사/물품구매, 국내 시스템 유지보수 등은 ODA로 보지 않는다.

입력:
- 공고명: {title}
- 수요기관: {org}
- 링크: {url}

출력은 반드시 아래 JSON 한 줄만 반환:
{{"is_oda": true/false, "reason": "근거를 40자 이내로"}}
""".strip()

    body = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 120
        }
    }

    try:
        r = requests.post(
            f"{GEMINI_ENDPOINT}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=body,
            timeout=30
        )

        # 무료 구간은 한도나 속도 제한이 있을 수 있어요. :contentReference[oaicite:1]{index=1}
        if r.status_code == 429:
            return (False, "Gemini 한도 초과")
        if not r.ok:
            return (False, f"Gemini 오류 {r.status_code}")

        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # 모델이 JSON 이외를 섞을 때 대비: 첫 중괄호부터 마지막 중괄호까지 잘라서 파싱
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return (False, "응답 파싱 실패")

        obj = json.loads(text[start:end+1])
        is_oda = bool(obj.get("is_oda", False))
        reason = str(obj.get("reason", "")).strip()[:60] or "근거 없음"
        return (is_oda, reason)

    except Exception as e:
        return (False, f"예외: {type(e).__name__}")