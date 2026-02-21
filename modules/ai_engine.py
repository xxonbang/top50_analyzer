"""
Gemini API 연동 및 프롬프트 관리 (배치 처리 방식)
"""
from __future__ import annotations
import time
import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path
from google import genai

# KST 시간대
KST = timezone(timedelta(hours=9))

from config.settings import GEMINI_API_KEYS, GEMINI_MODEL, GEMINI_MODEL_LITE, SIGNAL_CATEGORIES
from modules.utils import parse_json_response, resize_image


# 현재 사용 중인 API 키 인덱스
_current_key_index = 0
_failed_keys = set()


def get_next_api_key() -> tuple[str, int] | None:
    """다음 사용 가능한 API 키 반환"""
    global _current_key_index

    if not GEMINI_API_KEYS:
        print("[ERROR] Gemini API 키가 설정되지 않았습니다.")
        return None

    if len(_failed_keys) >= len(GEMINI_API_KEYS):
        print("[INFO] 모든 키가 실패 상태. 리셋 후 재시도...")
        _failed_keys.clear()

    for _ in range(len(GEMINI_API_KEYS)):
        if _current_key_index not in _failed_keys:
            key = GEMINI_API_KEYS[_current_key_index]
            return key, _current_key_index
        _current_key_index = (_current_key_index + 1) % len(GEMINI_API_KEYS)

    return None


def mark_key_failed(key_index: int):
    """키를 실패 상태로 표시"""
    _failed_keys.add(key_index)
    print(f"  [KEY #{key_index + 1}] 실패. 남은 키: {len(GEMINI_API_KEYS) - len(_failed_keys)}개")


def rotate_to_next_key():
    """다음 키로 로테이션"""
    global _current_key_index
    _current_key_index = (_current_key_index + 1) % len(GEMINI_API_KEYS)


