# ai_filter.py
import os
import json
import re
import requests

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"

# ==========================================
# 정규식 패턴 세팅
# ==========================================
# 1. 제외 키워드
EXCLUDE_KEYWORDS = [
    "유지보수", "정비사업", "도로포장", "CCTV", "청사", "사무용품", "단순 수출",
    "박람회", "전시회", "국내", "보도블럭", "조경", "방역", "경비용역", "폐기물", "인도 및 차도",
    "자격시험", "도배", "예방접종", "건강검진", "차량 임차", "구내식당", "사무환경", "기자재 공급", "기자재 도입", "기자재 구매", "제작 및 설치", "가구 제작", 
    "시스템 감리", "감리 용역", "건축물 개보수", "버스 공급", "항공권 구매", "단체보험", "단체 보험", "항공권", "항공권 구매", "비자 발급", "비자발급", "임직원", "보험 공급자",
    "하자소송", "법률대리", "변호사 선임", "체육시설", "안전경영", 
    "재외동포", "차세대동포", "해양법", "모국 초청", "채용 대행", "신규 채용", "렌터카", "차량 임차", "행사 대행", "개막식", "탁구", "마스터즈", "전시물 제작", "기념 특별전", 
    "세계기록유산", "인류무형유산", "창의도시", "생태탐방로"
]
_EXCLUDE_PATTERN = re.compile("|".join(map(re.escape, EXCLUDE_KEYWORDS)))

# 2. 핵심 ODA 키워드 (무조건 합격)
CORE_KEYWORDS = [
    "ODA", "공적개발원조", "한국국제협력단", "KOICA", "EDCF",
    "대외경제협력기금", "국제개발협력", "수원국", "무상원조", "한국국제보건의료재단", "KOFIH", "국제질병퇴치기금", 
    "다자개발은행", "MDB", "글로벌녹색성장기구", "GGGI", "경제발전경험공유사업", "KSP", "경제혁신파트너십프로그램", "EIPP", 
    "월드프렌즈코리아", "WFK", "글로벌 연수사업", "PMC 용역", "형성조사", "초청연수", "초청 연수", "기아대책",     
    # 다자개발은행 (MDB)
    "다자개발은행", "MDB", "세계은행", "World Bank", "WB", "아시아개발은행", "ADB", "아프리카개발은행", "AfDB", "미주개발은행", "IDB", "유럽부흥개발은행", "EBRD", "아시아인프라투자은행", "AIIB",
    
    # UN 및 국제기구
    "UNDP", "유엔개발계획", "UNICEF", "유니세프", "UNHCR", "유엔난민기구", "WHO", "세계보건기구", "WFP", "세계식량계획", "FAO", "식량농업기구", "ILO", "국제노동기구", "IOM", "국제이주기구", "UNIDO", "유엔공업개발기구", "UNEP", "유엔환경계획", "UNFPA", "유엔인구기금",
]
_CORE_PATTERN = re.compile("|".join(map(re.escape, CORE_KEYWORDS)), re.IGNORECASE)

