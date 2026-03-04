"""
Gemini API 연동 및 프롬프트 관리 (배치 처리 방식)
"""
from __future__ import annotations
import random
import re
import time
import base64
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

# KST 시간대
KST = timezone(timedelta(hours=9))

from config.settings import GEMINI_API_KEYS, GEMINI_MODEL, GEMINI_MODEL_LITE, SIGNAL_CATEGORIES
from modules.key_monitor import record_alert
from modules.utils import parse_json_response, resize_image


@dataclass
class KeyState:
    index: int
    request_count: int = 0       # 할당 횟수 (로깅용)
    success_count: int = 0       # 성공 횟수
    consecutive_429: int = 0     # 연속 429 횟수
    daily_exhausted: bool = False
    cooldown_until: float = 0.0

    def is_available(self) -> bool:
        if self.daily_exhausted:
            return False
        if self.cooldown_until > time.time():
            return False
        return True


# 키 상태 리스트 초기화
_key_states: list[KeyState] = [KeyState(index=i) for i in range(len(GEMINI_API_KEYS))]


def get_next_api_key() -> tuple[str, int] | None:
    """사용 가능한 키 중 request_count가 가장 낮은 것 선택"""
    if not GEMINI_API_KEYS:
        print("[ERROR] Gemini API 키가 설정되지 않았습니다.")
        return None

    available = [ks for ks in _key_states if ks.is_available()]

    if not available:
        # 쿨다운 중인 키가 있으면 최단 쿨다운 만료까지 대기
        cooling = [ks for ks in _key_states if not ks.daily_exhausted]
        if cooling:
            soonest = min(ks.cooldown_until for ks in cooling)
            wait = max(0, soonest - time.time())
            if wait > 0:
                print(f"  [KEY] 모든 키 쿨다운 중. {wait:.0f}초 대기...")
                time.sleep(wait)
            available = [ks for ks in _key_states if ks.is_available()]

    if not available:
        print("[ERROR] 모든 키 소진 (daily_exhausted)")
        record_alert("GEMINI", "", "quota_exhausted", "모든 키 소진 (daily_exhausted)")
        return None

    # 여유 프로젝트 우선 (request_count 가장 낮은 키)
    best = min(available, key=lambda ks: ks.request_count)
    best.request_count += 1
    return GEMINI_API_KEYS[best.index], best.index


def handle_rate_limit(key_index: int, retry_delay: float | None = None):
    """429 에러 시 쿨다운 설정 (RPM 제한 대응)

    모든 429는 RPM(일시적) 제한으로 처리 — 쿨다운만 설정.
    daily_exhausted는 절대 마킹하지 않음 (401/403 인증 오류에서만 사용).
    """
    ks = _key_states[key_index]
    ks.consecutive_429 += 1

    if retry_delay and retry_delay > 0:
        cooldown = min(retry_delay + random.uniform(1, 5), 300)
    else:
        cooldown = min(30 * (2 ** (ks.consecutive_429 - 1)), 300)
    ks.cooldown_until = time.time() + cooldown
    print(f"  [KEY #{key_index + 1}] RPM 제한. 쿨다운 {cooldown:.0f}초 설정. (연속 429: {ks.consecutive_429}회)")

    avail_count = sum(1 for ks in _key_states if ks.is_available())
    print(f"  남은 사용 가능 키: {avail_count}개")


def mark_success(key_index: int):
    """API 호출 성공 시 호출 — 연속 429 카운터를 리셋"""
    ks = _key_states[key_index]
    ks.success_count += 1
    ks.consecutive_429 = 0


def _parse_retry_delay(error) -> float | None:
    """429 에러 메시지에서 retryDelay 추출 (초 단위)"""
    try:
        match = re.search(r'retry in (\d+\.?\d*)s', str(error))
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return None


def _check_finish_reason(response) -> str | None:
    """응답의 finish_reason 확인. 차단된 경우 사유 문자열 반환, 정상이면 None."""
    try:
        if not response.candidates:
            return None
        fr = response.candidates[0].finish_reason
        fr_str = fr.name if hasattr(fr, 'name') else str(fr) if fr else ""
        if fr_str in ("SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII"):
            return fr_str
    except (AttributeError, IndexError):
        pass
    return None


