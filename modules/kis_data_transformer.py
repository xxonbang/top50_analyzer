"""
KIS 데이터 변환기 - Gemini 분석용 통합 포맷
- 종목 코드 기준으로 모든 데이터를 단일 객체로 통합
- Gemini가 이해하기 쉬운 명확한 구조로 변환
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

# KST 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import KIS_OUTPUT_DIR


class KISDataTransformer:
    """KIS 데이터를 Gemini 분석용으로 변환"""

    def __init__(self):
        self.output_dir = KIS_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_raw_data(self, filename: str = "kis_latest.json") -> Dict[str, Any]:
        """원본 데이터 로드"""
        filepath = self.output_dir / filename
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def transform_for_gemini(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gemini가 이해하기 쉬운 통합 포맷으로 변환

        변환 전:
            - rankings: { kospi: [...], kosdaq: [...] }
            - stock_details: { "005930": {...}, ... }

        변환 후:
            - stocks: {
                "005930": {
                    기본정보, 순위정보, 가격정보, 투자자동향, 재무정보 등 모든 데이터 통합
                }
              }
        """
        print("[TRANSFORM] KIS 데이터 변환 시작...")

        meta = raw_data.get("meta", {})
        rankings = raw_data.get("rankings", {})
        stock_details = raw_data.get("stock_details", {})

        print(f"[TRANSFORM] 입력 데이터:")
        print(f"  - meta 키: {list(meta.keys())}")
        print(f"  - rankings 키: {list(rankings.keys())}")
        print(f"  - kospi 종목 수: {len(rankings.get('kospi', []))}")
        print(f"  - kosdaq 종목 수: {len(rankings.get('kosdaq', []))}")
        print(f"  - stock_details 종목 수: {len(stock_details)}")

        # 순위 정보를 종목코드 기준 맵으로 변환
        ranking_map = self._build_ranking_map(rankings)

        # 종목별 통합 데이터 생성
        stocks = {}
        for code, details in stock_details.items():
            stocks[code] = self._merge_stock_data(
                code=code,
                ranking_info=ranking_map.get(code),
                details=details,
            )

        # 통합 결과
        result = {
            "meta": {
                "format_version": "2.0",
                "format_description": "종목별 통합 데이터 (Gemini 분석용)",
                "original_collected_at": meta.get("collected_at"),
                "transformed_at": datetime.now(KST).isoformat(),
                "total_stocks": len(stocks),
                "kospi_count": meta.get("kospi_count", 0),
                "kosdaq_count": meta.get("kosdaq_count", 0),
                "data_source": "한국투자증권 OpenAPI",
            },
            "stocks": stocks,
        }

        # 변환 결과 요약
        result_json = json.dumps(result, ensure_ascii=False)
        print(f"[TRANSFORM] 변환 완료:")
        print(f"  - 출력 종목 수: {len(stocks)}")
        print(f"  - 출력 데이터 크기: {len(result_json):,}자")
        if stocks:
            sample_code = list(stocks.keys())[0]
            sample_keys = list(stocks[sample_code].keys())
            print(f"  - 샘플 종목({sample_code}) 필드: {sample_keys}")

        return result

    def _build_ranking_map(self, rankings: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """순위 데이터를 종목코드 기준 맵으로 변환"""
        ranking_map = {}

        # 코스피 순위
        for stock in rankings.get("kospi", []):
            code = stock.get("code")
            if code:
                ranking_map[code] = {
                    "market": "KOSPI",
                    "name": stock.get("name"),  # 종목명 추가
                    "volume_rank": stock.get("rank"),
                    "volume": stock.get("volume"),
                    "volume_rate": stock.get("volume_rate"),
                    "trading_value": stock.get("trading_value"),
                }

        # 코스닥 순위
        for stock in rankings.get("kosdaq", []):
            code = stock.get("code")
            if code:
                ranking_map[code] = {
                    "market": "KOSDAQ",
                    "name": stock.get("name"),  # 종목명 추가
                    "volume_rank": stock.get("rank"),
                    "volume": stock.get("volume"),
                    "volume_rate": stock.get("volume_rate"),
                    "trading_value": stock.get("trading_value"),
                }

        return ranking_map

    def _merge_stock_data(
        self,
        code: str,
        ranking_info: Optional[Dict[str, Any]],
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """종목별 모든 데이터를 단일 객체로 통합"""

        current_price = details.get("current_price", {})
        asking_price = details.get("asking_price", {})
        investor_trend = details.get("investor_trend", {})
        investor_trend_estimate = details.get("investor_trend_estimate", {})
        daily_chart = details.get("daily_chart", {})
        foreign_inst = details.get("foreign_institution_summary", {})
        financial_info = details.get("financial_info", {})

        # 종목명: ranking_info에서 가져오거나 daily_chart에서 가져옴
        stock_name = ""
        if ranking_info:
            stock_name = ranking_info.get("name", "")
        if not stock_name:
            stock_name = daily_chart.get("stock_name", current_price.get("stock_name", ""))

        # 기본 정보
        stock_data = {
            # === 기본 정보 ===
            "code": code,
            "name": stock_name,
            "market": ranking_info.get("market", "UNKNOWN") if ranking_info else "UNKNOWN",

            # === 순위 정보 ===
            "ranking": {
                "volume_rank": ranking_info.get("volume_rank") if ranking_info else None,
                "volume": ranking_info.get("volume") if ranking_info else None,
                "volume_rate_vs_prev": ranking_info.get("volume_rate") if ranking_info else None,
                "trading_value": ranking_info.get("trading_value") if ranking_info else None,
                "description": "거래량 기준 시장 내 순위 (1=최다 거래량)",
            },

            # === 현재가 및 등락 ===
            "price": {
                "current": current_price.get("current_price"),
                "change": current_price.get("change_price"),
                "change_rate_pct": current_price.get("change_rate"),
                "open": current_price.get("open_price"),
                "high": current_price.get("high_price"),
                "low": current_price.get("low_price"),
                "prev_close": current_price.get("prev_close"),
                "high_52week": current_price.get("high_52week"),
                "low_52week": current_price.get("low_52week"),
            },

            # === 거래 정보 ===
            "trading": {
                "volume": current_price.get("volume"),
                "trading_value": current_price.get("trading_value"),
                "volume_turnover_pct": current_price.get("volume_turnover"),
            },

            # === 시가총액 및 주식 정보 ===
            "market_info": {
                "market_cap_billion": current_price.get("market_cap"),
                "shares_outstanding": current_price.get("shares_outstanding"),
                "foreign_holding_pct": current_price.get("foreign_ratio"),
            },

            # === 밸류에이션 ===
            "valuation": {
                "per": current_price.get("per"),
                "pbr": current_price.get("pbr"),
                "eps": current_price.get("eps"),
                "bps": current_price.get("bps"),
            },

            # === 호가 정보 ===
            "order_book": self._transform_order_book(asking_price),

            # === 투자자별 매매동향 ===
            "investor_flow": self._transform_investor_trend(investor_trend, investor_trend_estimate),

            # === 외인/기관 동향 요약 ===
            "foreign_institution": self._transform_foreign_institution(foreign_inst),

            # === 일봉 차트 (최근 20일) ===
            "price_history": self._transform_daily_chart(daily_chart),
        }

        # === 펀더멘탈 (유효한 데이터가 있을 때만) ===
        fundamental = self._transform_financial_info(financial_info)
        if fundamental:
            stock_data["fundamental"] = fundamental

            # PEG 계산: PER / EPS 성장률
            per = current_price.get("per")
            eps_growth = fundamental.get("eps_growth_rate")
            if per and eps_growth and eps_growth > 0:
                stock_data["valuation"]["peg"] = round(per / eps_growth, 2)
            else:
                stock_data["valuation"]["peg"] = None
        else:
            stock_data["valuation"]["peg"] = None

        return stock_data

    def _transform_order_book(self, asking_price: Dict[str, Any]) -> Dict[str, Any]:
        """호가 정보 변환"""
        if not asking_price:
            return {}

        ask_prices = asking_price.get("ask_prices", [])
        bid_prices = asking_price.get("bid_prices", [])

        return {
            "total_ask_volume": asking_price.get("total_ask_volume"),
            "total_bid_volume": asking_price.get("total_bid_volume"),
            "bid_ask_ratio": round(
                asking_price.get("total_bid_volume", 0) /
                asking_price.get("total_ask_volume", 1) * 100, 2
            ) if asking_price.get("total_ask_volume", 0) > 0 else None,
            "best_ask": ask_prices[0] if ask_prices else None,
            "best_bid": bid_prices[0] if bid_prices else None,
            "description": "bid_ask_ratio > 100: 매수세 우위, < 100: 매도세 우위",
        }

    def _transform_investor_trend(
        self,
        investor_trend: Dict[str, Any],
        investor_trend_estimate: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """투자자별 매매동향 변환 (일자별 투자자 동향 데이터)"""
        if not investor_trend:
            return {}

        daily_trend = investor_trend.get("daily_investor_trend", [])

        # 최근 5일 데이터 추출
        recent_days = daily_trend[:5] if daily_trend else []

        # 오늘(가장 최근) 데이터 - 장중에는 0일 수 있음
        today = recent_days[0] if recent_days else {}

        # 5일 합계 계산
        foreign_5d = sum(d.get("foreign_net", 0) for d in recent_days)
        organ_5d = sum(d.get("organ_net", 0) for d in recent_days)
        individual_5d = sum(d.get("individual_net", 0) for d in recent_days)

        # 추정 데이터가 있으면 today 필드를 추정 데이터로 대체
        is_estimated = False
        if investor_trend_estimate and not investor_trend_estimate.get("error") and investor_trend_estimate.get("is_estimated"):
            estimated = investor_trend_estimate.get("estimated_data", {})
            is_estimated = True
            today_data = {
                "date": today.get("date"),
                "foreign_net": estimated.get("foreign_net"),
                "institution_net": estimated.get("institution_net"),
                "individual_net": None,  # 개인은 추정 불가
            }
        else:
            today_data = {
                "date": today.get("date"),
                "foreign_net": today.get("foreign_net"),
                "institution_net": today.get("organ_net"),
                "individual_net": today.get("individual_net"),
            }

        result = {
            "today": today_data,
            "sum_5_days": {
                "foreign_net": foreign_5d,
                "institution_net": organ_5d,
                "individual_net": individual_5d,
            },
            "daily_trend": [
                {
                    "date": d.get("date"),
                    "foreign_net": d.get("foreign_net"),
                    "institution_net": d.get("organ_net"),
                    "individual_net": d.get("individual_net"),
                }
                for d in recent_days
            ],
            "description": "양수=순매수, 음수=순매도. foreign=외국인, institution=기관, individual=개인",
        }

        if is_estimated:
            result["is_estimated"] = True

        return result

    def _transform_foreign_institution(self, foreign_inst: Dict[str, Any]) -> Dict[str, Any]:
        """외인/기관 동향 요약 변환"""
        if not foreign_inst:
            return {}

        today = foreign_inst.get("today", {})
        summary_5d = foreign_inst.get("summary_5d", {})
        summary_20d = foreign_inst.get("summary_20d", {})

        return {
            "today": {
                "date": today.get("date"),
                "foreign_net": today.get("foreign_net"),
                "institution_net": today.get("organ_net"),
                "individual_net": today.get("individual_net"),
            },
            "sum_5_days": {
                "foreign_net": summary_5d.get("foreign_net"),
                "institution_net": summary_5d.get("organ_net"),
                "individual_net": summary_5d.get("individual_net"),
            },
            "sum_20_days": {
                "foreign_net": summary_20d.get("foreign_net"),
                "institution_net": summary_20d.get("organ_net"),
                "individual_net": summary_20d.get("individual_net"),
            },
            "description": "양수=순매수, 음수=순매도. 5일/20일 누적 합계",
        }

    @staticmethod
    def _calculate_rsi(close_prices: list, period: int = 14) -> Optional[float]:
        """Wilder's smoothed RSI 계산

        Args:
            close_prices: 시간순(오래된→최근) close 가격 리스트
            period: RSI 기간 (기본 14)

        Returns:
            RSI 값 (0~100) 또는 데이터 부족 시 None
        """
        if not close_prices or len(close_prices) < period + 1:
            return None

        # 가격 변동 계산
        deltas = [close_prices[i] - close_prices[i - 1] for i in range(1, len(close_prices))]

        # 초기 평균 (첫 period개)
        gains = [d if d > 0 else 0 for d in deltas[:period]]
        losses = [-d if d < 0 else 0 for d in deltas[:period]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        # Wilder's smoothing (나머지 구간)
        for d in deltas[period:]:
            gain = d if d > 0 else 0
            loss = -d if d < 0 else 0
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)

    def _transform_financial_info(self, financial_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """재무정보를 펀더멘탈 데이터로 변환

        Args:
            financial_info: get_financial_info() 결과 (재무비율 + 손익계산서 병합)

        Returns:
            펀더멘탈 딕셔너리 또는 데이터 없으면 None
        """
        if not financial_info or financial_info.get("error"):
            return None

        financial_data = financial_info.get("financial_data", [])
        if not financial_data:
            return None

        # 유효한(non-zero) 최신 연도 탐색 — 재무비율 또는 손익계산서 데이터 존재
        latest = None
        for item in financial_data:
            roe = item.get("roe", 0)
            eps = item.get("eps", 0)
            sales = item.get("sales", 0)
            if roe != 0 or eps != 0 or sales != 0:
                latest = item
                break

        if latest is None:
            return None

        roe = latest.get("roe", 0)
        debt_ratio = latest.get("debt_ratio", 0)
        sales = latest.get("sales", 0)
        operating_profit = latest.get("operating_profit", 0)

        # OPM (영업이익률) 계산 — 손익계산서 데이터 사용
        opm = round(operating_profit / sales * 100, 2) if sales != 0 else None

        # EPS 성장률 (YoY) 계산 — 최신과 그 다음 유효 연도 비교
        eps_growth_rate = None
        if len(financial_data) >= 2:
            prev = None
            for item in financial_data[1:]:
                prev_roe = item.get("roe", 0)
                prev_eps = item.get("eps", 0)
                prev_sales = item.get("sales", 0)
                if prev_roe != 0 or prev_eps != 0 or prev_sales != 0:
                    prev = item
                    break

            if prev:
                curr_eps = latest.get("eps", 0)
                prev_eps = prev.get("eps", 0)
                if prev_eps and prev_eps != 0:
                    eps_growth_rate = round((curr_eps - prev_eps) / abs(prev_eps) * 100, 2)

        # 매출액/영업이익 증가율 — 재무비율 API에서 직접 제공
        sales_growth = latest.get("sales_growth", 0)
        op_profit_growth = latest.get("op_profit_growth", 0)

        result = {
            "roe": roe if roe != 0 else None,
            "opm": opm,
            "debt_ratio": debt_ratio if debt_ratio != 0 else None,
            "eps_growth_rate": eps_growth_rate,
            "sales_growth": sales_growth if sales_growth != 0 else None,
            "op_profit_growth": op_profit_growth if op_profit_growth != 0 else None,
            "latest_year": latest.get("year", ""),
        }

        # 모든 값이 None이면 반환하지 않음
        if all(v is None for k, v in result.items() if k != "latest_year"):
            return None

        return result

    def _transform_daily_chart(self, daily_chart: Dict[str, Any]) -> Dict[str, Any]:
        """일봉 차트 데이터 변환 (최근 20일 + RSI-14)"""
        if not daily_chart:
            return {}

        ohlcv = daily_chart.get("ohlcv", [])
        if not ohlcv:
            return {}

        # RSI 계산: 전체 OHLCV(최대 41일)를 시간순으로 정렬하여 계산
        # ohlcv는 최신→과거 순이므로 reversed
        all_closes = [c.get("close", 0) for c in reversed(ohlcv) if c.get("close")]
        rsi_14 = self._calculate_rsi(all_closes, period=14)

        # 최근 20일만 포함
        recent = ohlcv[:20]

        return {
            "days": [
                {
                    "date": c.get("date"),
                    "open": c.get("open"),
                    "high": c.get("high"),
                    "low": c.get("low"),
                    "close": c.get("close"),
                    "volume": c.get("volume"),
                }
                for c in recent
            ],
            "count": len(recent),
            "rsi_14": rsi_14,
        }

    def save_transformed_data(
        self,
        data: Dict[str, Any],
        filename: str = "kis_gemini.json",
    ) -> Path:
        """변환된 데이터 저장"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[Transformer] 저장 완료: {filepath}")
        return filepath

    def run(
        self,
        input_file: str = "kis_latest.json",
        output_file: str = "kis_gemini.json",
    ) -> Dict[str, Any]:
        """데이터 변환 실행

        Args:
            input_file: 입력 파일명
            output_file: 출력 파일명

        Returns:
            변환된 데이터
        """
        print(f"[Transformer] 데이터 로드: {input_file}")
        raw_data = self.load_raw_data(input_file)

        print("[Transformer] Gemini 분석용 포맷으로 변환 중...")
        transformed = self.transform_for_gemini(raw_data)

        print(f"[Transformer] 총 {len(transformed['stocks'])}개 종목 변환 완료")
        self.save_transformed_data(transformed, output_file)

        # 타임스탬프 파일도 저장
        timestamp = datetime.now(KST).strftime("%Y%m%d_%H%M%S")
        self.save_transformed_data(transformed, f"kis_gemini_{timestamp}.json")

        return transformed


def generate_gemini_prompt(data: Dict[str, Any], stock_codes: List[str] = None) -> str:
    """Gemini 분석 요청용 프롬프트 생성

    Args:
        data: 변환된 데이터
        stock_codes: 분석할 종목 코드 리스트 (없으면 전체)

    Returns:
        Gemini 프롬프트 문자열
    """
    stocks = data.get("stocks", {})

    if stock_codes:
        selected = {code: stocks[code] for code in stock_codes if code in stocks}
    else:
        selected = stocks

    prompt = f"""다음은 한국 주식시장 종목 데이터입니다. 각 종목에 대해 투자 시그널을 분석해주세요.

## 데이터 수집 정보
- 수집 시간: {data['meta'].get('original_collected_at')}
- 총 종목 수: {len(selected)}개
- 데이터 출처: 한국투자증권 OpenAPI

## 분석 대상 종목 데이터
```json
{json.dumps(selected, ensure_ascii=False, indent=2)}
```

## 분석 요청
각 종목에 대해 다음을 분석해주세요:

1. **투자 시그널**: 강력매수 / 매수 / 중립 / 매도 / 강력매도
2. **시그널 근거**: 주요 지표 기반 판단 이유 (2-3문장)
3. **주요 관찰점**:
   - 거래량 동향 (전일 대비 변화율)
   - 투자자 동향 (외인/기관 순매수 여부)
   - 밸류에이션 (PER/PBR 수준)
   - 차트 패턴 (최근 20일 추세)

## 응답 형식
JSON 형식으로 응답해주세요:
```json
{{
  "analysis_date": "YYYY-MM-DD",
  "stocks": {{
    "종목코드": {{
      "name": "종목명",
      "signal": "강력매수|매수|중립|매도|강력매도",
      "signal_reason": "시그널 판단 근거",
      "observations": {{
        "volume": "거래량 동향 분석",
        "investor_flow": "투자자 동향 분석",
        "valuation": "밸류에이션 분석",
        "trend": "차트 추세 분석"
      }},
      "risk_factors": ["리스크 요인1", "리스크 요인2"],
      "confidence": 0.0-1.0
    }}
  }}
}}
```
"""
    return prompt


def main():
    """메인 실행"""
    transformer = KISDataTransformer()
    data = transformer.run()

    # 샘플 프롬프트 생성 (상위 5개 종목)
    sample_codes = list(data["stocks"].keys())[:5]
    prompt = generate_gemini_prompt(data, sample_codes)

    print("\n" + "=" * 60)
    print("[샘플 Gemini 프롬프트 - 상위 5개 종목]")
    print("=" * 60)
    print(prompt[:2000] + "...\n")


if __name__ == "__main__":
    main()
