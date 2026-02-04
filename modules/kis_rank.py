"""
한국투자증권 순위분석 API
- 거래량 순위
- 등락률 순위 (상승/하락)
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

# KST 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))

from modules.kis_client import KISClient


def safe_int(value, default: int = 0) -> int:
    """빈 문자열이나 None을 안전하게 정수로 변환"""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """빈 문자열이나 None을 안전하게 실수로 변환"""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class KISRankAPI:
    """순위분석 API"""

    def __init__(self, client: KISClient = None):
        """
        Args:
            client: KIS 클라이언트 (없으면 새로 생성)
        """
        self.client = client or KISClient()

    def _determine_market(self, code: str) -> str:
        """종목코드로 시장 구분

        한국거래소 종목코드 규칙:
        - KOSPI: 주로 0~2로 시작하는 6자리 (예: 005930 삼성전자)
        - KOSDAQ: 주로 3~4로 시작하는 6자리 (예: 373220 LG에너지솔루션은 예외)
        - ETN: Q로 시작 (예: Q530036)
        - ETF: 6자리, 1~2로 시작 (예: 114800 KODEX인버스)

        Note: 완벽하지 않으므로 참고용으로만 사용
        """
        if not code:
            return "UNKNOWN"

        # ETN은 Q로 시작
        if code.startswith("Q"):
            return "ETN"

        # 6자리 숫자인 경우
        if len(code) == 6 and code.isdigit():
            first_digit = code[0]
            # 3, 4로 시작하면 대체로 KOSDAQ
            if first_digit in ("3", "4"):
                return "KOSDAQ"
            # 나머지는 KOSPI (ETF 포함)
            return "KOSPI"

        return "UNKNOWN"

    def _is_etf_or_etn(self, code: str, name: str) -> bool:
        """ETF/ETN 여부 판단

        Args:
            code: 종목코드
            name: 종목명

        Returns:
            ETF/ETN이면 True
        """
        # ETN은 Q로 시작
        if code.startswith("Q"):
            return True

        # 종목명에 ETF 운용사 키워드 포함
        etf_keywords = [
            "KODEX", "TIGER", "KBSTAR", "ARIRANG", "HANARO",
            "SOL", "KINDEX", "KOSEF", "ACE", "PLUS", "RISE",
            "ETN", "ETF", "선물", "인버스", "레버리지",
            "채권", "국채", "회사채", "액티브",
        ]
        for keyword in etf_keywords:
            if keyword in name:
                return True

        # 특수 코드 형태 (0000XX 등)
        if code.startswith("0000") or code.startswith("00"):
            if not code[2:].isdigit():  # 0000D0 같은 형태
                return True

        return False

    def _fetch_volume_rank_raw(
        self,
        market_code: str = "0000",
        price_min: str = "",
        price_max: str = "",
    ) -> List[Dict[str, Any]]:
        """거래량순위 원본 API 호출 (내부용)

        Args:
            market_code: 시장 코드
                - "0000": 전종목
                - "0001": 코스피
                - "1001": 코스닥
            price_min: 최소 가격 조건
            price_max: 최대 가격 조건

        Returns:
            API 원본 응답의 output 리스트
        """
        path = "/uapi/domestic-stock/v1/quotations/volume-rank"
        tr_id = "FHPST01710000"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20171",
            "FID_INPUT_ISCD": market_code,
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "0",
            "FID_TRGT_EXLS_CLS_CODE": "0",
            "FID_INPUT_PRICE_1": price_min,
            "FID_INPUT_PRICE_2": price_max,
            "FID_VOL_CNT": "",
            "FID_INPUT_DATE_1": "",
        }

        result = self.client.request("GET", path, tr_id, params=params)

        if result.get("rt_cd") != "0":
            raise Exception(f"API 오류: {result.get('msg1', 'Unknown error')}")

        return result.get("output", [])

    def _collect_extended_stocks(self, market_code: str = "0000") -> List[Dict[str, Any]]:
        """가격대별 분할 조회로 확장된 종목 수집

        KIS API는 1회 최대 30개만 반환하므로,
        가격대별로 세분화하여 분할 조회합니다.

        Args:
            market_code: 시장 코드
                - "0000": 전종목
                - "0001": 코스피
                - "1001": 코스닥

        Returns:
            중복 제거된 전체 종목 리스트 (거래량 순 정렬)
        """
        # 세분화된 가격대 (15개 구간 → 최대 450개 종목 수집 가능)
        price_ranges = [
            ("", "500"),
            ("500", "1000"),
            ("1000", "2000"),
            ("2000", "3000"),
            ("3000", "5000"),
            ("5000", "7000"),
            ("7000", "10000"),
            ("10000", "15000"),
            ("15000", "20000"),
            ("20000", "30000"),
            ("30000", "50000"),
            ("50000", "70000"),
            ("70000", "100000"),
            ("100000", "150000"),
            ("150000", ""),
        ]

        all_stocks = []
        seen_codes = set()

        for price_min, price_max in price_ranges:
            stocks = self._fetch_volume_rank_raw(market_code, price_min, price_max)
            for stock in stocks:
                code = stock.get("mksc_shrn_iscd", "")
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    all_stocks.append(stock)

        # 거래량 기준 정렬
        all_stocks.sort(key=lambda x: safe_int(x.get("acml_vol", 0)), reverse=True)

        return all_stocks

    def get_volume_rank(
        self,
        market: str = "ALL",
        limit: int = 30,
        exclude_etf: bool = False,
        extended: bool = True,
    ) -> List[Dict[str, Any]]:
        """거래량순위 조회

        Args:
            market: 시장 구분
                - "ALL": 전체
                - "KOSPI": 코스피
                - "KOSDAQ": 코스닥
            limit: 조회 건수
            exclude_etf: ETF/ETN 제외 여부
            extended: 확장 조회 모드 (가격대별 분할 조회로 더 많은 종목 수집)

        Returns:
            거래량 순위 종목 리스트
        """
        # 시장 코드 매핑 (FID_INPUT_ISCD)
        # - "0001": 코스피
        # - "1001": 코스닥
        # - "0000": 전종목 (실제로는 코스피만 반환되는 문제 있음)
        market_upper = market.upper()

        # 시장별로 API 호출
        if market_upper == "KOSPI":
            market_codes = ["0001"]
        elif market_upper == "KOSDAQ":
            market_codes = ["1001"]
        else:  # ALL
            # 전종목은 코스피 + 코스닥 각각 조회하여 병합
            market_codes = ["0001", "1001"]

        # 시장 코드 → 시장명 매핑
        market_code_to_name = {
            "0001": "KOSPI",
            "1001": "KOSDAQ",
        }

        # 종목 수집 (시장 정보 포함)
        all_stocks = []
        seen_codes = set()

        for market_code in market_codes:
            # API 호출 시 사용한 market_code로 시장 결정
            actual_market = market_code_to_name.get(market_code, "UNKNOWN")

            if extended and exclude_etf:
                stocks = self._collect_extended_stocks(market_code)
            else:
                stocks = self._fetch_volume_rank_raw(market_code)

            for stock in stocks:
                code = stock.get("mksc_shrn_iscd", "")
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    # 시장 정보를 stock에 추가
                    stock["_market"] = actual_market
                    all_stocks.append(stock)

        # 거래량 기준 정렬 (여러 시장 병합 시 필요)
        all_stocks.sort(key=lambda x: safe_int(x.get("acml_vol", 0)), reverse=True)

        # 결과 정리 및 필터링
        parsed = []
        for stock in all_stocks:
            code = stock.get("mksc_shrn_iscd", "")
            name = stock.get("hts_kor_isnm", "")
            # API 호출 시 결정된 시장 사용 (추측 대신 실제 값)
            stock_market = stock.get("_market", self._determine_market(code))
            is_etf = self._is_etf_or_etn(code, name)

            # ETF/ETN 제외 필터
            if exclude_etf and is_etf:
                continue

            parsed.append({
                "rank": len(parsed) + 1,
                "code": code,
                "name": name,
                "current_price": safe_int(stock.get("stck_prpr", 0)),
                "change_rate": safe_float(stock.get("prdy_ctrt", 0)),
                "change_price": safe_int(stock.get("prdy_vrss", 0)),
                "volume": safe_int(stock.get("acml_vol", 0)),
                "volume_rate": safe_float(stock.get("vol_inrt", 0)),
                "trading_value": safe_int(stock.get("acml_tr_pbmn", 0)),
                "market": stock_market,
                "is_etf": is_etf,
            })

            if len(parsed) >= limit:
                break

        return parsed

    def get_fluctuation_rank(
        self,
        market: str = "ALL",
        direction: str = "UP",
        limit: int = 30,
        exclude_etf: bool = False,
        extended: bool = True,
    ) -> List[Dict[str, Any]]:
        """등락률순위 조회

        Note: KIS API의 등락률순위 전용 API가 불안정하여,
              거래량순위 API 데이터를 등락률 기준으로 정렬하여 반환합니다.

        Args:
            market: 시장 구분 ("ALL", "KOSPI", "KOSDAQ")
            direction: 상승/하락 ("UP": 상승, "DOWN": 하락)
            limit: 조회 건수
            exclude_etf: ETF/ETN 제외 여부
            extended: 확장 조회 모드

        Returns:
            등락률 순위 종목 리스트
        """
        # 거래량 순위 API에서 전체 데이터 가져오기 (등락률 정보 포함)
        volume_data = self.get_volume_rank(
            market=market, limit=500, exclude_etf=exclude_etf, extended=extended
        )

        # 등락률 기준 정렬
        if direction.upper() == "UP":
            # 상승률 순 (높은 순)
            sorted_data = sorted(volume_data, key=lambda x: x["change_rate"], reverse=True)
            # 양수 등락률만 필터링
            sorted_data = [s for s in sorted_data if s["change_rate"] > 0]
        else:
            # 하락률 순 (낮은 순)
            sorted_data = sorted(volume_data, key=lambda x: x["change_rate"])
            # 음수 등락률만 필터링
            sorted_data = [s for s in sorted_data if s["change_rate"] < 0]

        # 순위 재계산 및 방향 추가
        result = []
        for idx, stock in enumerate(sorted_data[:limit]):
            stock_copy = stock.copy()
            stock_copy["rank"] = idx + 1
            stock_copy["direction"] = direction.upper()
            result.append(stock_copy)

        return result

    def get_top30_by_volume(
        self,
        exclude_etf: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """코스피/코스닥 거래량 Top30 조회

        Args:
            exclude_etf: ETF/ETN 제외 여부 (기본값: True)

        Returns:
            {
                "kospi": [...],
                "kosdaq": [...],
                "collected_at": "2024-01-01T12:00:00"
            }
        """
        return {
            "kospi": self.get_volume_rank(market="KOSPI", limit=30, exclude_etf=exclude_etf),
            "kosdaq": self.get_volume_rank(market="KOSDAQ", limit=30, exclude_etf=exclude_etf),
            "collected_at": datetime.now(KST).isoformat(),
            "category": "volume",
            "exclude_etf": exclude_etf,
        }

    def get_top30_by_fluctuation(
        self,
        exclude_etf: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """코스피/코스닥 등락률 Top30 조회 (상승 + 하락)

        Args:
            exclude_etf: ETF/ETN 제외 여부 (기본값: True)

        Returns:
            {
                "kospi_up": [...],
                "kospi_down": [...],
                "kosdaq_up": [...],
                "kosdaq_down": [...],
                "collected_at": "2024-01-01T12:00:00"
            }
        """
        return {
            "kospi_up": self.get_fluctuation_rank(market="KOSPI", direction="UP", limit=30, exclude_etf=exclude_etf),
            "kospi_down": self.get_fluctuation_rank(market="KOSPI", direction="DOWN", limit=30, exclude_etf=exclude_etf),
            "kosdaq_up": self.get_fluctuation_rank(market="KOSDAQ", direction="UP", limit=30, exclude_etf=exclude_etf),
            "kosdaq_down": self.get_fluctuation_rank(market="KOSDAQ", direction="DOWN", limit=30, exclude_etf=exclude_etf),
            "collected_at": datetime.now(KST).isoformat(),
            "category": "fluctuation",
            "exclude_etf": exclude_etf,
        }

    def get_all_top30(
        self,
        exclude_etf: bool = True,
    ) -> Dict[str, Any]:
        """거래량 + 등락률 Top30 종합 조회

        Args:
            exclude_etf: ETF/ETN 제외 여부 (기본값: True)

        Returns:
            종합 Top30 데이터
        """
        print(f"[KIS] 거래량 Top30 조회 중... (ETF 제외: {exclude_etf})")
        volume_data = self.get_top30_by_volume(exclude_etf=exclude_etf)

        print(f"[KIS] 등락률 Top30 조회 중... (ETF 제외: {exclude_etf})")
        fluctuation_data = self.get_top30_by_fluctuation(exclude_etf=exclude_etf)

        # 중복 제거된 전체 종목 코드 리스트
        all_codes = set()
        for stocks in [
            volume_data.get("kospi", []),
            volume_data.get("kosdaq", []),
            fluctuation_data.get("kospi_up", []),
            fluctuation_data.get("kospi_down", []),
            fluctuation_data.get("kosdaq_up", []),
            fluctuation_data.get("kosdaq_down", []),
        ]:
            for stock in stocks:
                all_codes.add(stock["code"])

        return {
            "volume": volume_data,
            "fluctuation": fluctuation_data,
            "unique_stock_codes": list(all_codes),
            "unique_stock_count": len(all_codes),
            "collected_at": datetime.now(KST).isoformat(),
        }


def test_rank_api():
    """순위 API 테스트"""
    try:
        api = KISRankAPI()

        print("=" * 60)
        print("[거래량 Top30 조회 테스트]")
        print("=" * 60)

        # 코스피 거래량 Top 10
        print("\n[코스피 거래량 Top 10]")
        kospi_vol = api.get_volume_rank(market="KOSPI", limit=10)
        for stock in kospi_vol:
            print(f"  {stock['rank']:2d}. {stock['name']:<15s} ({stock['code']}) "
                  f"| {stock['current_price']:>10,}원 | {stock['change_rate']:>+6.2f}% | "
                  f"거래량: {stock['volume']:>15,}")

        # 코스닥 거래량 Top 10
        print("\n[코스닥 거래량 Top 10]")
        kosdaq_vol = api.get_volume_rank(market="KOSDAQ", limit=10)
        for stock in kosdaq_vol:
            print(f"  {stock['rank']:2d}. {stock['name']:<15s} ({stock['code']}) "
                  f"| {stock['current_price']:>10,}원 | {stock['change_rate']:>+6.2f}% | "
                  f"거래량: {stock['volume']:>15,}")

        print("\n" + "=" * 60)
        print("[등락률 Top 10 조회 테스트]")
        print("=" * 60)

        # 코스피 상승률 Top 10
        print("\n[코스피 상승률 Top 10]")
        kospi_up = api.get_fluctuation_rank(market="KOSPI", direction="UP", limit=10)
        for stock in kospi_up:
            print(f"  {stock['rank']:2d}. {stock['name']:<15s} ({stock['code']}) "
                  f"| {stock['current_price']:>10,}원 | {stock['change_rate']:>+6.2f}%")

        # 코스피 하락률 Top 10
        print("\n[코스피 하락률 Top 10]")
        kospi_down = api.get_fluctuation_rank(market="KOSPI", direction="DOWN", limit=10)
        for stock in kospi_down:
            print(f"  {stock['rank']:2d}. {stock['name']:<15s} ({stock['code']}) "
                  f"| {stock['current_price']:>10,}원 | {stock['change_rate']:>+6.2f}%")

    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_rank_api()
