"""
한국투자증권 종목 상세 데이터 API
- 현재가 시세
- 호가 정보
- 투자자 동향
- 회원사 매매현황
- 기간별 시세
- 당일 체결 데이터
"""
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from modules.kis_client import KISClient


class KISStockDetailAPI:
    """종목 상세 데이터 API"""

    def __init__(self, client: KISClient = None):
        """
        Args:
            client: KIS 클라이언트 (없으면 새로 생성)
        """
        self.client = client or KISClient()

    def get_current_price(self, stock_code: str) -> Dict[str, Any]:
        """주식현재가 시세 조회

        Returns:
            현재가, 전일대비, 등락률, 거래량 등 기본 시세 정보
        """
        path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        tr_id = "FHKST01010100"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
        }

        result = self.client.request("GET", path, tr_id, params=params)

        if result.get("rt_cd") != "0":
            return {"error": result.get("msg1", "Unknown error")}

        output = result.get("output", {})

        return {
            "stock_code": stock_code,
            "stock_name": output.get("rprs_mrkt_kor_name", ""),        # 종목명
            "current_price": int(output.get("stck_prpr", 0)),         # 현재가
            "change_price": int(output.get("prdy_vrss", 0)),          # 전일대비
            "change_rate": float(output.get("prdy_ctrt", 0)),         # 등락률
            "change_sign": output.get("prdy_vrss_sign", ""),          # 부호 (1:상승, 2:하락, 3:보합)
            "open_price": int(output.get("stck_oprc", 0)),            # 시가
            "high_price": int(output.get("stck_hgpr", 0)),            # 고가
            "low_price": int(output.get("stck_lwpr", 0)),             # 저가
            "prev_close": int(output.get("stck_sdpr", 0)),            # 전일종가
            "volume": int(output.get("acml_vol", 0)),                 # 누적거래량
            "trading_value": int(output.get("acml_tr_pbmn", 0)),      # 누적거래대금
            "high_52week": int(output.get("stck_mxpr", 0)),           # 52주 최고가
            "low_52week": int(output.get("stck_llam", 0)),            # 52주 최저가
            "per": float(output.get("per", 0) or 0),                  # PER
            "pbr": float(output.get("pbr", 0) or 0),                  # PBR
            "eps": float(output.get("eps", 0) or 0),                  # EPS
            "bps": float(output.get("bps", 0) or 0),                  # BPS
            "market_cap": int(output.get("hts_avls", 0)),             # 시가총액 (억원)
            "shares_outstanding": int(output.get("lstn_stcn", 0)),    # 상장주수
            "foreign_ratio": float(output.get("hts_frgn_ehrt", 0)),   # 외국인소진율
            "volume_turnover": float(output.get("vol_tnrt", 0)),      # 거래량회전율
        }

    def get_asking_price(self, stock_code: str) -> Dict[str, Any]:
        """주식현재가 호가/예상체결 조회

        Returns:
            10단계 매수/매도 호가 정보
        """
        path = "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn"
        tr_id = "FHKST01010200"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
        }

        result = self.client.request("GET", path, tr_id, params=params)

        if result.get("rt_cd") != "0":
            return {"error": result.get("msg1", "Unknown error")}

        output = result.get("output1", {})
        output2 = result.get("output2", {})

        # 10단계 호가 파싱
        ask_prices = []  # 매도호가 (1~10)
        bid_prices = []  # 매수호가 (1~10)

        for i in range(1, 11):
            ask_prices.append({
                "price": int(output.get(f"askp{i}", 0)),
                "volume": int(output.get(f"askp_rsqn{i}", 0)),
            })
            bid_prices.append({
                "price": int(output.get(f"bidp{i}", 0)),
                "volume": int(output.get(f"bidp_rsqn{i}", 0)),
            })

        return {
            "stock_code": stock_code,
            "ask_prices": ask_prices,                                    # 매도호가
            "bid_prices": bid_prices,                                    # 매수호가
            "total_ask_volume": int(output.get("total_askp_rsqn", 0)),  # 총매도잔량
            "total_bid_volume": int(output.get("total_bidp_rsqn", 0)),  # 총매수잔량
            "expected_price": int(output2.get("antc_cnpr", 0)),         # 예상체결가
            "expected_volume": int(output2.get("antc_vol", 0)),         # 예상체결량
            "expected_change_rate": float(output2.get("antc_cntg_prdy_ctrt", 0)),  # 예상등락률
        }

    def get_investor_trend(self, stock_code: str) -> Dict[str, Any]:
        """주식현재가 투자자 조회 (최근 30일)

        Returns:
            개인/외국인/기관 매매 동향
        """
        path = "/uapi/domestic-stock/v1/quotations/inquire-investor"
        tr_id = "FHKST01010900"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
        }

        result = self.client.request("GET", path, tr_id, params=params)

        if result.get("rt_cd") != "0":
            return {"error": result.get("msg1", "Unknown error")}

        output = result.get("output", [])

        # 일별 투자자 동향
        daily_data = []
        for item in output[:30]:  # 최근 30일
            daily_data.append({
                "date": item.get("stck_bsop_date", ""),              # 영업일자
                "close_price": int(item.get("stck_clpr", 0)),        # 종가
                "change_rate": float(item.get("prdy_ctrt", 0)),      # 등락률
                "foreign_net": int(item.get("frgn_ntby_qty", 0)),    # 외국인순매수
                "organ_net": int(item.get("orgn_ntby_qty", 0)),      # 기관순매수
                "individual_net": int(item.get("prsn_ntby_qty", 0)), # 개인순매수
            })

        return {
            "stock_code": stock_code,
            "daily_investor_trend": daily_data,
        }

    def get_member_trading(self, stock_code: str) -> Dict[str, Any]:
        """주식현재가 회원사 조회 (증권사별 매매현황)

        Returns:
            증권사별 매수/매도 현황 (상위 5개)
        """
        path = "/uapi/domestic-stock/v1/quotations/inquire-member"
        tr_id = "FHKST01010600"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
        }

        result = self.client.request("GET", path, tr_id, params=params)

        if result.get("rt_cd") != "0":
            return {"error": result.get("msg1", "Unknown error")}

        output = result.get("output", {})

        # 매도 상위 5개 증권사
        sell_members = []
        for i in range(1, 6):
            name = output.get(f"seln_mbcr_name{i}", "")
            if name:
                sell_members.append({
                    "member_name": name,
                    "volume": int(output.get(f"total_seln_qty{i}", 0) or 0),
                    "ratio": float(output.get(f"seln_mbcr_rlim{i}", 0) or 0),
                })

        # 매수 상위 5개 증권사
        buy_members = []
        for i in range(1, 6):
            name = output.get(f"shnu_mbcr_name{i}", "")
            if name:
                buy_members.append({
                    "member_name": name,
                    "volume": int(output.get(f"total_shnu_qty{i}", 0) or 0),
                    "ratio": float(output.get(f"shnu_mbcr_rlim{i}", 0) or 0),
                })

        return {
            "stock_code": stock_code,
            "sell_members": sell_members,
            "buy_members": buy_members,
            "global_sell_total": int(output.get("glob_total_seln_qty", 0) or 0),
            "global_buy_total": int(output.get("glob_total_shnu_qty", 0) or 0),
            "global_net": int(output.get("glob_ntby_qty", 0) or 0),
        }

    def get_daily_chart(
        self,
        stock_code: str,
        period: str = "D",
        days: int = 60,
    ) -> Dict[str, Any]:
        """국내주식기간별시세 조회 (일봉/주봉/월봉)

        Args:
            stock_code: 종목코드
            period: D(일), W(주), M(월), Y(년)
            days: 조회 일수

        Returns:
            OHLCV 데이터
        """
        path = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        tr_id = "FHKST03010100"

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": period,
            "FID_ORG_ADJ_PRC": "0",  # 수정주가 적용
        }

        result = self.client.request("GET", path, tr_id, params=params)

        if result.get("rt_cd") != "0":
            return {"error": result.get("msg1", "Unknown error")}

        output1 = result.get("output1", {})
        output2 = result.get("output2", [])

        # OHLCV 데이터 파싱
        ohlcv = []
        for item in output2:
            ohlcv.append({
                "date": item.get("stck_bsop_date", ""),
                "open": int(item.get("stck_oprc", 0)),
                "high": int(item.get("stck_hgpr", 0)),
                "low": int(item.get("stck_lwpr", 0)),
                "close": int(item.get("stck_clpr", 0)),
                "volume": int(item.get("acml_vol", 0)),
                "trading_value": int(item.get("acml_tr_pbmn", 0)),
                "change_rate": float(item.get("prdy_ctrt", 0)),
            })

        return {
            "stock_code": stock_code,
            "stock_name": output1.get("hts_kor_isnm", ""),
            "period": period,
            "ohlcv": ohlcv,
        }

    def get_today_ticks(self, stock_code: str) -> Dict[str, Any]:
        """주식현재가 당일시간대별체결 조회 (분봉/틱)

        Returns:
            당일 시간대별 체결 데이터
        """
        path = "/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
        tr_id = "FHPST01060000"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_HOUR_1": "",
        }

        result = self.client.request("GET", path, tr_id, params=params)

        if result.get("rt_cd") != "0":
            return {"error": result.get("msg1", "Unknown error")}

        output = result.get("output", [])

        ticks = []
        for item in output[:100]:  # 최근 100건
            ticks.append({
                "time": item.get("stck_cntg_hour", ""),          # 체결시간 (HHMMSS)
                "price": int(item.get("stck_prpr", 0)),          # 체결가
                "change_price": int(item.get("prdy_vrss", 0)),   # 전일대비
                "change_sign": item.get("prdy_vrss_sign", ""),   # 부호
                "volume": int(item.get("cntg_vol", 0)),          # 체결량
                "cumulative_volume": int(item.get("acml_vol", 0)),  # 누적거래량
            })

        return {
            "stock_code": stock_code,
            "ticks": ticks,
        }

    def get_financial_info(self, stock_code: str) -> Dict[str, Any]:
        """재무정보 조회

        Returns:
            매출액, 영업이익, 순이익, 자산, 부채 등 재무제표 정보
        """
        path = "/uapi/domestic-stock/v1/finance/financial-ratio"
        tr_id = "FHKST66430100"

        params = {
            "FID_DIV_CLS_CODE": "0",
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code,
        }

        result = self.client.request("GET", path, tr_id, params=params)

        if result.get("rt_cd") != "0":
            return {"error": result.get("msg1", "Unknown error")}

        output = result.get("output", [])

        # 연도별 재무 데이터
        yearly_data = []
        for item in output[:5]:  # 최근 5년
            yearly_data.append({
                "year": item.get("stac_yymm", ""),                    # 결산년월
                "sales": int(item.get("sale_account", 0) or 0),       # 매출액
                "operating_profit": int(item.get("bsop_prti", 0) or 0),  # 영업이익
                "net_income": int(item.get("thtr_ntin", 0) or 0),     # 당기순이익
                "roe": float(item.get("roe_val", 0) or 0),            # ROE
                "eps": float(item.get("eps", 0) or 0),                # EPS
                "bps": float(item.get("bps", 0) or 0),                # BPS
                "debt_ratio": float(item.get("lblt_rate", 0) or 0),   # 부채비율
            })

        return {
            "stock_code": stock_code,
            "financial_data": yearly_data,
        }

    def get_dividend_info(self, stock_code: str) -> Dict[str, Any]:
        """배당정보 조회

        Returns:
            배당금, 배당수익률, 배당성향 등
        """
        # 현재가 API에서 배당 정보 추출 (별도 배당 API가 없는 경우)
        price_data = self.get_current_price(stock_code)

        if "error" in price_data:
            return {"error": price_data["error"]}

        # 배당 관련 정보는 현재가 시세에서 일부 제공
        return {
            "stock_code": stock_code,
            "per": price_data.get("per", 0),
            "pbr": price_data.get("pbr", 0),
            "eps": price_data.get("eps", 0),
            "bps": price_data.get("bps", 0),
        }

    def get_daily_price(self, stock_code: str, days: int = 30) -> Dict[str, Any]:
        """주식현재가 일자별 조회

        Returns:
            최근 N일간 일별 시세 데이터
        """
        path = "/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        tr_id = "FHKST01010400"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0",
        }

        result = self.client.request("GET", path, tr_id, params=params)

        if result.get("rt_cd") != "0":
            return {"error": result.get("msg1", "Unknown error")}

        output = result.get("output", [])

        daily_prices = []
        for item in output[:days]:
            daily_prices.append({
                "date": item.get("stck_bsop_date", ""),
                "close": int(item.get("stck_clpr", 0)),
                "open": int(item.get("stck_oprc", 0)),
                "high": int(item.get("stck_hgpr", 0)),
                "low": int(item.get("stck_lwpr", 0)),
                "volume": int(item.get("acml_vol", 0)),
                "trading_value": int(item.get("acml_tr_pbmn", 0)),
                "change_rate": float(item.get("prdy_ctrt", 0)),
            })

        return {
            "stock_code": stock_code,
            "daily_prices": daily_prices,
        }

    def get_program_trading(self, stock_code: str) -> Dict[str, Any]:
        """종목별 프로그램매매추이 (체결)

        Returns:
            실시간 프로그램 매매 현황
        """
        path = "/uapi/domestic-stock/v1/quotations/program-trade-by-stock"
        tr_id = "FHPPG04650100"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
        }

        try:
            result = self.client.request("GET", path, tr_id, params=params)

            if result.get("rt_cd") != "0":
                return {"error": result.get("msg1", "Unknown error")}

            output = result.get("output", [])

            program_data = []
            for item in output[:20]:
                program_data.append({
                    "time": item.get("bsop_hour", ""),
                    "buy_volume": int(item.get("pgmg_buy_qty", 0) or 0),
                    "sell_volume": int(item.get("pgmg_sell_qty", 0) or 0),
                    "net_volume": int(item.get("pgmg_ntby_qty", 0) or 0),
                })

            return {
                "stock_code": stock_code,
                "program_trading": program_data,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_credit_balance(self, stock_code: str) -> Dict[str, Any]:
        """국내주식 신용잔고 일별추이

        Returns:
            신용거래 잔고 현황
        """
        path = "/uapi/domestic-stock/v1/quotations/credit-balance"
        tr_id = "FHKST01010700"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
        }

        try:
            result = self.client.request("GET", path, tr_id, params=params)

            if result.get("rt_cd") != "0":
                return {"error": result.get("msg1", "Unknown error")}

            output = result.get("output", [])

            credit_data = []
            for item in output[:30]:
                credit_data.append({
                    "date": item.get("stck_bsop_date", ""),
                    "credit_balance": int(item.get("crdt_ldng_rmnd", 0) or 0),  # 신용융자잔고
                    "credit_ratio": float(item.get("crdt_rate", 0) or 0),        # 신용비율
                })

            return {
                "stock_code": stock_code,
                "credit_balance": credit_data,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_foreign_institution_summary(self, stock_code: str) -> Dict[str, Any]:
        """외인/기관 매매 요약 (투자자 동향에서 추출)

        Returns:
            최근 외국인/기관 순매수 요약
        """
        investor_data = self.get_investor_trend(stock_code)

        if "error" in investor_data:
            return investor_data

        daily = investor_data.get("daily_investor_trend", [])

        if not daily:
            return {"error": "No investor data available"}

        # 최근 5일 합계
        recent_5d = daily[:5]
        foreign_5d = sum(d.get("foreign_net", 0) for d in recent_5d)
        organ_5d = sum(d.get("organ_net", 0) for d in recent_5d)
        individual_5d = sum(d.get("individual_net", 0) for d in recent_5d)

        # 최근 20일 합계
        recent_20d = daily[:20]
        foreign_20d = sum(d.get("foreign_net", 0) for d in recent_20d)
        organ_20d = sum(d.get("organ_net", 0) for d in recent_20d)
        individual_20d = sum(d.get("individual_net", 0) for d in recent_20d)

        return {
            "stock_code": stock_code,
            "today": daily[0] if daily else {},
            "summary_5d": {
                "foreign_net": foreign_5d,
                "organ_net": organ_5d,
                "individual_net": individual_5d,
            },
            "summary_20d": {
                "foreign_net": foreign_20d,
                "organ_net": organ_20d,
                "individual_net": individual_20d,
            },
        }

    def get_all_stock_data(
        self,
        stock_code: str,
        include_chart: bool = True,
        include_ticks: bool = False,
        include_extended: bool = True,
    ) -> Dict[str, Any]:
        """종목의 모든 상세 데이터 수집

        Args:
            stock_code: 종목코드
            include_chart: 차트 데이터 포함 여부
            include_ticks: 틱 데이터 포함 여부 (양이 많음)
            include_extended: 확장 데이터 포함 (재무, 프로그램매매 등)

        Returns:
            종목 종합 데이터
        """
        data = {
            "stock_code": stock_code,
            "collected_at": datetime.now().isoformat(),
        }

        # 1. 현재가 시세 (필수)
        data["current_price"] = self.get_current_price(stock_code)
        time.sleep(0.1)

        # 2. 호가 정보
        data["asking_price"] = self.get_asking_price(stock_code)
        time.sleep(0.1)

        # 3. 투자자 동향 (30일)
        data["investor_trend"] = self.get_investor_trend(stock_code)
        time.sleep(0.1)

        # 4. 회원사 매매현황
        data["member_trading"] = self.get_member_trading(stock_code)
        time.sleep(0.1)

        # 5. 일별 시세 (30일)
        data["daily_price"] = self.get_daily_price(stock_code, days=30)
        time.sleep(0.1)

        # 6. 일봉 차트 (선택)
        if include_chart:
            data["daily_chart"] = self.get_daily_chart(stock_code, period="D", days=60)
            time.sleep(0.1)

        # 7. 당일 틱 데이터 (선택)
        if include_ticks:
            data["today_ticks"] = self.get_today_ticks(stock_code)
            time.sleep(0.1)

        # 8. 확장 데이터 (선택)
        if include_extended:
            # 재무정보
            data["financial_info"] = self.get_financial_info(stock_code)
            time.sleep(0.1)

            # 외국인/기관 매매 요약
            data["foreign_institution_summary"] = self.get_foreign_institution_summary(stock_code)
            time.sleep(0.1)

            # 프로그램매매 (실패해도 계속 진행)
            data["program_trading"] = self.get_program_trading(stock_code)

        return data

    def get_multiple_stocks_data(
        self,
        stock_codes: List[str],
        include_chart: bool = True,
        include_ticks: bool = False,
        include_extended: bool = True,
        delay: float = 0.2,
    ) -> List[Dict[str, Any]]:
        """여러 종목의 상세 데이터 수집

        Args:
            stock_codes: 종목코드 리스트
            include_chart: 차트 데이터 포함 여부
            include_ticks: 틱 데이터 포함 여부
            include_extended: 확장 데이터 포함 여부 (재무, 프로그램매매 등)
            delay: API 호출 간 지연 (초)

        Returns:
            종목별 종합 데이터 리스트
        """
        results = []
        total = len(stock_codes)

        for idx, code in enumerate(stock_codes):
            print(f"  [{idx + 1}/{total}] {code} 데이터 수집 중...")

            try:
                stock_data = self.get_all_stock_data(
                    code,
                    include_chart=include_chart,
                    include_ticks=include_ticks,
                    include_extended=include_extended,
                )
                # 종목명 추가
                if "current_price" in stock_data and "stock_name" in stock_data["current_price"]:
                    stock_data["stock_name"] = stock_data["current_price"]["stock_name"]
                results.append(stock_data)
            except Exception as e:
                print(f"    [ERROR] {code} 수집 실패: {e}")
                results.append({
                    "stock_code": code,
                    "error": str(e),
                    "collected_at": datetime.now().isoformat(),
                })

            time.sleep(delay)

        return results


def test_stock_detail_api():
    """종목 상세 API 테스트"""
    try:
        api = KISStockDetailAPI()

        # 삼성전자 테스트
        stock_code = "005930"
        print(f"\n[{stock_code}] 종목 상세 데이터 테스트")
        print("=" * 60)

        # 현재가
        print("\n[현재가 시세]")
        price_data = api.get_current_price(stock_code)
        if "error" not in price_data:
            print(f"  현재가: {price_data['current_price']:,}원")
            print(f"  전일대비: {price_data['change_price']:+,}원 ({price_data['change_rate']:+.2f}%)")
            print(f"  거래량: {price_data['volume']:,}")
            print(f"  PER: {price_data['per']:.2f}")
            print(f"  PBR: {price_data['pbr']:.2f}")
            print(f"  시가총액: {price_data['market_cap']:,}억원")
        else:
            print(f"  오류: {price_data['error']}")

        # 호가
        print("\n[호가 정보]")
        asking_data = api.get_asking_price(stock_code)
        if "error" not in asking_data:
            print(f"  매도잔량: {asking_data['total_ask_volume']:,}")
            print(f"  매수잔량: {asking_data['total_bid_volume']:,}")
            print("  [상위 3단계 호가]")
            for i in range(3):
                ask = asking_data['ask_prices'][i]
                bid = asking_data['bid_prices'][i]
                print(f"    {ask['volume']:>10,} | {ask['price']:>10,} | "
                      f"{bid['price']:>10,} | {bid['volume']:>10,}")
        else:
            print(f"  오류: {asking_data['error']}")

        # 투자자 동향 (최근 5일)
        print("\n[투자자 동향 - 최근 5일]")
        investor_data = api.get_investor_trend(stock_code)
        if "error" not in investor_data:
            for day in investor_data['daily_investor_trend'][:5]:
                print(f"  {day['date']}: 외국인 {day['foreign_net']:+,} | "
                      f"기관 {day['organ_net']:+,} | 개인 {day['individual_net']:+,}")
        else:
            print(f"  오류: {investor_data['error']}")

    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_stock_detail_api()
