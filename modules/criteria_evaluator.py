"""종목 선정 기준 평가 모듈 (7-Criteria Evaluator)

KIS API로 수집된 kis_latest.json 데이터를 기반으로
모든 종목을 7개 독립 기준으로 평가한다.

기준:
  1. 전고점 돌파 (빨강)
  2. 끼 보유 (주황)
  3. 심리적 저항선 돌파 (노랑)
  4. 이동평균선 정배열 (청록)
  5. 외국인/기관 수급 (파랑)
  6. 프로그램 매매 (보라)
  7. 거래대금 TOP30 (자홍)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


# 심리적 저항선: 호가 단위 경계 (한국 주식 호가 단위 기준)
TICK_BOUNDARIES = [
    1000, 2000, 3000, 4000, 5000,
    10000, 20000, 30000, 40000, 50000,
    100000, 200000, 300000, 400000, 500000,
    1000000,
]

# 라운드 넘버 (심리적 매물대)
ROUND_LEVELS = [
    1000, 2000, 3000, 5000,
    10000, 20000, 30000, 50000,
    100000, 150000, 200000, 250000, 300000, 400000, 500000,
    600000, 700000, 800000, 900000, 1000000,
]


class CriteriaEvaluator:
    def __init__(self, kis_raw_data: dict):
        self.stock_details = kis_raw_data.get("stock_details", {})
        self.rankings = kis_raw_data.get("rankings", {})
        self._top30_codes = self._build_top30_set()

    def _build_top30_set(self) -> set:
        """거래대금 TOP30 종목코드 집합 구성 (KOSPI+KOSDAQ 합산)"""
        all_stocks = (
            self.rankings.get("kospi", []) +
            self.rankings.get("kosdaq", [])
        )
        sorted_by_value = sorted(
            all_stocks,
            key=lambda s: s.get("trading_value", 0),
            reverse=True,
        )
        return {s["code"] for s in sorted_by_value[:30]}

    def check_high_breakout(
        self,
        current_price: float,
        daily_prices: list[dict],
        w52_high: float,
    ) -> dict:
        """1. 전고점 돌파: 6개월(120영업일) 고가 또는 52주 신고가 돌파"""
        if not current_price or current_price <= 0:
            return {"met": False, "reason": "현재가 데이터 없음"}

        # 최근 120일 고가 max (ohlcv는 최신순)
        recent_highs = [d.get("high", 0) for d in daily_prices[:120] if d.get("high")]
        six_mo_high = max(recent_highs) if recent_highs else 0

        is_52w = False
        if w52_high and w52_high > 0 and current_price >= w52_high:
            is_52w = True
            return {
                "met": True,
                "is_52w_high": True,
                "reason": f"52주 신고가 돌파 (현재가 {current_price:,.0f} >= 52주고가 {w52_high:,.0f})",
            }

        if six_mo_high > 0 and current_price >= six_mo_high:
            return {
                "met": True,
                "is_52w_high": False,
                "reason": f"6개월 고점 돌파 (현재가 {current_price:,.0f} >= 6개월고가 {six_mo_high:,.0f})",
            }

        return {
            "met": False,
            "is_52w_high": False,
            "reason": f"미돌파 (현재가 {current_price:,.0f}, 6개월고가 {six_mo_high:,.0f}, 52주고가 {w52_high:,.0f})",
        }

    def check_momentum_history(self, daily_prices: list[dict]) -> dict:
        """2. 끼 보유: 과거 상한가(>=29%) 또는 급등(>=15%) 이력"""
        had_limit_up = False
        had_15pct_rise = False

        for d in daily_prices:
            cr = d.get("change_rate", 0)
            if cr is None:
                continue
            # change_rate가 0으로 들어오는 경우 직접 계산
            if cr == 0 and d.get("close") and d.get("open") and d["open"] > 0:
                cr = ((d["close"] - d["open"]) / d["open"]) * 100

            if cr >= 29:
                had_limit_up = True
            if cr >= 15:
                had_15pct_rise = True

        met = had_limit_up or had_15pct_rise
        reasons = []
        if had_limit_up:
            reasons.append("상한가 이력 있음(>=29%)")
        if had_15pct_rise:
            reasons.append("급등 이력 있음(>=15%)")

        return {
            "met": met,
            "had_limit_up": had_limit_up,
            "had_15pct_rise": had_15pct_rise,
            "reason": ", ".join(reasons) if reasons else "급등 이력 없음",
        }

    def check_resistance_breakout(
        self,
        current_price: float,
        prev_close: float,
    ) -> dict:
        """3. 심리적 저항선 돌파: 전일종가 < 경계 <= 현재가"""
        if not current_price or not prev_close or current_price <= prev_close:
            return {"met": False, "reason": "하락 또는 데이터 없음"}

        broken = []
        all_levels = sorted(set(TICK_BOUNDARIES + ROUND_LEVELS))
        for boundary in all_levels:
            if prev_close < boundary <= current_price:
                broken.append(boundary)

        if broken:
            levels_str = ", ".join(f"{b:,.0f}" for b in broken[:3])
            return {
                "met": True,
                "reason": f"저항선 돌파: {levels_str} (전일 {prev_close:,.0f} → 현재 {current_price:,.0f})",
            }

        return {
            "met": False,
            "reason": f"돌파 없음 (전일 {prev_close:,.0f} → 현재 {current_price:,.0f})",
        }

    def check_ma_alignment(
        self,
        current_price: float,
        daily_prices: list[dict],
    ) -> dict:
        """4. 이동평균선 정배열: 현재가 > MA5 > MA10 > MA20 > MA60 > MA120"""
        if not current_price or current_price <= 0:
            return {"met": False, "reason": "현재가 데이터 없음"}

        # ohlcv는 최신순 → 역순으로 close 추출
        closes = []
        for d in reversed(daily_prices):
            c = d.get("close")
            if c and c > 0:
                closes.append(c)

        def sma(data: list, period: int) -> float | None:
            if len(data) < period:
                return None
            return sum(data[-period:]) / period

        ma_periods = [5, 10, 20, 60, 120]
        ma_values: dict[str, float | None] = {}
        for p in ma_periods:
            ma_values[f"MA{p}"] = sma(closes, p)

        # 데이터 부족 체크
        if any(v is None for v in ma_values.values()):
            missing = [k for k, v in ma_values.items() if v is None]
            return {
                "met": False,
                "reason": f"데이터 부족 ({', '.join(missing)} 계산 불가, {len(closes)}일)",
                "ma_values": {k: round(v, 1) if v else None for k, v in ma_values.items()},
            }

        # 정배열 검사: 현재가 > MA5 > MA10 > MA20 > MA60 > MA120
        vals = [current_price] + [ma_values[f"MA{p}"] for p in ma_periods]
        is_aligned = all(vals[i] > vals[i + 1] for i in range(len(vals) - 1))

        ma_display = {k: round(v, 1) for k, v in ma_values.items() if v is not None}

        if is_aligned:
            return {
                "met": True,
                "reason": f"정배열 확인 (현재가>{'>'.join(f'MA{p}' for p in ma_periods)})",
                "ma_values": ma_display,
            }

        return {
            "met": False,
            "reason": "정배열 아님",
            "ma_values": ma_display,
        }

    def check_supply_demand(
        self,
        foreign_net: float,
        institution_net: float,
    ) -> dict:
        """5. 외국인/기관 동시 순매수"""
        foreign_buy = foreign_net > 0
        institution_buy = institution_net > 0
        met = foreign_buy and institution_buy

        parts = []
        parts.append(f"외국인 {'순매수' if foreign_buy else '순매도'}({foreign_net:+,.0f})")
        parts.append(f"기관 {'순매수' if institution_buy else '순매도'}({institution_net:+,.0f})")

        return {
            "met": met,
            "reason": ", ".join(parts),
        }

    def check_program_trading(self, program_net_buy_qty: float) -> dict:
        """6. 프로그램 순매수"""
        met = program_net_buy_qty > 0
        return {
            "met": met,
            "reason": f"프로그램 순매수량: {program_net_buy_qty:+,.0f}",
        }

    def check_top30_trading_value(self, stock_code: str) -> dict:
        """7. 거래대금 TOP30"""
        met = stock_code in self._top30_codes
        return {
            "met": met,
            "reason": "거래대금 TOP30" if met else "TOP30 아님",
        }

    def evaluate_stock(self, code: str) -> dict:
        """단일 종목 7개 기준 평가"""
        details = self.stock_details.get(code, {})
        cp_data = details.get("current_price", {})
        daily_chart = details.get("daily_chart", {})
        ohlcv = daily_chart.get("ohlcv", [])

        current_price = cp_data.get("current_price", 0)
        w52_high = cp_data.get("high_52week", 0)
        prev_close = cp_data.get("prev_close", 0)

        # 외국인/기관 수급 (추정치 우선)
        estimate = details.get("investor_trend_estimate", {})
        if estimate.get("is_estimated"):
            est_data = estimate.get("estimated_data", {})
            foreign_net = est_data.get("foreign_net", 0)
            institution_net = est_data.get("institution_net", 0)
        else:
            trend = details.get("investor_trend", {}).get("daily_investor_trend", [])
            today = trend[0] if trend else {}
            foreign_net = today.get("foreign_net", 0)
            institution_net = today.get("organ_net", 0)

        # 프로그램 매매 순매수량 합산
        prog_data = details.get("program_trading", {})
        prog_list = prog_data.get("program_trading", [])
        program_net = sum(p.get("net_volume", 0) for p in prog_list)

        criteria = {
            "high_breakout": self.check_high_breakout(current_price, ohlcv, w52_high),
            "momentum_history": self.check_momentum_history(ohlcv),
            "resistance_breakout": self.check_resistance_breakout(current_price, prev_close),
            "ma_alignment": self.check_ma_alignment(current_price, ohlcv),
            "supply_demand": self.check_supply_demand(foreign_net, institution_net),
            "program_trading": self.check_program_trading(program_net),
            "top30_trading_value": self.check_top30_trading_value(code),
        }

        criteria["all_met"] = all(
            c["met"] for key, c in criteria.items()
            if key != "all_met" and isinstance(c, dict)
        )

        return criteria

    def evaluate_all(self) -> dict:
        """전체 종목 평가"""
        result = {}
        for code in self.stock_details:
            result[code] = self.evaluate_stock(code)
        return result


if __name__ == "__main__":
    raw_path = Path("results/kis/kis_latest.json")
    if not raw_path.exists():
        print("kis_latest.json 없음")
        exit(1)

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    evaluator = CriteriaEvaluator(data)
    result = evaluator.evaluate_all()

    output_path = Path("results/kis/criteria_data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 요약 출력
    total = len(result)
    met_counts: dict[str, int] = {}
    all_met_count = 0
    for code, c in result.items():
        if c.get("all_met"):
            all_met_count += 1
        for key in [
            "high_breakout", "momentum_history", "resistance_breakout",
            "ma_alignment", "supply_demand", "program_trading", "top30_trading_value",
        ]:
            if c.get(key, {}).get("met"):
                met_counts[key] = met_counts.get(key, 0) + 1

    print(f"기준 평가 완료: {total}개 종목")
    for key, count in met_counts.items():
        print(f"  {key}: {count}/{total}")
    print(f"  ALL MET: {all_met_count}/{total}")
    print(f"저장: {output_path}")