# Vision AI 분석 프롬프트
VISION_ANALYSIS_PROMPT = """당신은 20년 경력의 대한민국 주식 시장 전문 퀀트 애널리스트입니다.

오늘 날짜: {today}

아래에 {count}개의 네이버 증권 종목 상세 페이지 스크린샷이 첨부되어 있습니다.
각 이미지에 대해 다음 작업을 수행하세요:

## 1. 데이터 추출
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
- 차트 패턴 및 추세 방향
- 이동평균선 배열 및 이격도
- 거래량 변화 추세

### 2-2. 수급 분석 (가중치 35%)
- 외인/기관 순매수 동향
- 호가 잔량 비율 (매수세 vs 매도세)
- 외인소진율 변화

### 2-3. 밸류에이션 분석 (가중치 20%)
- PER/PBR 수준 평가 (동일 업종/섹터 평균 대비 상대적으로 평가하세요. 절대 수치만으로 판단하지 마세요.)
- 추정EPS 대비 현재 PER (PEG 개념)
- 목표주가 대비 괴리율

### 2-4. 재료 분석 (가중치 15%)
각 종목에 대해 google_search 도구를 사용하여 최근 관련 뉴스를 검색하세요.
검색 키워드: "{{종목명}} 주식 뉴스" (예: "삼성전자 주식 뉴스")
검색 결과를 바탕으로:
- 호재/악재 여부 및 시장 심리 판단
- 실적, M&A, 신사업, 규제, 소송 등 주요 재료 파악
- 테마 및 섹터 모멘텀 평가
- 뉴스 시의성: 오늘 날짜 기준 1주일 이내를 '최근'으로 간주하세요.

## 3. 계산 지표 활용
다음 지표들을 계산하여 분석에 반영하세요:
1. **가격 모멘텀**: (현재가 - 전일가) / 전일가 × 100
2. **고저 대비 위치**: (현재가 - 저가) / (고가 - 저가) × 100
3. **이동평균 이격도**: 현재가와 각 이동평균선 간의 괴리율
4. **매수/매도 잔량 비율**: 총매수잔량 / 총매도잔량

## 4. 시그널 판단 기준
다음 기준에 따라 시그널을 결정하세요:

| 시그널 | 조건 |
|--------|------|
| **적극매수** | 기술적 강한 상승 신호 + 수급 매수 우위 + 저평가 + 긍정적 재료 (3가지 이상 충족) |
| **매수** | 위 조건 중 2가지 이상 충족, 또는 수급이 강하게 매수 우위 |
| **중립** | 혼조세, 방향성 불명확, 또는 판단 근거 부족 |
| **매도** | 기술적 하락 신호 + 수급 매도 우위 + 부정적 재료 중 1가지 이상 |
| **적극매도** | 기술적 강한 하락 신호 + 수급 매도 우위 + 고평가 + 부정적 재료 (3가지 이상 충족) |

## 5. 신뢰도(confidence) 산정 기준
| 조건 | confidence |
|------|-----------|
| 4개 분석 축(기술/수급/밸류/재료)이 같은 방향 | 0.8~1.0 |
| 3개 축 일치, 1개 상충 | 0.6~0.8 |
| 2개 축 일치, 혼조세 | 0.4~0.6 |
| 데이터 부족 또는 판단 근거 불충분 | 0.2~0.4 |

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
        "key_news": ["주요 뉴스 1줄 요약 (최대 5개)"],
        "catalyst": "핵심 재료 요약 (1~2문장)"
      }}
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


def analyze_stocks_batch(scrape_results: list[dict], capture_dir: Path, max_retries: int = 3) -> list[dict]:
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
        today=today
    )

    # API 호출 시도
    for attempt in range(max_retries):
        key_info = get_next_api_key()
        if not key_info:
            print("[ERROR] 사용 가능한 API 키가 없습니다.")
            return []

        api_key, key_index = key_info
        print(f"[시도 {attempt + 1}/{max_retries}] API 키 #{key_index + 1} 사용")

        try:
            client = genai.Client(api_key=api_key)

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

                # === 3. 시그널 검증 및 메타데이터 추가 ===
                signal_stats = {}
                for item in valid_results:
                    # 시그널 유효성 검증
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
                rotate_to_next_key()
                return valid_results

            # 파싱 실패: 디버깅 로그와 함께 재파싱 시도
            print("[ERROR] 응답 파싱 실패 - API 호출은 성공했으나 JSON 파싱 불가")
            print("[DEBUG] 상세 파싱 로그:")
            parse_json_response(response.text, debug=True)  # 디버그 모드로 재시도하여 로그 출력
            print(f"[DEBUG] 응답 전체 (최대 500자):\n{response.text[:500]}")
            if len(response.text) > 500:
                print(f"[DEBUG] ... (총 {len(response.text)}자 중 500자만 표시)")
            rotate_to_next_key()
            return []  # 파싱 실패 시 빈 결과 반환, 재호출 안 함

        except Exception as e:
            error_msg = str(e)
            print(f"  [KEY #{key_index + 1}] 오류: {error_msg[:100]}")

            # 429 오류 (쿼터 초과): 다른 키로 재시도
            if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                mark_key_failed(key_index)
                rotate_to_next_key()
                print(f"  [KEY #{key_index + 1}] 실패. 남은 키: {len(GEMINI_API_KEYS) - len(_failed_keys)}개")
                time.sleep(2)
                continue

            if "404" in error_msg:
                print("[ERROR] 모델을 찾을 수 없습니다.")
                return []

            # 기타 오류: 다른 키로 재시도
            rotate_to_next_key()
            time.sleep(1)

    print(f"[ERROR] {max_retries}회 시도 후 실패 (모든 API 키 쿼터 소진)")
    return []


# 하위 호환성을 위한 별칭
def analyze_stocks(scrape_results: list[dict], capture_dir: Path) -> list[dict]:
    """analyze_stocks_batch의 별칭 (하위 호환성)"""
    return analyze_stocks_batch(scrape_results, capture_dir)


# KIS API 데이터 분석에 사용할 필수 필드
KIS_ESSENTIAL_FIELDS = [
    'code',                 # 종목코드
    'name',                 # 종목명
    'market',               # 시장구분
    'ranking',              # 거래량 순위 및 변화율
    'price',                # 현재가, 등락률, 시고저종, 52주 고저
    'trading',              # 거래량, 거래대금, 회전율
    'market_info',          # 시가총액, 상장주수, 외인소진율
    'valuation',            # PER, PBR, EPS, BPS
    'order_book',           # 호가 잔량 비율 (수급 압력)
    'investor_flow',        # 외인/기관/개인 순매수 (당일, 5일)
    'foreign_institution',  # 외인/기관 누적 순매수
    'price_history',        # 최근 20일 일봉 (OHLCV) + RSI-14
    'fundamental',          # ROE, OPM, 부채비율, EPS 성장률
]


def reduce_kis_data(stocks: dict) -> dict:
    """KIS 데이터를 분석에 필요한 필수 필드만 추출하여 축소

    Args:
        stocks: 원본 종목 데이터 딕셔너리

    Returns:
        축소된 종목 데이터 딕셔너리
    """
    reduced = {}
    for code, data in stocks.items():
        reduced[code] = {
            field: data[field]
            for field in KIS_ESSENTIAL_FIELDS
            if field in data
        }
    return reduced


# KIS API 데이터 분석용 프롬프트
KIS_ANALYSIS_PROMPT = """당신은 20년 경력의 대한민국 주식 시장 전문 퀀트 애널리스트입니다.

