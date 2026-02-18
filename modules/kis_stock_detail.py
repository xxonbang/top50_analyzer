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
from datetime import datetime, timedelta, timezone

# KST 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))

from modules.kis_client import KISClient
from modules.market_calendar import is_market_hours


def safe_int(value, default: int = 0) -> int:
    """빈 문자열이나 None을 안전하게 정수로 변환"""
    if value is None or value == "":
        return default
    try:
        return int(float(value))
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

        # API가 list를 반환하는 경우 처리
        if isinstance(output, list):
            output = output[0] if output else {}

        return {
            "stock_code": stock_code,
            "stock_name": output.get("rprs_mrkt_kor_name", ""),        # 종목명
            "current_price": safe_int(output.get("stck_prpr", 0)),         # 현재가
            "change_price": safe_int(output.get("prdy_vrss", 0)),          # 전일대비
            "change_rate": safe_float(output.get("prdy_ctrt", 0)),         # 등락률
            "change_sign": output.get("prdy_vrss_sign", ""),          # 부호 (1:상승, 2:하락, 3:보합)
            "open_price": safe_int(output.get("stck_oprc", 0)),            # 시가
            "high_price": safe_int(output.get("stck_hgpr", 0)),            # 고가
            "low_price": safe_int(output.get("stck_lwpr", 0)),             # 저가
            "prev_close": safe_int(output.get("stck_sdpr", 0)),            # 전일종가
            "volume": safe_int(output.get("acml_vol", 0)),                 # 누적거래량
            "trading_value": safe_int(output.get("acml_tr_pbmn", 0)),      # 누적거래대금
            "high_52week": safe_int(output.get("stck_mxpr", 0)),           # 52주 최고가
            "low_52week": safe_int(output.get("stck_llam", 0)),            # 52주 최저가
            "per": safe_float(output.get("per", 0) or 0),                  # PER
            "pbr": safe_float(output.get("pbr", 0) or 0),                  # PBR
            "eps": safe_float(output.get("eps", 0) or 0),                  # EPS
            "bps": safe_float(output.get("bps", 0) or 0),                  # BPS
            "market_cap": safe_int(output.get("hts_avls", 0)),             # 시가총액 (억원)
            "shares_outstanding": safe_int(output.get("lstn_stcn", 0)),    # 상장주수
            "foreign_ratio": safe_float(output.get("hts_frgn_ehrt", 0)),   # 외국인소진율
            "volume_turnover": safe_float(output.get("vol_tnrt", 0)),      # 거래량회전율
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

        # API가 list를 반환하는 경우 처리
        if isinstance(output, list):
            output = output[0] if output else {}
        if isinstance(output2, list):
            output2 = output2[0] if output2 else {}

        # 10단계 호가 파싱
        ask_prices = []  # 매도호가 (1~10)
        bid_prices = []  # 매수호가 (1~10)

        for i in range(1, 11):
            ask_prices.append({
                "price": safe_int(output.get(f"askp{i}", 0)),
                "volume": safe_int(output.get(f"askp_rsqn{i}", 0)),
            })
            bid_prices.append({
                "price": safe_int(output.get(f"bidp{i}", 0)),
                "volume": safe_int(output.get(f"bidp_rsqn{i}", 0)),
            })

        return {
            "stock_code": stock_code,
            "ask_prices": ask_prices,                                    # 매도호가
            "bid_prices": bid_prices,                                    # 매수호가
            "total_ask_volume": safe_int(output.get("total_askp_rsqn", 0)),  # 총매도잔량
            "total_bid_volume": safe_int(output.get("total_bidp_rsqn", 0)),  # 총매수잔량
            "expected_price": safe_int(output2.get("antc_cnpr", 0)),         # 예상체결가
            "expected_volume": safe_int(output2.get("antc_vol", 0)),         # 예상체결량
            "expected_change_rate": safe_float(output2.get("antc_cntg_prdy_ctrt", 0)),  # 예상등락률
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
                "close_price": safe_int(item.get("stck_clpr", 0)),        # 종가
                "change_rate": safe_float(item.get("prdy_ctrt", 0)),      # 등락률
                "foreign_net": safe_int(item.get("frgn_ntby_qty", 0)),    # 외국인순매수
                "organ_net": safe_int(item.get("orgn_ntby_qty", 0)),      # 기관순매수
                "individual_net": safe_int(item.get("prsn_ntby_qty", 0)), # 개인순매수
            })

        return {
            "stock_code": stock_code,
            "daily_investor_trend": daily_data,
        }

    def get_investor_trend_estimate(self, stock_code: str) -> Dict[str, Any]:
        """종목별 외인기관 추정가집계 (장중 추정 데이터)

        Returns:
            외국인/기관 추정 순매수 데이터
        """
        path = "/uapi/domestic-stock/v1/quotations/investor-trend-estimate"
        tr_id = "HHPTJ04160200"

        params = {
            "MKSC_SHRN_ISCD": stock_code,
        }

        try:
            result = self.client.request("GET", path, tr_id, params=params)

            if result.get("rt_cd") != "0":
                return {"error": result.get("msg1", "Unknown error")}

            output2 = result.get("output2", [])

            # 시간대별 상세 데이터
            time_details = []
            total_foreign_net = 0
            total_institution_net = 0
            total_net = 0

            for item in output2:
                frgn_qty = safe_int(item.get("frgn_fake_ntby_qty", 0))
                orgn_qty = safe_int(item.get("orgn_fake_ntby_qty", 0))
                sum_qty = safe_int(item.get("sum_fake_ntby_qty", 0))

                time_details.append({
                    "time_group": item.get("bsop_hour_gb", ""),
                    "foreign_net": frgn_qty,
                    "institution_net": orgn_qty,
                    "total_net": sum_qty,
                })

            # 가장 최근(마지막 집계) 데이터의 누적값 사용
            # output2의 첫 번째 항목이 가장 최근 누적값
            if output2:
                latest = output2[0]
                total_foreign_net = safe_int(latest.get("frgn_fake_ntby_qty", 0))
                total_institution_net = safe_int(latest.get("orgn_fake_ntby_qty", 0))
                total_net = safe_int(latest.get("sum_fake_ntby_qty", 0))

            return {
                "stock_code": stock_code,
                "is_estimated": True,
                "estimated_data": {
                    "foreign_net": total_foreign_net,
                    "institution_net": total_institution_net,
                    "total_net": total_net,
                },
                "time_details": time_details,
            }
        except Exception as e:
            return {"error": str(e)}

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

        # API가 list를 반환하는 경우 처리
        if isinstance(output, list):
            output = output[0] if output else {}

        # 매도 상위 5개 증권사
        sell_members = []
        for i in range(1, 6):
            name = output.get(f"seln_mbcr_name{i}", "")
            if name:
                sell_members.append({
                    "member_name": name,
                    "volume": safe_int(output.get(f"total_seln_qty{i}", 0) or 0),
                    "ratio": safe_float(output.get(f"seln_mbcr_rlim{i}", 0) or 0),
                })

        # 매수 상위 5개 증권사
        buy_members = []
        for i in range(1, 6):
            name = output.get(f"shnu_mbcr_name{i}", "")
            if name:
                buy_members.append({
                    "member_name": name,
                    "volume": safe_int(output.get(f"total_shnu_qty{i}", 0) or 0),
                    "ratio": safe_float(output.get(f"shnu_mbcr_rlim{i}", 0) or 0),
                })

        return {
            "stock_code": stock_code,
            "sell_members": sell_members,
            "buy_members": buy_members,
            "global_sell_total": safe_int(output.get("glob_total_seln_qty", 0) or 0),
            "global_buy_total": safe_int(output.get("glob_total_shnu_qty", 0) or 0),
            "global_net": safe_int(output.get("glob_ntby_qty", 0) or 0),
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

        end_date = datetime.now(KST).strftime("%Y%m%d")
        start_date = (datetime.now(KST) - timedelta(days=days)).strftime("%Y%m%d")

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

        # API가 list를 반환하는 경우 처리
        if isinstance(output1, list):
            output1 = output1[0] if output1 else {}

        # OHLCV 데이터 파싱
        ohlcv = []
        for item in output2:
            ohlcv.append({
                "date": item.get("stck_bsop_date", ""),
                "open": safe_int(item.get("stck_oprc", 0)),
                "high": safe_int(item.get("stck_hgpr", 0)),
                "low": safe_int(item.get("stck_lwpr", 0)),
                "close": safe_int(item.get("stck_clpr", 0)),
                "volume": safe_int(item.get("acml_vol", 0)),
                "trading_value": safe_int(item.get("acml_tr_pbmn", 0)),
                "change_rate": safe_float(item.get("prdy_ctrt", 0)),
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
                "price": safe_int(item.get("stck_prpr", 0)),          # 체결가
                "change_price": safe_int(item.get("prdy_vrss", 0)),   # 전일대비
                "change_sign": item.get("prdy_vrss_sign", ""),   # 부호
                "volume": safe_int(item.get("cntg_vol", 0)),          # 체결량
                "cumulative_volume": safe_int(item.get("acml_vol", 0)),  # 누적거래량
            })

        return {
            "stock_code": stock_code,
            "ticks": ticks,
        }

    def get_financial_info(self, stock_code: str) -> Dict[str, Any]:
        """재무비율 + 손익계산서 통합 조회

        Returns:
            ROE, 부채비율, EPS, BPS, 매출액, 영업이익, 당기순이익 등
        """
        # --- (A) 재무비율 API ---
        ratio_path = "/uapi/domestic-stock/v1/finance/financial-ratio"
        ratio_tr_id = "FHKST66430300"

        params = {
            "FID_DIV_CLS_CODE": "0",
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code,
        }

        ratio_result = self.client.request("GET", ratio_path, ratio_tr_id, params=params)
        ratio_output = []
        if ratio_result.get("rt_cd") == "0":
            ratio_output = ratio_result.get("output", [])

        # --- (B) 손익계산서 API ---
        time.sleep(0.05)
        income_path = "/uapi/domestic-stock/v1/finance/income-statement"
        income_tr_id = "FHKST66430200"

        income_result = self.client.request("GET", income_path, income_tr_id, params=params)
        income_output = []
        if income_result.get("rt_cd") == "0":
            income_output = income_result.get("output", [])

        # --- (C) 연도(stac_yymm) 기준으로 병합 ---
        # 손익계산서를 연도 맵으로 변환
        income_map = {}
        for item in income_output[:5]:
            year = item.get("stac_yymm", "")
            if year:
                income_map[year] = item

        yearly_data = []
        for item in ratio_output[:5]:
            year = item.get("stac_yymm", "")
            inc = income_map.get(year, {})

            yearly_data.append({
                "year": year,                                                    # 결산년월
                # 재무비율 API
                "roe": safe_float(item.get("roe_val", 0) or 0),                 # ROE
                "eps": safe_float(item.get("eps", 0) or 0),                     # EPS
                "bps": safe_float(item.get("bps", 0) or 0),                     # BPS
                "debt_ratio": safe_float(item.get("lblt_rate", 0) or 0),        # 부채비율
                "sales_growth": safe_float(item.get("grs", 0) or 0),            # 매출액 증가율
                "op_profit_growth": safe_float(item.get("bsop_prfi_inrt", 0) or 0),  # 영업이익 증가율
                # 손익계산서 API
                "sales": safe_int(inc.get("sale_account", 0) or 0),              # 매출액
                "operating_profit": safe_int(inc.get("bsop_prti", 0) or 0),      # 영업이익
                "net_income": safe_int(inc.get("thtr_ntin", 0) or 0),            # 당기순이익
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
                "close": safe_int(item.get("stck_clpr", 0)),
                "open": safe_int(item.get("stck_oprc", 0)),
                "high": safe_int(item.get("stck_hgpr", 0)),
                "low": safe_int(item.get("stck_lwpr", 0)),
                "volume": safe_int(item.get("acml_vol", 0)),
                "trading_value": safe_int(item.get("acml_tr_pbmn", 0)),
                "change_rate": safe_float(item.get("prdy_ctrt", 0)),
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
                    "buy_volume": safe_int(item.get("pgmg_buy_qty", 0) or 0),
                    "sell_volume": safe_int(item.get("pgmg_sell_qty", 0) or 0),
                    "net_volume": safe_int(item.get("pgmg_ntby_qty", 0) or 0),
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
                    "credit_balance": safe_int(item.get("crdt_ldng_rmnd", 0) or 0),  # 신용융자잔고
                    "credit_ratio": safe_float(item.get("crdt_rate", 0) or 0),        # 신용비율
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
            "collected_at": datetime.now(KST).isoformat(),
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

        # 3-1. 장중이면 추정 수급 데이터 추가 수집
        if is_market_hours():
            data["investor_trend_estimate"] = self.get_investor_trend_estimate(stock_code)
            time.sleep(0.1)

        # 4. 회원사 매매현황
        data["member_trading"] = self.get_member_trading(stock_code)
        time.sleep(0.1)

        # 5. 일별 시세 (30일)
        data["daily_price"] = self.get_daily_price(stock_code, days=30)
        time.sleep(0.1)

        # 6. 일봉 차트 (선택)
        if include_chart:
            data["daily_chart"] = self.get_daily_chart(stock_code, period="D", days=200)
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
                    "collected_at": datetime.now(KST).isoformat(),
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