# Vision AI 분석 프롬프트
VISION_ANALYSIS_PROMPT = """당신은 20년 경력의 대한민국 주식 시장 전문 퀀트 애널리스트입니다.

오늘 날짜: {today}

아래에 {count}개의 네이버 증권 종목 상세 페이지 스크린샷이 첨부되어 있습니다.
각 이미지에 대해 다음 작업을 수행하세요:

{macro_context}## 1. 데이터 추출
이미지에서 다음 항목들을 추출하세요:
- 기본정보: 종목명, 종목코드, 시장구분(코스피/코스닥)
- 가격정보: 현재가, 전일대비, 등락률, 전일, 시가, 고가, 저가
- 거래정보: 거래량, 거래대금, 시가총액
- 기술적지표: 이동평균선(MA), 차트 패턴
- 밸류에이션: PER, EPS, 추정PER, 추정EPS, PBR, BPS
- 배당정보: 배당수익률, 주당배당금
- 컨센서스: 목표주가, 투자의견 (없는 종목 있음)
- 수급정보: 외인소진율, 호가잔량, 투자자별 매매동향

**데이터 판독 불가 시**: 이미지에서 특정 데이터가 보이지 않거나 판독이 어려운 경우, 해당 항목은 무시하고 판독 가능한 데이터만으로 분석을 진행하세요.

## 2. 분석 수행
추출한 데이터를 바탕으로 다음 분석을 수행하세요:

### 2-1. 기술적 분석 (가중치 30%)
각 항목을 0~10점으로 채점한 뒤 평균을 산출하세요:
- **추세** (5일/20일/60일 이동평균선 기준): 정배열=8~10, 혼조=4~6, 역배열=0~3
- **차트 패턴**: 강한 돌파=8~10, 횡보=4~6, 하락 패턴=0~3
- **거래량**: 전일대비 150%↑ 동반 상승=8~10, 평균 수준=4~6, 감소세=0~3
- **이격도**: 20일선 대비 -5%~+5% 적정=5~7, 과이격=0~3

### 2-2. 수급 분석 (가중치 35%)
각 항목을 0~10점으로 채점한 뒤 평균을 산출하세요:
- **외국인 동향**: 5일 연속 순매수=8~10, 혼조=4~6, 5일 연속 순매도=0~3
- **기관 동향**: 5일 연속 순매수=8~10, 혼조=4~6, 5일 연속 순매도=0~3
- **호가 잔량**: 매수잔량/매도잔량 > 1.5=8~10, 0.7~1.5=4~6, < 0.7=0~3

### 2-3. 밸류에이션 분석 (가중치 20%)
각 항목을 0~10점으로 채점한 뒤 평균을 산출하세요:
- **PER 상대평가**: 동종업 평균 대비 30%↓=8~10, 비슷=4~6, 30%↑=0~3 (절대 수치만으로 판단하지 마세요)
- **PEG**: <1=8~10, 1~2=4~6, >2=0~3 (추정EPS 가용 시)
- **목표주가 괴리율**: 현재가가 목표가 대비 20%↓=8~10, 근접=4~6, 20%↑=0~3

### 2-4. 재료 분석 (가중치 15%)
각 종목에 대해 google_search 도구를 사용하여 최근 관련 뉴스를 검색하세요.
검색 키워드: "{{종목명}} 주식 뉴스" (예: "삼성전자 주식 뉴스")
검색 결과를 바탕으로:
- 호재/악재 여부 및 시장 심리 판단
- 실적, M&A, 신사업, 규제, 소송 등 주요 재료 파악
- 테마 및 섹터 모멘텀 평가
- 뉴스 시의성: 오늘 날짜 기준 1주일 이내를 '최근'으로 간주하세요.
- **센티먼트 점수**: -1.0(극히 부정) ~ +1.0(극히 긍정) 산출. 7일 이내 뉴스에 가중치 2배.
- **재료 점수**: 센티먼트 점수를 0~10 스케일로 변환 (0.0→5, +1.0→10, -1.0→0)

## 3. 계산 지표 활용
다음 지표들을 계산하여 분석에 반영하세요:
1. **가격 모멘텀**: (현재가 - 전일가) / 전일가 × 100
2. **고저 대비 위치**: (현재가 - 저가) / (고가 - 저가) × 100
3. **이동평균 이격도**: 현재가와 각 이동평균선 간의 괴리율
4. **매수/매도 잔량 비율**: 총매수잔량 / 총매도잔량

## 4. 시그널 판단 기준
종합점수 = 기술(×0.30) + 수급(×0.35) + 밸류(×0.20) + 재료(×0.15) 로 산출하고, 아래 테이블로 판정하세요:

| 종합점수 | 시그널 |
|----------|--------|
| 8.0 ~ 10.0 | **적극매수** |
| 6.5 ~ 7.9 | **매수** |
| 3.5 ~ 6.4 | **중립** |
| 2.0 ~ 3.4 | **매도** |
| 0.0 ~ 1.9 | **적극매도** |

## 5. 신뢰도(confidence) 산정 기준
confidence = 종합점수 / 10 (소수점 둘째 자리까지)
예: 종합점수 7.2 → confidence 0.72

## 6. 분석 대상 종목
{stock_list}

## 7. 출력 형식
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만 출력하세요:
```json
{{
  "results": [
    {{
      "name": "종목명",
      "code": "종목코드",
      "market": "코스피 또는 코스닥",
      "current_price": 현재가(숫자),
      "change_rate": 등락률(숫자, 예: 2.5),
      "signal": "시그널",
      "scores": {{
        "technical": 기술점수(0~10),
        "supply_demand": 수급점수(0~10),
        "valuation": 밸류점수(0~10),
        "material": 재료점수(0~10),
        "total": 종합점수(0~10, 가중평균)
      }},
      "reason": "분석 근거 (2~3문장, 반드시 구체적 수치를 인용. 예: RSI 72, PER 8.3, 외인 순매수 +150억 등)",
      "key_factors": {{
        "price_trend": "상승/횡보/하락",
        "volume_signal": "급증/증가/보통/감소",
        "foreign_flow": "매수우위/중립/매도우위",
        "institution_flow": "매수우위/중립/매도우위",
        "valuation": "저평가/적정/고평가"
      }},
      "risk_level": "높음/중간/낮음",
      "confidence": 신뢰도(0.0~1.0),
      "news_analysis": {{
        "sentiment": "긍정/중립/부정",
        "sentiment_score": 센티먼트점수(-1.0~+1.0),
        "key_news": ["주요 뉴스 1줄 요약 (최대 5개)"],
        "catalyst": "핵심 재료 요약 (1~2문장)"
      }}
    }}
  ]
}}
```

### few-shot 예시 (1개 종목)
```json
{{
  "results": [
    {{
      "name": "삼성전자",
      "code": "005930",
      "market": "코스피",
      "current_price": 72000,
      "change_rate": 2.1,
      "signal": "매수",
      "scores": {{"technical": 7.0, "supply_demand": 7.5, "valuation": 6.0, "material": 6.5, "total": 6.95}},
      "reason": "20일선 위 정배열 전환, 외인 3일 연속 순매수(+120억), PER 12.3으로 업종 평균 15.2 대비 저평가.",
      "key_factors": {{"price_trend": "상승", "volume_signal": "증가", "foreign_flow": "매수우위", "institution_flow": "중립", "valuation": "저평가"}},
      "risk_level": "중간",
      "confidence": 0.70,
      "news_analysis": {{"sentiment": "긍정", "sentiment_score": 0.4, "key_news": ["삼성전자, AI 반도체 수주 확대 전망"], "catalyst": "AI 반도체 수요 증가로 HBM 매출 성장 기대"}}
    }}
  ]
}}
```

## 중요 사항
1. 모든 {count}개 종목에 대해 분석 결과를 반드시 포함해야 합니다.
2. 종목과 해당 종목에 대한 분석 결과가 정확히 매칭되도록 주의하세요.
3. 이미지 순서와 종목 목록 순서가 동일합니다.
4. 각 종목에 대해 반드시 google_search로 뉴스를 검색하고 news_analysis 필드를 포함하세요.
5. news_analysis는 반드시 google_search 검색 결과를 기반으로 작성하세요. 검색 결과에 없는 내용을 추측하여 포함하지 마세요.
"""


def validate_and_recalculate(item: dict) -> dict:
    """scores 필드 검증 및 종합점수/confidence/signal 재계산

    AI 응답의 scores가 누락되거나 total이 가중평균과 불일치할 때 보정.
    """
    scores = item.get("scores")
    if not scores or not isinstance(scores, dict):
        return item

    weights = {"technical": 0.30, "supply_demand": 0.35, "valuation": 0.20, "material": 0.15}

    # 개별 점수를 0~10 범위로 클램프
    for key in weights:
        val = scores.get(key)
        if isinstance(val, (int, float)):
            scores[key] = max(0.0, min(10.0, float(val)))
        else:
            scores[key] = 5.0  # 기본값

    # 가중평균 재계산
    total = sum(scores[k] * w for k, w in weights.items())
    scores["total"] = round(total, 2)
    item["scores"] = scores

    # confidence 재계산
    item["confidence"] = round(total / 10, 2)

    return item