# 3. 애매한 키워드 (전 세계 모든 개발도상국 목록 추가 - LLM 검증 필요)
AMBIGUOUS_KEYWORDS = [
    # 💡 ODA 실무 키워드 및 대륙명
    "개발협력", "국제협력", "기술협력", "개발지원", "조성사업", "강화사업", "구축사업",
    "역량강화", "역량 강화", "마스터플랜", "타당성조사", "타당성 조사", "심층조사", "심층 조사", "기획조사", "기획 조사", "성과관리", 
    "모니터링", "플랫폼", "정보시스템", "현대화", "전략계획", "로드맵", "기획지원", "평가",
    "개발도상국", "개도국", "아프리카", "아시아", "중남미", "오세아니아", "태평양", "CIS", "동유럽", "UNESCO", "유네스코",
    
    # 💡 OECD DAC 수원국 명단 (개발도상국)
    # [아시아]
    "네팔", "동티모르", "라오스", "미얀마", "방글라데시", "아프가니스탄", "캄보디아", "북한", 
    "몽골", "베트남", "부탄", "스리랑카", "인도", "파키스탄", "필리핀", "말레이시아", 
    "몰디브", "인도네시아", "중국", "태국",
    
    # [아프리카]
    "감비아", "기니", "기니비사우", "남수단", "니제르", "라이베리아", "레소토", "르완다", 
    "마다가스카르", "말라위", "말리", "모리타니아", "모잠비크", "베냉", "부룬디", "부르키나파소", 
    "상투메프린시페", "세네갈", "소말리아", "수단", "시에라리온", "앙골라", "에리트레아", 
    "에티오피아", "우간다", "잠비아", "중앙아프리카", "지부티", "차드", "코모로", "탄자니아", 
    "토고", "DR콩고", "콩고", "가나", "나이지리아", "모로코", "알제리", "에스와티니", 
    "이집트", "카메룬", "카보베르데", "코트디부아르", "케냐", "튀니지", "짐바브웨", "가봉", 
    "나미비아", "남아프리카공화국", "리비아", "모리셔스", "보츠와나", "세인트헬레나", "적도기니",
    
    # [중남미]
    "아이티", "니카라과", "볼리비아", "온두라스", "가이아나", "과테말라", "그레나다", 
    "도미니카", "멕시코", "몬트세랫", "베네수엘라", "벨리즈", "브라질", "세인트루시아", 
    "세인트빈센트", "수리남", "아르헨티나", "에콰도르", "엘살바도르", "자메이카", 
    "코스타리카", "콜롬비아", "쿠바", "파나마", "파라과이", "페루",
    
    # [중동/CIS/동유럽]
    "예멘", "시리아", "레바논", "요르단", "우즈베키스탄", "우크라이나", "키르기스스탄", 
    "이란", "타지키스탄", "북마케도니아", "몬테네그로", "몰도바", "벨라루스", "보스니아", 
    "팔레스타인", "세르비아", "아르메니아", "아제르바이잔", "알바니아", "이라크", "조지아", 
    "카자흐스탄", "코소보", "터키", "튀르키예", "투르크메니스탄",
    
    # [오세아니아]
    "솔로몬제도", "키리바시", "투발루", "마이크로네시아", "바누아투", "사모아", "토켈라우", 
    "파푸아뉴기니", "나우루", "피지", "마셜제도", "니우에", "왈리스푸투나"
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

# 💡 프롬프트
    prompt = f"""
너는 ODA(공적개발원조) 및 국제개발협력 컨설팅 전문 기업의 입찰 판별 AI다.
우리 회사는 아래 [수주 가능 사업 유형]에 해당하는 용역만 수주한다.

반드시 아래 순서대로 판별하라:
① [즉시 탈락 기준]을 먼저 확인 → 하나라도 해당하면 무조건 is_oda: false
② 탈락이 아닌 경우에만 [합격 기준] 확인

━━━━━━━━━━━━━━━━━━━━━━
【① 즉시 탈락 기준】 — 아래 중 하나라도 해당하면 무조건 false
━━━━━━━━━━━━━━━━━━━━━━

[A. 하드웨어·물품·시설]
기자재/물품/가구 공급, 전시물 제작·설치, 버스·차량 공급, 건축물 신축·개보수,
토목·도로·포장·조경 공사, 시스템 감리 용역

[B. 단순 행정·운영 지원]
채용 대행 (예: 'KOICA 신규 채용 대행'), 렌터카·차량 임차, 항공권 구매,
비자 발급 대행, 단체보험 공급자 선정, 변호사 선임·하자소송,
건물·시설 위탁운영, 구내식당, 경비·방역 용역

[C. 국내 행사·전시·문화·체육 용역]
국내 전시 기획·연출, 전시물 제작 및 설치, 국내 기념행사·특별전 운영,
개막식·부대행사 운영, 학술토론회·포럼 단순 행사대행,
탁구·스포츠 대회 운영 (예: '강릉세계마스터즈탁구선수권대회')

[D. 유네스코·유니세프 등 국제기구 명칭을 쓴 국내 사업]
유네스코 세계기록유산·인류무형유산 등재 신청/전략 수립,
유네스코 창의도시 행사, 유네스코 생태탐방로 조성,
유니세프·WHO 국내 캠페인, 유네스코 센터 차량 임차 등
※ 기관 이름이 ODA 기관(KOICA, 유네스코 등)이더라도 내용이 국내 행정·운영이면 탈락

[E. 비ODA 목적 교류·연수]
재외동포/차세대동포 모국 초청, 해양법 아카데미,
특정 직군 단순 해외연수 (교통공무원 초청, 수도관계자 초청 등),
ODA 컨설팅과 무관한 단발성 교류 행사

[F. 동음이의어·국내 지명·일반명사 오인]
'인도(보행로)', '가나(출판사/식품)', '차드(인명)' 등 개발도상국명이 아닌 용례,
국내 지자체 사업에 국가명이 우연히 포함된 경우

━━━━━━━━━━━━━━━━━━━━━━
【② 합격 기준】 — 탈락이 아닌 경우에만 아래 해당 여부 확인
━━━━━━━━━━━━━━━━━━━━━━

[1. ODA 사업 기획·조사·평가·연구 용역]
형성조사, 타당성조사(F/S), 심층조사, 기획조사, 전략평가, 성과관리, 모니터링,
역량진단, 중장기 로드맵·마스터플랜 수립, 패키지사업 기획, 평가 연구
- 합격 예시: '라오스 암 검진 역량강화 형성조사', '우크라이나 공항 마스터플랜',
  'ODA 시행기관 역량진단', '다지역 유사 ODA 사업 평가', 'ODA 무상사업 성과관리 연구'

[2. ODA 사업 수행(PMC) 및 소프트웨어·IT 구축]
PMC 용역, 지적DB·토지정보 플랫폼 구축, 정보시스템 개발, 스마트시티·교통(ITS),
모빌리티 전략 수립, 스마트 솔루션 시범구축, 수산·농업 개발 연구용역
- 합격 예시: '우즈베키스탄 스마트 버스체계 구축', '탄자니아 지적DB 플랫폼 구축',
  '방글라데시 토지가격 정보시스템 개발', '콜롬비아 모빌리티 스마트 솔루션 시범구축'

[3. 개도국 대상 ODA 역량강화 및 초청연수 운영]
ODA 시행기관 역량강화 프로그램, 국제협력센터 초청연수 운영 대행,
개도국 전문 인력 역량강화, ODA 역량강화 교육 운영
- 합격 예시: '2026년 국제협력센터 초청연수 운영 대행',
  '국제개발협력(ODA) 역량강화 프로그램 운영 용역',
  '감염병 신속대응 인재양성 후속사업 기획지원'

입력 정보:
- 공고명: {title}
- 수요기관: {org}
- 링크: {url}

위 기준을 바탕으로 분석하여, 결과를 반드시 아래 JSON 한 줄만 반환:
{{"is_oda": true/false, "reason": "40자 이내 구체적 판단 근거"}}
""".strip()



# ==========================================
# 1순위: Gemini 호출
# ==========================================
def _call_gemini(prompt: str) -> tuple[bool, str] | None:
    """
    Gemini 호출. 성공 시 결과 반환, 429/오류 시 None 반환 (→ DeepSeek로 폴백)
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None  # 키 없으면 바로 폴백

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
            print("   ㄴ[Gemini 한도초과] → DeepSeek로 폴백")
            return None  # 폴백 신호

        if not r.ok:
            print(f"   ㄴ[Gemini 오류 {r.status_code}] → DeepSeek로 폴백")
            return None

        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            return None

        obj = json.loads(text[start:end+1])
        is_oda = bool(obj.get("is_oda", False))
        reason = str(obj.get("reason", "")).strip()[:60] or "근거 없음"
        return (is_oda, f"🤖 [Gemini] {reason}")

    except Exception as e:
        print(f"   ㄴ[Gemini 예외 {type(e).__name__}] → DeepSeek로 폴백")
        return None


# ==========================================
# 2순위: DeepSeek 호출
# ==========================================
def _call_deepseek(prompt: str) -> tuple[bool, str] | None:
    """
    DeepSeek 호출. 성공 시 결과 반환, 오류 시 None 반환 (→ 임시통과)
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return None  # 키 없으면 임시통과

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    body = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 120,
    }

    try:
        r = requests.post(
            DEEPSEEK_ENDPOINT,
            headers=headers,
            json=body,
            timeout=30
        )

        if not r.ok:
            print(f"   ㄴ[DeepSeek 오류 {r.status_code}] → 임시통과")
            return None

        data = r.json()
        text = data["choices"][0]["message"]["content"].strip()
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            return None

        obj = json.loads(text[start:end+1])
        is_oda = bool(obj.get("is_oda", False))
        reason = str(obj.get("reason", "")).strip()[:60] or "근거 없음"
        return (is_oda, f"🤖 [DeepSeek] {reason}")

    except Exception as e:
        print(f"   ㄴ[DeepSeek 예외 {type(e).__name__}] → 임시통과")
        return None


# ==========================================
# LLM 호출 통합 (Gemini → DeepSeek → 임시통과)
# ==========================================
def _is_oda_project_llm(title: str, org: str = "", url: str = "") -> tuple[bool, str]:
    prompt = _build_prompt(title, org)

    # 1순위: Gemini
    result = _call_gemini(prompt)
    if result is not None:
        return result

    # 2순위: DeepSeek
    result = _call_deepseek(prompt)
    if result is not None:
        return result

    # 최후: 그냥 탈락
    return (False, "🛑 [전체실패] Gemini·DeepSeek 모두 한도초과")



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