오늘 날짜: {today}

아래에 한국투자증권 OpenAPI에서 수집한 {count}개 종목의 실시간 데이터가 JSON 형식으로 제공됩니다.

## 1. 데이터 설명
각 종목에는 다음 정보가 포함되어 있습니다:
- **code**: 종목코드
- **name**: 종목명
- **market**: 시장구분 (KOSPI/KOSDAQ)
- **ranking**: 거래량 순위 (volume_rank), 전일대비 거래량 변화율 (volume_rate_vs_prev)
- **price**: 현재가, 등락률, 시고저종, 52주 고저
- **trading**: 거래량, 거래대금, 거래량회전율 (volume_turnover_pct)
- **market_info**: 시가총액 (억원), 상장주수, 외인소진율 (foreign_holding_pct)
- **valuation**: PER, PBR, EPS, BPS
- **order_book**: 총매수잔량, 총매도잔량, 매수/매도 잔량비율 (bid_ask_ratio, 100 이상이면 매수세 우위)
- **investor_flow**: 외인/기관/개인 순매수 동향 (당일, 5일 합계)
- **foreign_institution**: 외인/기관 5일/20일 누적 순매수
- **price_history**: 최근 20거래일 일봉 데이터 (OHLCV) - 추세 분석용
- **price_history.rsi_14**: RSI 14일 지표. null이면 데이터 부족으로 산출 불가.
- **valuation.peg**: PEG 비율 (PER / EPS 성장률). null이면 산출 불가.
- **fundamental** (일부 종목만): ROE, 영업이익률(OPM), 부채비율, EPS 성장률, 매출액 증가율, 영업이익 증가율. ETF 등은 이 필드 생략.

**데이터 결측값 처리**: 특정 필드가 0, null, 또는 누락된 경우 해당 항목은 분석에서 제외하고 유효한 데이터만으로 판단하세요.

## 2. 분석 수행
각 종목에 대해 다음 분석을 가중치에 따라 수행하세요:

### 2-1. 기술적 분석 (가중치 30%)
- 20일 일봉 데이터 기반 추세 판단 (상승/횡보/하락)
- 52주 고저 대비 현재 위치
- 거래량 변화율 및 회전율 분석
- RSI-14 지표: 과매수(>70) / 과매도(<30) / 중립(30~70) 구간 판단

### 2-2. 수급 분석 (가중치 35%)
- 호가 잔량비율 (bid_ask_ratio): 100 이상이면 매수세 우위
- 외인/기관 순매수 동향 (당일 + 5일 누적)
- 외인/기관 20일 누적 순매수 추세