def analyze_stocks_batch(scrape_results: list[dict], capture_dir: Path, max_retries: int = min(2 * len(GEMINI_API_KEYS), 10), macro_context: str = "") -> list[dict]:
    """모든 종목 이미지를 한 번에 배치 분석 (API 1회 호출)"""
    print("\n=== Phase 3: AI 배치 분석 (Vision) ===\n")
    print(f"[INFO] 사용 가능한 API 키: {len(GEMINI_API_KEYS)}개")
    print(f"[INFO] 모델: {GEMINI_MODEL}")
    print(f"[INFO] 최대 재시도: {max_retries}회")

    # 성공한 종목만 필터링
    valid_stocks = []
    image_parts = []

    for stock in scrape_results:
        if not stock.get("success"):
            continue

        code = stock["code"]
        image_path = capture_dir / f"{code}.png"

        if not image_path.exists():
            print(f"  [SKIP] {stock['name']}: 이미지 없음")
            continue

        # 이미지 로드 및 리사이즈
        image_bytes = resize_image(image_path)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        valid_stocks.append(stock)
        image_parts.append({
            "inline_data": {
                "mime_type": "image/png",
                "data": image_b64
            }
        })

    if not valid_stocks:
        print("[ERROR] 분석할 종목이 없습니다.")
        return []

    print(f"분석 대상: {len(valid_stocks)}개 종목")
    print(f"총 이미지: {len(image_parts)}개\n")

    # 종목 리스트 문자열 생성
    stock_list_str = "\n".join([
        f"- {i+1}번째 이미지: {s['name']} ({s['code']}) - {s['market']}"
        for i, s in enumerate(valid_stocks)
    ])

    # 프롬프트 생성
    today = datetime.now(KST).strftime("%Y-%m-%d")
    prompt = VISION_ANALYSIS_PROMPT.format(
        count=len(valid_stocks),
        stock_list=stock_list_str,
        today=today,
        macro_context=macro_context,
    )

    # API 호출 시도
    consecutive_parse_failures = 0
    for attempt in range(max_retries):
        key_info = get_next_api_key()
        if not key_info:
            print("[ERROR] 사용 가능한 API 키가 없습니다.")
            record_alert("GEMINI", "", "no_available_key", "Vision 분석: 사용 가능한 API 키 없음")
            return []

        api_key, key_index = key_info
        print(f"[시도 {attempt + 1}/{max_retries}] API 키 #{key_index + 1} 사용")

        try:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=300_000,
                    retry_options=types.HttpRetryOptions(
                        initial_delay=2.0, attempts=3, exp_base=2,
                        max_delay=30, jitter=1,
                        http_status_codes=[408, 500, 502, 503, 504],
                    ),
                ),
            )

            # 모든 이미지와 프롬프트를 하나의 요청으로
            parts = image_parts + [{"text": prompt}]

            print(f"[API] Gemini API 호출 시작...")
            print(f"[API] 요청 데이터: 이미지 {len(image_parts)}개, 프롬프트 {len(prompt)}자")
            api_start_time = time.time()

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    {
                        "role": "user",
                        "parts": parts
                    }
                ],
                config={
                    "max_output_tokens": 65536,  # 최대 출력 토큰 (100개 종목 분석용)
                    "tools": [{"google_search": {}}],
                }
            )

            api_elapsed = time.time() - api_start_time
            print(f"[API] 응답 수신 완료 (소요시간: {api_elapsed:.1f}초)")

            # FinishReason 검사 (콘텐츠 차단 감지)
            blocked_reason = _check_finish_reason(response)
            if blocked_reason:
                print(f"[WARNING] 콘텐츠 차단됨 (finish_reason={blocked_reason}). 재시도...")
                time.sleep(min(5 * (attempt + 1), 30))
                continue

            # response.text가 비어있는 경우 방어 (STOP이어도 빈 응답 가능)
            if not response.text or not response.text.strip():
                print("[ERROR] 응답 텍스트가 비어있음 (response.text=None/empty)")
                backoff = min(2 * (2 ** attempt) + random.uniform(0, 1), 60)
                time.sleep(backoff)
                continue

            print(f"[API] 응답 길이: {len(response.text)}자")

            # 응답 파싱
            result = parse_json_response(response.text)

            if result and "results" in result:
                raw_results = result["results"]
                analysis_time = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
                expected_count = len(valid_stocks)

                # === 1. 중복 제거 (같은 종목코드는 첫 번째만 유지) ===
                seen_codes = set()
                deduped_results = []
                duplicate_count = 0
                for item in raw_results:
                    code = item.get("code")
                    if code and code not in seen_codes:
                        seen_codes.add(code)
                        deduped_results.append(item)
                    elif code:
                        duplicate_count += 1

                if duplicate_count > 0:
                    print(f"[INFO] 중복 제거: {len(raw_results)}개 → {len(deduped_results)}개 ({duplicate_count}개 중복)")

                # === 2. 필수 필드 및 데이터 유효성 검증 ===
                REQUIRED_FIELDS = ["name", "code", "signal"]
                valid_results = []
                invalid_count = 0
                invalid_reasons = {"missing_field": 0, "null_value": 0, "invalid_code": 0}

                for item in deduped_results:
                    is_valid = True

                    # 필수 필드 존재 여부
                    for field in REQUIRED_FIELDS:
                        if field not in item:
                            is_valid = False
                            invalid_reasons["missing_field"] += 1
                            break

                    if not is_valid:
                        invalid_count += 1
                        continue

                    # null/빈 값 검증
                    code = item.get("code")
                    name = item.get("name")
                    if not code or not name or code == "null" or name == "null":
                        invalid_count += 1
                        invalid_reasons["null_value"] += 1
                        continue

                    # 종목코드 형식 검증 (6자리 숫자)
                    if not (isinstance(code, str) and len(code) == 6 and code.isdigit()):
                        # 문자열 변환 시도
                        try:
                            code = str(code).zfill(6)
                            if len(code) != 6 or not code.isdigit():
                                raise ValueError()
                            item["code"] = code
                        except:
                            invalid_count += 1
                            invalid_reasons["invalid_code"] += 1
                            continue

                    valid_results.append(item)

                if invalid_count > 0:
                    print(f"[WARNING] 유효하지 않은 항목 제외: {invalid_count}개")
                    print(f"[WARNING] 상세: 필드누락={invalid_reasons['missing_field']}, "
                          f"null값={invalid_reasons['null_value']}, "
                          f"잘못된코드={invalid_reasons['invalid_code']}")

                # === 3. scores 검증 및 시그널/메타데이터 추가 ===
                signal_stats = {}
                for item in valid_results:
                    # scores 검증 및 재계산
                    validate_and_recalculate(item)

                    # 시그널 유효성 검증 (scores 없는 경우 fallback)
                    if item.get("signal") not in SIGNAL_CATEGORIES:
                        item["signal"] = "중립"

                    # 매칭되는 종목의 캡처 시각 추가
                    matched_stock = next(
                        (s for s in valid_stocks if s["code"] == item.get("code")),
                        None
                    )
                    if matched_stock:
                        item["capture_time"] = matched_stock.get("capture_time", "N/A")
                    else:
                        item["capture_time"] = "N/A"

                    item["analysis_time"] = analysis_time

                    # 시그널 통계
                    sig = item.get("signal", "중립")
                    signal_stats[sig] = signal_stats.get(sig, 0) + 1

                # === 4. 요청/응답 종목 리스트 일치 검증 ===
                requested_codes = set(s["code"] for s in valid_stocks)
                responded_codes = set(item.get("code") for item in valid_results)

                missing_codes = requested_codes - responded_codes  # 요청했지만 응답 없음
                extra_codes = responded_codes - requested_codes    # 요청 안했지만 응답 있음
                matched_codes = requested_codes & responded_codes  # 일치

                match_rate = (len(matched_codes) / len(requested_codes) * 100) if requested_codes else 0

                print(f"\n[VALIDATION] 종목 리스트 검증:")
                print(f"  - 요청: {len(requested_codes)}개, 응답: {len(responded_codes)}개, 일치: {len(matched_codes)}개 ({match_rate:.1f}%)")

                if missing_codes:
                    missing_names = [s["name"] for s in valid_stocks if s["code"] in missing_codes][:10]
                    print(f"  - 누락된 종목 ({len(missing_codes)}개): {missing_names}{'...' if len(missing_codes) > 10 else ''}")

                if extra_codes:
                    print(f"  - 추가된 종목 ({len(extra_codes)}개): {list(extra_codes)[:10]}{'...' if len(extra_codes) > 10 else ''}")
                    # 요청한 종목만 유지
                    valid_results = [item for item in valid_results if item.get("code") in requested_codes]

                if not missing_codes and not extra_codes:
                    print(f"  - ✓ 요청/응답 종목 리스트 완전 일치")

                # === 5. 결과 수 검증 (입력 대비 80% 미만이면 경고) ===
                actual_count = len(valid_results)
                coverage_rate = (actual_count / expected_count * 100) if expected_count > 0 else 0

                if coverage_rate < 80:
                    print(f"[WARNING] 결과 부족: {actual_count}/{expected_count}개 ({coverage_rate:.1f}%)")
                    print(f"[WARNING] max_output_tokens 한계 또는 모델 처리 한계일 수 있음")

                print(f"\n[SUCCESS] 분석 완료: {actual_count}/{expected_count}개 종목 ({coverage_rate:.1f}%)")
                print(f"[INFO] 시그널 분포: {signal_stats}")
                mark_success(key_index)
                return valid_results

            # 파싱 실패: 연속 2회 시 빠른 포기
            consecutive_parse_failures += 1
            print(f"[ERROR] 응답 파싱 실패 - JSON 파싱 불가 (연속 {consecutive_parse_failures}회)")
            print("[DEBUG] 상세 파싱 로그:")
            parse_json_response(response.text, debug=True)
            print(f"[DEBUG] 응답 앞부분 (최대 300자):\n{response.text[:300]}")
            if consecutive_parse_failures >= 2:
                print("[ERROR] 연속 2회 파싱 실패. 이 배치 스킵.")
                return []
            backoff = min(2 * (2 ** attempt) + random.uniform(0, 1), 60)
            time.sleep(backoff)
            continue  # 재시도

        except ClientError as e:
            print(f"  [KEY #{key_index + 1}] ClientError({e.code}): {str(e)[:150]}")
            if e.code == 429:
                retry_delay = _parse_retry_delay(e)
                handle_rate_limit(key_index, retry_delay=retry_delay)
                # 별도 프로젝트 키가 남아있으면 즉시 전환, 없으면 백오프 대기
                avail = sum(1 for ks in _key_states if ks.is_available())
                if avail > 0:
                    time.sleep(random.uniform(1, 3))
                else:
                    backoff = min(2 * (2 ** attempt) + random.uniform(0, 1), 60)
                    time.sleep(backoff)
                continue
            elif e.code == 400:
                # INVALID_ARGUMENT — 요청 자체 문제, 다른 키로 재시도해도 동일
                print(f"  요청 오류 (HTTP 400). 동일 요청 재시도 불가.")
                record_alert("GEMINI", f"KEY_{key_index+1}", "request_error", f"Vision: HTTP 400 요청 오류")
                return []
            elif e.code in (401, 403):
                _key_states[key_index].daily_exhausted = True
                print(f"  [KEY #{key_index + 1}] 인증/권한 오류 — 당일 제외 (HTTP {e.code})")
                record_alert("GEMINI", f"KEY_{key_index+1}", "auth_error", f"Vision: HTTP {e.code} 키 제외")
                continue
            elif e.code == 404:
                print("[ERROR] 모델을 찾을 수 없습니다.")
                return []
            else:
                backoff = min(2 * (2 ** attempt) + random.uniform(0, 1), 60)
                time.sleep(backoff)

        except ServerError as e:
            print(f"  [KEY #{key_index + 1}] ServerError({e.code}): {str(e)[:150]}")
            if e.code == 503:
                backoff = min(30 * (2 ** attempt) + random.uniform(0, 5), 120)
                print(f"  서버 과부하. {backoff:.0f}초 대기.")
            elif e.code == 504:
                print(f"  서버 타임아웃 (5분 제한 초과 가능).")
                backoff = min(10 + random.uniform(0, 5), 30)
            else:
                backoff = min(2 * (2 ** attempt) + random.uniform(0, 1), 60)
            time.sleep(backoff)

        except Exception as e:
            print(f"  [KEY #{key_index + 1}] 오류: {str(e)[:150]}")
            backoff = min(2 * (2 ** attempt) + random.uniform(0, 1), 60)
            time.sleep(backoff)

    print(f"[ERROR] {max_retries}회 시도 후 실패 (모든 API 키 쿼터 소진)")
    record_alert("GEMINI", "", "all_retries_failed", f"Vision: {max_retries}회 시도 후 실패")
    return []


