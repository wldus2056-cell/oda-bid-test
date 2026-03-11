# ai_filter.py
import os
import json
import re
import requests

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ==========================================
# 정규식 패턴 세팅
# ==========================================
# 1. 제외 키워드
EXCLUDE_KEYWORDS = [
    "유지보수", "정비사업", "도로포장", "CCTV", "청사", "사무용품", "단순 수출",
    "박람회", "전시회", "국내", "보도블럭", "조경", "방역", "경비용역", "폐기물", "인도 및 차도",
    "자격시험", "도배", "예방접종", "건강검진", "차량 임차", "구내식당", "사무환경", "기자재 공급", "기자재 도입", "기자재 구매", "제작 및 설치", "가구 제작", 
    "시스템 감리", "감리 용역", "건축물 개보수", "버스 공급"
]
_EXCLUDE_PATTERN = re.compile("|".join(map(re.escape, EXCLUDE_KEYWORDS)))

# 2. 핵심 ODA 키워드 (무조건 합격)
CORE_KEYWORDS = [
    "ODA", "공적개발원조", "한국국제협력단", "KOICA", "EDCF",
    "대외경제협력기금", "국제개발협력", "수원국", "무상원조", "한국국제보건의료재단", "KOFIH", "국제질병퇴치기금", 
    "다자개발은행", "MDB", "글로벌녹색성장기구", "GGGI", "경제발전경험공유사업", "KSP", "경제혁신파트너십프로그램", "EIPP", 
    "월드프렌즈코리아", "WFK", "글로벌 연수사업", "PMC 용역", "디지털전환"
]
_CORE_PATTERN = re.compile("|".join(map(re.escape, CORE_KEYWORDS)), re.IGNORECASE)

# 3. 애매한 키워드 (국가명, 일반적인 협력/개발 단어 - LLM 검증 필요)
AMBIGUOUS_KEYWORDS = [
    "가나", "수단", "말리", "차드", "조지아", "인도", "개발협력", "국제협력",
    "개발도상국", "아프리카", "아시아", "중남미", "베트남", "인도네시아", "르완다",
    "우즈베키스탄", "몽골", "필리핀", "캄보디아", "라오스", "페루", "도미니카", "카메룬",
    "기술협력", "개발지원", "조성사업", "강화사업", "구축사업", "타당성 조사"
]
_AMBIGUOUS_PATTERN = re.compile("|".join(map(re.escape, AMBIGUOUS_KEYWORDS)))


# ==========================================
# LLM 호출용 내부 함수
# ==========================================
def _is_oda_project_llm(title: str, org: str = "", url: str = "") -> tuple[bool, str]:
    """실제 Gemini API를 호출하여 문맥을 판별하는 내부 함수"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return (False, "GEMINI_API_KEY 없음")

    prompt = f"""
너는 공공기관 입찰공고 문맥을 분석하여 ODA(공적개발원조) 및 국제개발협력 관련 사업인지 판별하는 전문가 시스템이다.
동음이의어 오탐지 방지를 위해 문맥을 엄격히 확인해라. 'ODA'라는 단어가 명시되지 않아도 아래 기준에 부합하면 ODA 사업으로 간주한다.

[핵심 판별 기준]
1. 진성 ODA/국제개발 사업 (is_oda: true): 
   - 개발도상국 현지를 대상으로 하는 정책 컨설팅, 마스터플랜 수립, PMC(사업관리) 용역, 전략 연구 등 '소프트웨어/컨설팅' 중심의 사업.
   - 예: '네팔 폴리테크닉 설립사업 PMC 용역', 'KOICA 디지털전환 전략 연구용역', '인도네시아 마스터플랜 수립 PMC 용역' 등.
2. 단순 인프라/기자재/물품공급 사업 강력 제외 (is_oda: false): 
   - ODA 관련 사업명의 타이틀을 달고 있더라도, 실제 입찰 내용이 단순 하드웨어, 기자재 납품, 건축, 단순 설치/제작, 감리인 경우는 제외한다.
   - 예: '기자재 공급 및 설치', '가구 제작 및 설치', '홍보관 전시물 제작', '시스템 감리 용역', '건축물 개보수', '버스 공급' 등.