### 2-3. 밸류에이션 분석 (가중치 20%)
- PER/PBR 수준 (동일 업종/섹터 평균 대비 상대적으로 평가하세요. 절대 수치만으로 판단하지 마세요.)
- 시가총액 대비 거래대금 비율
- PEG 비율: <1 저평가, 1~2 적정, >2 고평가 (null이면 생략)
- ROE: 10% 이상 양호, 15% 이상 우수 (fundamental 필드 있을 때)
- 영업이익률(OPM): 업종 특성 고려하여 수익성 판단
- 부채비율: 100% 미만 안정적, 200% 초과 주의

### 2-4. 재료 분석 (가중치 15%)
아래 제공된 뉴스 데이터를 활용하여 각 종목의 재료를 분석하세요.
- 호재/악재 여부 및 시장 심리 판단
- 실적, M&A, 신사업, 규제, 소송 등 주요 재료 파악
- 테마 및 섹터 모멘텀 평가
- 뉴스 시의성: 오늘 날짜 기준 1주일 이내를 '최근'으로 간주하세요.
- 뉴스가 없는 종목: sentiment="중립", catalyst="관련 뉴스 없음"으로 설정하세요.

## 3. 계산 지표 활용
다음 지표들을 직접 계산하여 분석에 반영하세요:

1. **거래량 비율**: volume_rate_vs_prev 활용 (100 이상이면 전일 대비 증가)
2. **가격 모멘텀**: change_rate_pct 활용 (양수면 상승, 음수면 하락)
3. **52주 고저 위치**: (현재가 - 52주저가) / (52주고가 - 52주저가) × 100
4. **수급 강도**: (외인순매수 + 기관순매수) / 시가총액 × 100
5. **호가 압력**: bid_ask_ratio (100 이상 매수세, 100 미만 매도세)
6. **추세 강도**: 20일 일봉에서 상승일 비율
7. **RSI-14**: price_history.rsi_14 활용. >70 과매수, <30 과매도, 30~70 중립
8. **PEG 비율**: valuation.peg 활용. <1 성장 대비 저평가, 1~2 적정, >2 고평가
9. **펀더멘탈 건전성**: fundamental의 ROE, OPM, debt_ratio, sales_growth, op_profit_growth 활용

## 4. 시그널 판단 기준
다음 기준에 따라 시그널을 결정하세요:

| 시그널 | 조건 |
|--------|------|
| **적극매수** | 기술적 강한 상승 신호 + 수급 매수 우위 + 저평가 + 긍정적 재료 (3가지 이상 충족) |
| **매수** | 위 조건 중 2가지 이상 충족, 또는 수급이 강하게 매수 우위 |
| **중립** | 혼조세, 방향성 불명확, 또는 판단 근거 부족 |
| **매도** | 기술적 하락 신호 + 수급 매도 우위 + 부정적 재료 중 1가지 이상 |
| **적극매도** | 기술적 강한 하락 신호 + 수급 매도 우위 + 고평가 + 부정적 재료 (3가지 이상 충족) |

## 5. 신뢰도(confidence) 산정 기준
| 조건 | confidence |
|------|-----------|
| 4개 분석 축(기술/수급/밸류/재료)이 같은 방향 | 0.8~1.0 |
| 3개 축 일치, 1개 상충 | 0.6~0.8 |
| 2개 축 일치, 혼조세 | 0.4~0.6 |
| 데이터 부족 또는 판단 근거 불충분 | 0.2~0.4 |

## 6. 분석 대상 종목 데이터
```json
{stock_data}
```

## 7. 종목별 뉴스 데이터
{news_data}