# 하위 호환성을 위한 별칭
def analyze_stocks(scrape_results: list[dict], capture_dir: Path, macro_context: str = "") -> list[dict]:
    """analyze_stocks_batch의 별칭 (하위 호환성)"""
    return analyze_stocks_batch(scrape_results, capture_dir, macro_context=macro_context)



def _calc_technical_indicators(price_history: dict) -> dict:
    """price_history에서 기술 지표를 사전 계산"""
    daily = price_history.get("daily", price_history.get("days", []))
    rsi = price_history.get("rsi_14")
    if not daily:
        return {"rsi_14": rsi}

    closes = [d["close"] for d in daily if d.get("close")]
    indicators = {"rsi_14": rsi}

    for period in [5, 10, 20]:
        if len(closes) >= period:
            indicators[f"ma{period}"] = round(sum(closes[:period]) / period)

    if len(closes) >= 5:
        indicators["change_5d_pct"] = round((closes[0] / closes[4] - 1) * 100, 2)
    if len(closes) >= 20:
        indicators["change_20d_pct"] = round((closes[0] / closes[-1] - 1) * 100, 2)

    # 20일 상승일 비율 (추세 강도)
    if len(daily) >= 2:
        up_count = sum(1 for i in range(min(20, len(daily) - 1)) if daily[i].get("close", 0) > daily[i + 1].get("close", 0))
        total = min(20, len(daily) - 1)
        indicators["up_days_20d"] = round(up_count / total, 2) if total > 0 else None

    ma5, ma10, ma20 = indicators.get("ma5"), indicators.get("ma10"), indicators.get("ma20")
    if ma5 and ma10 and ma20 and closes:
        if closes[0] > ma5 > ma10 > ma20:
            indicators["ma_status"] = "bullish"
        elif closes[0] < ma5 < ma10 < ma20:
            indicators["ma_status"] = "bearish"
        else:
            indicators["ma_status"] = "mixed"

    return indicators