3. 동음이의어 및 국내 사업 제외 (is_oda: false): 
   - '가나'(출판사, 가나다), '수단'(지급 수단, 목적과 수단), '말리'(말리다), '차드'(차량), '조지아'(커피) 등 개도국 국가명이 일반 명사로 쓰인 경우.
   - 단순 해외 전시회/수출, 공공기관 자체 운영(시험 운영, 시설 도배, 직원 건강검진/예방접종 등).
   
입력 정보:
- 공고명: {title}
- 수요기관: {org}
- 링크: {url}

결과는 반드시 아래 JSON 한 줄만 반환:
{{"is_oda": true/false, "reason": "40자 이내 구체적 판단 근거"}}
""".strip()

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 120}
    }

    try:
        r = requests.post(
            f"{GEMINI_ENDPOINT}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=body,
            timeout=30
        )

        if r.status_code == 429:
            return (False, "Gemini 한도 초과")
        if not r.ok:
            return (False, f"Gemini 오류 {r.status_code}")

        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return (False, "응답 파싱 실패")

        obj = json.loads(text[start:end+1])
        is_oda = bool(obj.get("is_oda", False))
        reason = str(obj.get("reason", "")).strip()[:60] or "근거 없음"
        
        # LLM이 판단한 것임을 표시
        return (is_oda, f"🤖 [LLM 판단] {reason}")

    except Exception as e:
        return (False, f"예외: {type(e).__name__}")


# ==========================================
# 하이브리드 필터 진입점 (main.py에서 호출됨)
# ==========================================
def gemini_is_oda(title: str, org: str = "", url: str = "") -> tuple[bool, str]:
    """
    4단계 하이브리드 필터링 컨트롤러
    """
    if not title:
        return (False, "제목 없음")
        
    # 1단계: 제외 키워드가 있으면 즉시 버림
    if _EXCLUDE_PATTERN.search(title):
        return (False, "🛑 [1차 탈락] 제외 키워드 포함")
        
    # 2단계: 핵심 ODA 키워드가 있으면 즉시 합격
    if _CORE_PATTERN.search(title):
        return (True, "⚡관련 ODA 키워드 포함")
        
    # 3단계: 애매한 국가명/단어가 포함된 경우에만 LLM에게 질문 (정확도 확보)
    if _AMBIGUOUS_PATTERN.search(title):
        print(f"   ㄴ[검증] '{title[:20]}...' -> 애매한 키워드 감지. LLM 호출!")
        return _is_oda_project_llm(title, org, url)
        
    # 4단계: 위 3개 조건에 모두 해당하지 않으면 ODA 사업이 아님
    return (False, "🛑 [탈락] 관련 키워드 없음")


# ==========================================
# 간단한 로컬 테스트 코드
# ==========================================
if __name__ == "__main__":
    # 환경 변수에 API 키가 세팅되어 있어야 3단계 LLM이 정상 작동합니다.
    test_titles = [
        "2024년 르완다 농업기술 역량강화 ODA 사업",      # 2단계에서 즉시 True
        "종로구 율곡로 보행 인도 및 차도 정비사업",        # 1단계에서 즉시 False
        "2025년 인도네시아 직업훈련원 건립 타당성 조사",   # 3단계로 넘어가서 LLM 호출
        "서울시 CCTV 유지보수 용역",                     # 1단계에서 즉시 False
        "신규 지급 수단 도입을 위한 시스템 구축 용역"      # 3단계로 넘어가서 LLM이 False 처리해야 함
    ]

    print("--- 하이브리드 필터링 테스트 시작 ---\n")
    for t in test_titles:
        is_oda, reason = gemini_is_oda(title=t)
        print(f"공고명: {t}")
        print(f"결 과: {is_oda} | 사유: {reason}")
        print("-" * 50)