## 8. 출력 형식
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
        "key_news": ["주요 뉴스 1줄 요약 (최대 5개)"],
        "catalyst": "핵심 재료 요약 (1~2문장)"
      }}
    }}
  ]
}}
```

## 중요 사항
1. 모든 {count}개 종목에 대해 분석 결과를 반드시 포함해야 합니다.
2. 종목과 해당 종목에 대한 분석 결과가 정확히 매칭되도록 주의하세요.
3. 입력 데이터의 종목 순서와 출력 결과의 순서가 동일해야 합니다.
4. 뉴스 데이터가 제공된 종목은 해당 데이터를 기반으로 news_analysis를 작성하세요.
5. 뉴스가 없는 종목은 sentiment="중립", catalyst="관련 뉴스 없음"으로 설정하세요.
"""


def analyze_kis_data(
    stocks_data: dict,
    stock_codes: list[str] | None = None,
    max_retries: int = 3,
    news_data: dict | None = None,
) -> list[dict]:
    """KIS API 데이터 기반 종목 분석

    Args:
        stocks_data: 변환된 KIS 데이터 (kis_gemini.json 형식)
        stock_codes: 분석할 종목 코드 리스트 (없으면 전체)
        max_retries: 최대 재시도 횟수
        news_data: 종목별 뉴스 데이터 {code: [news_list]}

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

    # 데이터 축소 (API 토큰 제한 대응)
    original_json = json.dumps(target_stocks, ensure_ascii=False)
    reduced_stocks = reduce_kis_data(target_stocks)
    reduced_json = json.dumps(reduced_stocks, ensure_ascii=False, indent=2)

    reduction_rate = (1 - len(reduced_json) / len(original_json)) * 100
    print(f"[INFO] 데이터 축소: {len(original_json):,}자 → {len(reduced_json):,}자 ({reduction_rate:.1f}% 감소)")

    # 배치 대상 종목의 뉴스 추출
    batch_news = {}
    if news_data:
        for code in reduced_stocks:
            if code in news_data:
                batch_news[code] = news_data[code]

    if batch_news:
        news_section = "```json\n" + json.dumps(batch_news, ensure_ascii=False, indent=2) + "\n```"
    else:
        news_section = "뉴스 데이터가 제공되지 않았습니다. 뉴스가 없는 종목은 sentiment=\"중립\", catalyst=\"관련 뉴스 없음\"으로 설정하세요."

    # 프롬프트 생성
    today = datetime.now(KST).strftime("%Y-%m-%d")
    prompt = KIS_ANALYSIS_PROMPT.format(
        count=len(reduced_stocks),
        stock_data=reduced_json,
        news_data=news_section,
        today=today
    )
    print(f"[INFO] 프롬프트 길이: {len(prompt):,}자")
    print(f"[INFO] 뉴스 데이터: {len(batch_news)}개 종목\n")

    # API 호출 시도 (429 오류 시에만 재시도, 파싱 실패 시 재시도 안 함)
    for attempt in range(max_retries):
        key_info = get_next_api_key()
        if not key_info:
            print("[ERROR] 사용 가능한 API 키가 없습니다.")
            print(f"[DEBUG] 실패한 키 인덱스: {list(_failed_keys)}")
            return []

        api_key, key_index = key_info
        print(f"[시도 {attempt + 1}/{max_retries}] API 키 #{key_index + 1} 사용 (키 마스킹: {api_key[:8]}...)")

        try:
            client = genai.Client(api_key=api_key)

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
                    "max_output_tokens": 65536,  # 최대 출력 토큰 (기본값 8K → 64K)
                    # google_search 비활성화: 배치당 처리시간 급증으로 80분 timeout 초과
                }
            )

            api_elapsed = time.time() - api_start_time
            print(f"[API] 응답 수신 완료 (소요시간: {api_elapsed:.1f}초)")
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

                if not missing_codes and not extra_codes:
                    print(f"  - ✓ 요청/응답 종목 리스트 완전 일치")

                # 결과 수 검증 (입력 대비 80% 미만이면 경고)
                expected_count = len(target_stocks)
                actual_count = len(analysis_results)
                coverage_rate = (actual_count / expected_count * 100) if expected_count > 0 else 0

                if coverage_rate < 80:
                    print(f"[WARNING] 결과 부족: {actual_count}/{expected_count}개 ({coverage_rate:.1f}%)")
                    print(f"[WARNING] max_output_tokens 한계 또는 모델 처리 한계일 수 있음")

                # 시그널 검증 및 메타데이터 추가
                signal_stats = {}
                for item in analysis_results:
                    if item.get("signal") not in SIGNAL_CATEGORIES:
                        item["signal"] = "중립"
                    item["analysis_time"] = analysis_time
                    item["data_source"] = "KIS_API"
                    # 시그널 통계
                    sig = item.get("signal", "중립")
                    signal_stats[sig] = signal_stats.get(sig, 0) + 1

                print(f"\n[SUCCESS] 분석 완료: {len(analysis_results)}/{expected_count}개 종목 ({coverage_rate:.1f}%)")
                print(f"[INFO] 시그널 분포: {signal_stats}")
                rotate_to_next_key()
                return analysis_results

            # 파싱 실패: 디버깅 로그와 함께 재파싱 시도
            print("[ERROR] 응답 파싱 실패 - API 호출은 성공했으나 JSON 파싱 불가")
            print("[DEBUG] 상세 파싱 로그:")
            parse_json_response(response.text, debug=True)  # 디버그 모드로 재시도하여 로그 출력
            print(f"[DEBUG] 응답 전체 (최대 500자):\n{response.text[:500]}")
            if len(response.text) > 500:
                print(f"[DEBUG] ... (총 {len(response.text)}자 중 500자만 표시)")
            rotate_to_next_key()
            return []  # 파싱 실패 시 빈 결과 반환, 재호출 안 함

        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] [KEY #{key_index + 1}] 오류: {error_msg[:200]}")

            # 429 오류 (쿼터 초과): 다른 키로 재시도
            if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                mark_key_failed(key_index)
                rotate_to_next_key()
                print(f"  [KEY #{key_index + 1}] 실패. 남은 키: {len(GEMINI_API_KEYS) - len(_failed_keys)}개")
                time.sleep(2)
                continue

            if "404" in error_msg:
                print("[ERROR] 모델을 찾을 수 없습니다.")
                return []

            # 기타 오류: 다른 키로 재시도
            rotate_to_next_key()
            time.sleep(1)

    print(f"[ERROR] {max_retries}회 시도 후 실패 (모든 API 키 쿼터 소진)")
    return []


def analyze_kis_data_batch(
    stocks_data: dict,
    batch_size: int = 10,
    max_retries: int = 3,
    news_data: dict | None = None,
) -> list[dict]:
    """KIS API 데이터 배치 분석 (대량 종목용)

    Args:
        stocks_data: 변환된 KIS 데이터
        batch_size: 배치당 종목 수
        max_retries: 최대 재시도 횟수
        news_data: 종목별 뉴스 데이터 {code: [news_list]}

    Returns:
        전체 분석 결과 리스트
    """
    stocks = stocks_data.get("stocks", {})
    all_codes = list(stocks.keys())

    print(f"\n=== KIS 데이터 배치 분석 시작 ===")
    print(f"총 종목: {len(all_codes)}개, 배치 크기: {batch_size}개\n")

    all_results = []

    for i in range(0, len(all_codes), batch_size):
        batch_codes = all_codes[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(all_codes) + batch_size - 1) // batch_size

        print(f"\n--- 배치 {batch_num}/{total_batches} ---")

        results = analyze_kis_data(
            stocks_data,
            stock_codes=batch_codes,
            max_retries=max_retries,
            news_data=news_data,
        )

        if results:
            all_results.extend(results)
            print(f"배치 {batch_num} 완료: {len(results)}개 종목 분석")
        else:
            print(f"배치 {batch_num} 실패")

        # 배치 간 딜레이 (rate limit 방지)
        if i + batch_size < len(all_codes):
            print("다음 배치 대기 중... (3초)")
            time.sleep(3)

    print(f"\n=== 배치 분석 완료 ===")
    print(f"총 분석 완료: {len(all_results)}개 종목")

    return all_results