def _count_consecutive_buys(daily_trend: list, key: str) -> int:
    """daily_trend에서 최근 연속 순매수 일수 계산"""
    count = 0
    for day in daily_trend:
        if (day.get(key) or 0) > 0:
            count += 1
        else:
            break
    return count


def _flatten_stock(code: str, data: dict) -> dict:
    """종목 데이터를 플랫 딕셔너리로 변환"""
    r = data.get("ranking", {})
    p = data.get("price", {})
    t = data.get("trading", {})
    m = data.get("market_info", {})
    v = data.get("valuation", {})
    ob = data.get("order_book", {})
    iv = data.get("investor_flow", {})
    iv_today = iv.get("today", {})
    iv_5d = iv.get("sum_5_days", {})
    iv_daily = iv.get("daily_trend", [])
    fi = data.get("foreign_institution", {})
    fi_20d = fi.get("sum_20_days", {})
    fund = data.get("fundamental", {})
    tech = _calc_technical_indicators(data.get("price_history", {}))

    return {
        "code": code,
        "name": data.get("name", ""),
        "market": data.get("market", ""),
        # ranking
        "vol_rank": r.get("volume_rank"),
        "vol_rate": r.get("volume_rate_vs_prev"),
        # price
        "price": p.get("current"),
        "change_pct": p.get("change_rate_pct"),
        "high_52w": p.get("high_52week"),
        "low_52w": p.get("low_52week"),
        # trading
        "turnover_pct": t.get("volume_turnover_pct"),
        # market_info
        "mktcap_bn": m.get("market_cap_billion"),
        "foreign_hold_pct": m.get("foreign_holding_pct"),
        # valuation
        "per": v.get("per"),
        "pbr": v.get("pbr"),
        "eps": v.get("eps"),
        "peg": v.get("peg"),
        # order_book
        "bid_ask_ratio": ob.get("bid_ask_ratio"),
        # investor_flow
        "for_today": iv_today.get("foreign_net"),
        "inst_today": iv_today.get("institution_net"),
        "for_5d": iv_5d.get("foreign_net"),
        "inst_5d": iv_5d.get("institution_net"),
        "for_consec_buy": _count_consecutive_buys(iv_daily, "foreign_net"),
        "inst_consec_buy": _count_consecutive_buys(iv_daily, "institution_net"),
        # foreign_institution 20d
        "for_20d": fi_20d.get("foreign_net"),
        "inst_20d": fi_20d.get("institution_net"),
        # technical_indicators (price_history 대체)
        "rsi_14": tech.get("rsi_14"),
        "ma5": tech.get("ma5"),
        "ma10": tech.get("ma10"),
        "ma20": tech.get("ma20"),
        "chg_5d_pct": tech.get("change_5d_pct"),
        "chg_20d_pct": tech.get("change_20d_pct"),
        "ma_status": tech.get("ma_status"),
        "up_days_20d": tech.get("up_days_20d"),
        # fundamental (optional)
        "roe": fund.get("roe"),
        "opm": fund.get("opm"),
        "debt_ratio": fund.get("debt_ratio"),
        "eps_growth": fund.get("eps_growth_rate"),
        "sales_growth": fund.get("sales_growth"),
        "op_profit_growth": fund.get("op_profit_growth"),
    }


def stocks_to_markdown_kv(stocks: dict) -> str:
    """종목 데이터를 Markdown-KV 문자열로 변환"""
    lines = []
    for code, data in stocks.items():
        row = _flatten_stock(code, data)
        lines.append(f"### {row['code']} {row['name']}")
        for k, v in row.items():
            if k in ("code", "name") or v is None or v == "":
                continue
            lines.append(f"- {k}: {v}")
        lines.append("")
    return "\n".join(lines)



# KIS API 데이터 분석용 프롬프트
KIS_ANALYSIS_PROMPT = """당신은 20년 경력의 대한민국 주식 시장 전문 퀀트 애널리스트입니다.

오늘 날짜: {today}

아래에 한국투자증권 OpenAPI에서 수집한 {count}개 종목의 실시간 데이터가 Markdown-KV 형식으로 제공됩니다.
각 종목은 `### 종목코드 종목명` 헤더로 구분되며, `- 필드: 값` 형태로 나열됩니다.

⚠️ 응답 형식: 반드시 유효한 JSON만 출력하세요. 마크다운, Python 코드, 설명 텍스트를 절대 포함하지 마세요.

{macro_context}## 1. 데이터 확인
필드 설명:
- code/name/market: 종목코드, 종목명, 시장(KOSPI/KOSDAQ)
- vol_rank: 거래량 순위, vol_rate: 전일대비 거래량 변화율(100 이상=증가)
- price/change_pct: 현재가, 등락률(%)
- high_52w/low_52w: 52주 최고가/최저가
- turnover_pct: 거래량 회전율(%)
- mktcap_bn: 시가총액(억원), foreign_hold_pct: 외인보유비율(%)
- per/pbr/eps/peg: 밸류에이션 지표
- bid_ask_ratio: 호가잔량비(100↑=매수우위)
- for_today/inst_today: 당일 외인/기관 순매수, for_5d/inst_5d: 5일 합계
- for_consec_buy/inst_consec_buy: 최근 연속 외인/기관 순매수 일수(0~5)
- for_20d/inst_20d: 20일 누적 외인/기관 순매수
- rsi_14: RSI-14, ma5/ma10/ma20: 이동평균, ma_status: 배열상태(bullish/bearish/mixed)
- chg_5d_pct/chg_20d_pct: 5일/20일 수익률(%)
- up_days_20d: 20일 중 상승일 비율(0~1)
- roe/opm/debt_ratio/eps_growth/sales_growth/op_profit_growth: 펀더멘탈(해당 시 제공)

누락된 필드는 데이터 없음. 분석에서 제외하세요.

## 2. 분석 수행
각 종목에 대해 다음 분석을 가중치에 따라 수행하세요:

### 2-1. 기술적 분석 (가중치 30%)
각 항목을 0~10점으로 채점한 뒤 평균을 산출하세요:
- **추세** (ma5/ma10/ma20 이동평균 + ma_status 기준): 정배열(bullish)=8~10, 혼조(mixed)=4~6, 역배열(bearish)=0~3
- **52주 고저 위치**: 저점 근처=8~10 (반등 가능), 중간=4~6, 고점 근처=2~4 (과열 주의)
- **거래량**: vol_rate 200↑=8~10, 100~200=4~6, 50↓=0~3
- **RSI-14**: 30~50(과매도 반등)=7~9, 50~70(중립)=4~6, >70(과매수)=1~3, <30(급락)=2~4

### 2-2. 수급 분석 (가중치 35%)
각 항목을 0~10점으로 채점한 뒤 평균을 산출하세요:
- **외국인 동향**: 5일 연속 순매수=8~10, 혼조=4~6, 5일 연속 순매도=0~3
- **기관 동향**: 5일 연속 순매수=8~10, 혼조=4~6, 5일 연속 순매도=0~3
- **호가 잔량**: bid_ask_ratio > 150=8~10, 70~150=4~6, < 70=0~3

### 2-3. 밸류에이션 분석 (가중치 20%)
각 항목을 0~10점으로 채점한 뒤 평균을 산출하세요:
- **PER 상대평가**: 동종업 평균 대비 30%↓=8~10, 비슷=4~6, 30%↑=0~3 (절대 수치만으로 판단하지 마세요)
- **PEG**: <1=8~10, 1~2=4~6, >2=0~3 (null이면 생략)
- **ROE**: 15%↑=8~10, 10~15%=5~7, <10%=2~4 (fundamental 필드 있을 때)
- **부채비율**: <100%=7~9, 100~200%=4~6, >200%=1~3

### 2-4. 재료 분석 (가중치 15%)
각 종목에 대해 google_search를 통해 검색하여 재료를 분석하세요.
검색 키워드: "{{종목명}} 주식 뉴스" (예: "삼성전자 주식 뉴스")
- 호재/악재 여부 및 시장 심리 판단
- 실적, M&A, 신사업, 규제, 소송 등 주요 재료 파악
- 테마 및 섹터 모멘텀 평가
- 뉴스 시의성: 오늘 날짜 기준 1주일 이내를 '최근'으로 간주하세요.
- **센티먼트 점수**: -1.0(극히 부정) ~ +1.0(극히 긍정) 산출. 7일 이내 뉴스에 가중치 2배.
- **재료 점수**: 센티먼트 점수를 0~10 스케일로 변환 (0.0→5, +1.0→10, -1.0→0)

## 3. 계산 지표 활용
1. **52주 고저 위치**: (price - low_52w) / (high_52w - low_52w) × 100
2. **수급 강도**: (for_today + inst_today) / mktcap_bn × 100
3. **RSI-14**: rsi_14 (>70 과매수, <30 과매도)
4. **PEG**: peg (<1 저평가, >2 고평가)

## 4. 시그널 판단 기준
종합점수 = 기술(×0.30) + 수급(×0.35) + 밸류(×0.20) + 재료(×0.15) 로 산출하고, 아래 테이블로 판정하세요:

| 종합점수 | 시그널 |
|----------|--------|
| 8.0 ~ 10.0 | **적극매수** |
| 6.5 ~ 7.9 | **매수** |
| 3.5 ~ 6.4 | **중립** |
| 2.0 ~ 3.4 | **매도** |
| 0.0 ~ 1.9 | **적극매도** |

## 5. 신뢰도(confidence) 산정 기준
confidence = 종합점수 / 10 (소수점 둘째 자리까지)
예: 종합점수 7.2 → confidence 0.72

## 6. 분석 대상 종목 데이터
{stock_data}

## 7. 출력 형식
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만 출력하세요:
```json
{{
  "analysis_time": "분석 시각 (YYYY-MM-DD HH:MM:SS)",
  "results": [
    {{
      "code": "종목코드",
      "name": "종목명",
      "market": "KOSPI/KOSDAQ",
      "current_price": 현재가(숫자),
      "change_rate": 등락률(숫자),
      "signal": "시그널",
      "scores": {{
        "technical": 기술점수(0~10),
        "supply_demand": 수급점수(0~10),
        "valuation": 밸류점수(0~10),
        "material": 재료점수(0~10),
        "total": 종합점수(0~10, 가중평균)
      }},
      "reason": "분석 근거 (2~3문장, 반드시 구체적 수치를 인용. 예: RSI 72, PER 8.3, 외인 순매수 +150억 등)",
      "key_factors": {{
        "price_trend": "상승/횡보/하락",
        "volume_signal": "급증/증가/보통/감소",
        "foreign_flow": "매수우위/중립/매도우위",
        "institution_flow": "매수우위/중립/매도우위",
        "valuation": "저평가/적정/고평가"
      }},
      "risk_level": "높음/중간/낮음",
      "confidence": 신뢰도(0.0~1.0),
      "news_analysis": {{
        "sentiment": "긍정/중립/부정",
        "sentiment_score": 센티먼트점수(-1.0~+1.0),
        "key_news": ["주요 뉴스 1줄 요약 (최대 5개)"],
        "catalyst": "핵심 재료 요약 (1~2문장)"
      }},
      "news": [
        {{"title": "뉴스 제목", "link": "URL", "description": "1줄 요약"}}
      ]
    }}
  ]
}}
```

### few-shot 예시 (1개 종목)
```json
{{
  "analysis_time": "2026-03-02 10:30:00",
  "results": [
    {{
      "code": "005930",
      "name": "삼성전자",
      "market": "KOSPI",
      "current_price": 72000,
      "change_rate": 2.1,
      "signal": "매수",
      "scores": {{"technical": 7.0, "supply_demand": 7.5, "valuation": 6.0, "material": 6.5, "total": 6.95}},
      "reason": "20일선 위 정배열 전환, 외인 3일 연속 순매수(+120억), PER 12.3으로 업종 평균 15.2 대비 저평가.",
      "key_factors": {{"price_trend": "상승", "volume_signal": "증가", "foreign_flow": "매수우위", "institution_flow": "중립", "valuation": "저평가"}},
      "risk_level": "중간",
      "confidence": 0.70,
      "news_analysis": {{"sentiment": "긍정", "sentiment_score": 0.4, "key_news": ["삼성전자, AI 반도체 수주 확대 전망"], "catalyst": "AI 반도체 수요 증가로 HBM 매출 성장 기대"}},
      "news": [{{"title": "삼성전자, AI 반도체 수주 확대", "link": "https://example.com", "description": "HBM 매출 성장 기대"}}]
    }}
  ]
}}
```

## 중요 사항
1. 모든 {count}개 종목에 대해 분석 결과를 반드시 포함해야 합니다.
2. 종목과 해당 종목에 대한 분석 결과가 정확히 매칭되도록 주의하세요.
3. 입력 데이터의 종목 순서와 출력 결과의 순서가 동일해야 합니다.
4. 각 종목에 대해 반드시 google_search로 뉴스를 검색하고 news_analysis와 news 필드를 포함하세요.
5. news_analysis와 news는 반드시 google_search 검색 결과를 기반으로 작성하세요. 검색 결과에 없는 내용을 추측하여 포함하지 마세요.
6. 응답은 순수 JSON만 포함해야 합니다. ```json 코드블록, 마크다운 헤딩(##), Python 코드를 절대 포함하지 마세요.
"""


def analyze_kis_data(
    stocks_data: dict,
    stock_codes: list[str] | None = None,
    max_retries: int = min(2 * len(GEMINI_API_KEYS), 10),
    macro_context: str = "",
) -> list[dict]:
    """KIS API 데이터 기반 종목 분석

    Args:
        stocks_data: 변환된 KIS 데이터 (kis_gemini.json 형식)
        stock_codes: 분석할 종목 코드 리스트 (없으면 전체)
        max_retries: 최대 재시도 횟수

    Returns:
        분석 결과 리스트
    """
    import json

    print("\n=== KIS API 데이터 AI 분석 ===\n")
    print(f"사용 가능한 API 키: {len(GEMINI_API_KEYS)}개")

    stocks = stocks_data.get("stocks", {})

    # 분석 대상 종목 필터링
    if stock_codes:
        target_stocks = {code: stocks[code] for code in stock_codes if code in stocks}
    else:
        target_stocks = stocks

    if not target_stocks:
        print("[ERROR] 분석할 종목이 없습니다.")
        return []

    print(f"[INFO] 분석 대상: {len(target_stocks)}개 종목")
    print(f"[INFO] 종목 코드: {list(target_stocks.keys())[:10]}{'...' if len(target_stocks) > 10 else ''}")

    # 데이터 Markdown-KV 변환 (프롬프트 크기 93% 감소)
    stock_md = stocks_to_markdown_kv(target_stocks)
    print(f"[INFO] Markdown-KV 데이터 크기: {len(stock_md):,}자 ({len(target_stocks)}개 종목)")

    # 프롬프트 생성
    today = datetime.now(KST).strftime("%Y-%m-%d")
    prompt = KIS_ANALYSIS_PROMPT.format(
        count=len(target_stocks),
        stock_data=stock_md,
        today=today,
        macro_context=macro_context,
    )
    print(f"[INFO] 프롬프트 길이: {len(prompt):,}자\n")

    # API 호출 시도 (파싱 실패, 429 오류 등 모두 재시도)
    consecutive_parse_failures = 0
    for attempt in range(max_retries):
        key_info = get_next_api_key()
        if not key_info:
            print("[ERROR] 사용 가능한 API 키가 없습니다.")
            record_alert("GEMINI", "", "no_available_key", "KIS 분석: 사용 가능한 API 키 없음")
            return []

        api_key, key_index = key_info
        print(f"[시도 {attempt + 1}/{max_retries}] API 키 #{key_index + 1} 사용 (키 마스킹: {api_key[:8]}...)")

        try:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=300_000,
                    retry_options=types.HttpRetryOptions(
                        initial_delay=2.0, attempts=3, exp_base=2,
                        max_delay=30, jitter=1,
                        http_status_codes=[408, 500, 502, 503, 504],
                    ),
                ),
            )

            print(f"[API] Gemini API 호출 시작...")
            print(f"[API] 모델: {GEMINI_MODEL_LITE} (KIS 데이터 분석용)")
            print(f"[API] 요청 데이터: {len(prompt):,}자")
            api_start_time = time.time()

            response = client.models.generate_content(
                model=GEMINI_MODEL_LITE,
                contents=[
                    {
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }
                ],
                config={
                    "max_output_tokens": 65536,
                    "tools": [{"google_search": {}}],
                },
            )

            api_elapsed = time.time() - api_start_time
            print(f"[API] 응답 수신 완료 (소요시간: {api_elapsed:.1f}초)")

            # FinishReason 검사 (콘텐츠 차단 감지)
            blocked_reason = _check_finish_reason(response)
            if blocked_reason:
                print(f"[WARNING] 콘텐츠 차단됨 (finish_reason={blocked_reason}). 재시도...")
                time.sleep(min(5 * (attempt + 1), 30))
                continue

            # response.text가 비어있는 경우 방어 (STOP이어도 빈 응답 가능)
            if not response.text or not response.text.strip():
                print("[ERROR] 응답 텍스트가 비어있음 (response.text=None/empty)")
                backoff = min(2 * (2 ** attempt) + random.uniform(0, 1), 60)
                time.sleep(backoff)
                continue

            print(f"[API] 응답 길이: {len(response.text):,}자")

            # 응답 파싱
            result = parse_json_response(response.text)

            if result and "results" in result:
                raw_results = result["results"]
                analysis_time = result.get(
                    "analysis_time",
                    datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
                )

                # 중복 제거 (같은 종목코드는 첫 번째만 유지)
                seen_codes = set()
                analysis_results = []
                for item in raw_results:
                    code = item.get("code")
                    if code and code not in seen_codes:
                        seen_codes.add(code)
                        analysis_results.append(item)

                if len(raw_results) != len(analysis_results):
                    print(f"[INFO] 중복 제거: {len(raw_results)}개 → {len(analysis_results)}개")

                # === 요청/응답 종목 리스트 일치 검증 ===
                requested_codes = set(target_stocks.keys())
                responded_codes = set(item.get("code") for item in analysis_results if item.get("code"))

                missing_codes = requested_codes - responded_codes  # 요청했지만 응답 없음
                extra_codes = responded_codes - requested_codes    # 요청 안했지만 응답 있음
                matched_codes = requested_codes & responded_codes  # 일치

                match_rate = (len(matched_codes) / len(requested_codes) * 100) if requested_codes else 0

                print(f"\n[VALIDATION] 종목 리스트 검증:")
                print(f"  - 요청: {len(requested_codes)}개, 응답: {len(responded_codes)}개, 일치: {len(matched_codes)}개 ({match_rate:.1f}%)")

                if missing_codes:
                    missing_names = [target_stocks[code].get("name", code) for code in list(missing_codes)[:10]]
                    print(f"  - 누락된 종목 ({len(missing_codes)}개): {missing_names}{'...' if len(missing_codes) > 10 else ''}")

                if extra_codes:
                    print(f"  - 추가된 종목 ({len(extra_codes)}개): {list(extra_codes)[:10]}{'...' if len(extra_codes) > 10 else ''}")
                    # 요청한 종목만 유지
                    analysis_results = [item for item in analysis_results if item.get("code") in requested_codes]

                if not missing_codes and not extra_codes:
                    print(f"  - ✓ 요청/응답 종목 리스트 완전 일치")

                # 결과 수 검증 (입력 대비 80% 미만이면 경고)
                expected_count = len(target_stocks)
                actual_count = len(analysis_results)
                coverage_rate = (actual_count / expected_count * 100) if expected_count > 0 else 0

                if coverage_rate < 80:
                    print(f"[WARNING] 결과 부족: {actual_count}/{expected_count}개 ({coverage_rate:.1f}%)")
                    print(f"[WARNING] max_output_tokens 한계 또는 모델 처리 한계일 수 있음")

                # scores 검증 및 시그널/메타데이터 추가
                signal_stats = {}
                for item in analysis_results:
                    # scores 검증 및 재계산
                    validate_and_recalculate(item)

                    if item.get("signal") not in SIGNAL_CATEGORIES:
                        item["signal"] = "중립"
                    item["analysis_time"] = analysis_time
                    item["data_source"] = "KIS_API"
                    # 시그널 통계
                    sig = item.get("signal", "중립")
                    signal_stats[sig] = signal_stats.get(sig, 0) + 1

                print(f"\n[SUCCESS] 분석 완료: {len(analysis_results)}/{expected_count}개 종목 ({coverage_rate:.1f}%)")
                print(f"[INFO] 시그널 분포: {signal_stats}")
                mark_success(key_index)
                return analysis_results

            # 파싱 실패: 연속 2회 시 빠른 포기
            consecutive_parse_failures += 1
            print(f"[ERROR] 응답 파싱 실패 - JSON 파싱 불가 (연속 {consecutive_parse_failures}회)")
            print("[DEBUG] 상세 파싱 로그:")
            parse_json_response(response.text, debug=True)
            print(f"[DEBUG] 응답 앞부분 (최대 300자):\n{response.text[:300]}")
            if consecutive_parse_failures >= 2:
                print("[ERROR] 연속 2회 파싱 실패. 이 배치 스킵.")
                return []
            backoff = min(2 * (2 ** attempt) + random.uniform(0, 1), 60)
            time.sleep(backoff)
            continue  # 재시도

        except ClientError as e:
            print(f"[ERROR] [KEY #{key_index + 1}] ClientError({e.code}): {str(e)[:200]}")
            if e.code == 429:
                retry_delay = _parse_retry_delay(e)
                handle_rate_limit(key_index, retry_delay=retry_delay)
                # 별도 프로젝트 키가 남아있으면 즉시 전환, 없으면 백오프 대기
                avail = sum(1 for ks in _key_states if ks.is_available())
                if avail > 0:
                    time.sleep(random.uniform(1, 3))
                else:
                    backoff = min(2 * (2 ** attempt) + random.uniform(0, 1), 60)
                    time.sleep(backoff)
                continue
            elif e.code == 400:
                # INVALID_ARGUMENT — 요청 자체 문제, 다른 키로 재시도해도 동일
                print(f"  요청 오류 (HTTP 400). 동일 요청 재시도 불가.")
                record_alert("GEMINI", f"KEY_{key_index+1}", "request_error", f"KIS 분석: HTTP 400 요청 오류")
                return []
            elif e.code in (401, 403):
                _key_states[key_index].daily_exhausted = True
                print(f"  [KEY #{key_index + 1}] 인증/권한 오류 — 당일 제외 (HTTP {e.code})")
                record_alert("GEMINI", f"KEY_{key_index+1}", "auth_error", f"KIS 분석: HTTP {e.code} 키 제외")
                continue
            elif e.code == 404:
                print("[ERROR] 모델을 찾을 수 없습니다.")
                return []
            else:
                backoff = min(2 * (2 ** attempt) + random.uniform(0, 1), 60)
                time.sleep(backoff)

        except ServerError as e:
            print(f"[ERROR] [KEY #{key_index + 1}] ServerError({e.code}): {str(e)[:200]}")
            if e.code == 503:
                backoff = min(30 * (2 ** attempt) + random.uniform(0, 5), 120)
                print(f"  서버 과부하. {backoff:.0f}초 대기.")
            elif e.code == 504:
                print(f"  서버 타임아웃 (5분 제한 초과 가능).")
                backoff = min(10 + random.uniform(0, 5), 30)
            else:
                backoff = min(2 * (2 ** attempt) + random.uniform(0, 1), 60)
            time.sleep(backoff)

        except Exception as e:
            print(f"[ERROR] [KEY #{key_index + 1}] 오류: {str(e)[:200]}")
            backoff = min(2 * (2 ** attempt) + random.uniform(0, 1), 60)
            time.sleep(backoff)

    print(f"[ERROR] {max_retries}회 시도 후 실패")
    record_alert("GEMINI", "", "all_retries_failed", f"KIS 분석: {max_retries}회 시도 후 실패")
    return []


def analyze_kis_data_batch(
    stocks_data: dict,
    batch_size: int = 10,
    max_retries: int = min(2 * len(GEMINI_API_KEYS), 10),
    macro_context: str = "",
) -> list[dict]:
    """KIS API 데이터 배치 분석 (대량 종목용)

    Args:
        stocks_data: 변환된 KIS 데이터
        batch_size: 배치당 종목 수
        max_retries: 최대 재시도 횟수

    Returns:
        전체 분석 결과 리스트
    """
    stocks = stocks_data.get("stocks", {})
    all_codes = list(stocks.keys())
    deadline = time.time() + 3600  # 60분 시간 예산

    print(f"\n=== KIS 데이터 배치 분석 시작 ===")
    print(f"총 종목: {len(all_codes)}개, 배치 크기: {batch_size}개\n")

    all_results = []

    for i in range(0, len(all_codes), batch_size):
        if time.time() > deadline:
            print("[WARNING] 시간 예산 초과 (60분). 남은 배치 스킵.")
            break

        batch_codes = all_codes[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(all_codes) + batch_size - 1) // batch_size

        print(f"\n--- 배치 {batch_num}/{total_batches} ---")

        results = analyze_kis_data(
            stocks_data,
            stock_codes=batch_codes,
            max_retries=max_retries,
            macro_context=macro_context,
        )

        if results:
            all_results.extend(results)
            print(f"배치 {batch_num} 완료: {len(results)}개 종목 분석")
        else:
            print(f"배치 {batch_num} 실패")

        # 배치 간 딜레이 (google_search 포함, 10 RPM 고려)
        if i + batch_size < len(all_codes):
            print("다음 배치 대기 중... (8초)")
            time.sleep(8)

    # === 누락 종목 재시도 ===
    analyzed_codes = set(r.get("code") for r in all_results if r.get("code"))
    missing_codes = [code for code in all_codes if code not in analyzed_codes]

    if missing_codes and time.time() <= deadline:
        print(f"\n=== 누락 종목 재시도 ({len(missing_codes)}개) ===")
        missing_names = [stocks[c].get("name", c) for c in missing_codes[:10]]
        print(f"[INFO] 대상: {missing_names}{'...' if len(missing_codes) > 10 else ''}")
        retry_max = min(3, max_retries)

        for i in range(0, len(missing_codes), batch_size):
            if time.time() > deadline:
                print("[WARNING] 시간 예산 초과. 남은 재시도 스킵.")
                break

            retry_codes = missing_codes[i:i + batch_size]
            retry_num = i // batch_size + 1

            print(f"\n--- 재시도 배치 {retry_num} ---")

            results = analyze_kis_data(
                stocks_data,
                stock_codes=retry_codes,
                max_retries=retry_max,
                macro_context=macro_context,
            )

            if results:
                all_results.extend(results)
                print(f"재시도 배치 {retry_num} 완료: {len(results)}개 종목 복구")
            else:
                print(f"재시도 배치 {retry_num} 실패")

            if i + batch_size < len(missing_codes):
                time.sleep(8)

    print(f"\n=== 배치 분석 완료 ===")
    print(f"총 분석 완료: {len(all_results)}/{len(all_codes)}개 종목")

    return all_results
