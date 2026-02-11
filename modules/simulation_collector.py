"""
모의투자 시뮬레이션 데이터 수집기

기존 분석 결과에서 '적극매수' 시그널 종목을 추출하고,
KIS API로 시가/종가를 수집하여 당일 수익률을 계산합니다.

카테고리:
- Vision: vision_analysis.json → signal='적극매수'
- KIS: kis_analysis.json → signal='적극매수'
- Combined: combined_analysis.json → match_status='match' AND vision_signal='적극매수'
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import ROOT_DIR
from modules.kis_client import KISClient


class SimulationCollector:
    """적극매수 종목의 당일 시가→종가 수익률 시뮬레이션 데이터 수집"""

    RESULTS_DIR = ROOT_DIR / "results"
    SIMULATION_DIR = RESULTS_DIR / "simulation"

    def __init__(self, kis_client: Optional[KISClient] = None):
        self.kis = kis_client or KISClient()
        self.SIMULATION_DIR.mkdir(parents=True, exist_ok=True)

    def _load_json(self, path: Path) -> Optional[dict]:
        """JSON 파일 로드 (실패 시 None)"""
        try:
            if not path.exists():
                print(f"[Simulation] 파일 없음: {path}")
                return None
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Simulation] JSON 로드 실패 ({path}): {e}")
            return None

    def get_strong_buy_stocks(self) -> dict[str, list[dict]]:
        """3개 카테고리별 적극매수 종목 추출

        Returns:
            {
                "vision": [{"code": "005930", "name": "삼성전자", "market": "KOSPI"}, ...],
                "kis": [...],
                "combined": [...]
            }
        """
        categories: dict[str, list[dict]] = {"vision": [], "kis": [], "combined": []}

        # Vision 적극매수
        vision_data = self._load_json(self.RESULTS_DIR / "vision" / "vision_analysis.json")
        if vision_data:
            for stock in vision_data.get("results", []):
                if stock.get("signal") == "적극매수":
                    market = stock.get("market", "")
                    # 코스피/코스닥 → KOSPI/KOSDAQ 정규화
                    if market in ("코스피", "KOSPI"):
                        market = "KOSPI"
                    elif market in ("코스닥", "KOSDAQ"):
                        market = "KOSDAQ"
                    categories["vision"].append({
                        "code": stock["code"],
                        "name": stock["name"],
                        "market": market,
                    })

        # KIS 적극매수
        kis_data = self._load_json(self.RESULTS_DIR / "kis" / "kis_analysis.json")
        if kis_data:
            for stock in kis_data.get("results", []):
                if stock.get("signal") == "적극매수":
                    categories["kis"].append({
                        "code": stock["code"],
                        "name": stock["name"],
                        "market": stock.get("market", ""),
                    })

        # Combined: match + 적극매수
        combined_data = self._load_json(self.RESULTS_DIR / "combined" / "combined_analysis.json")
        if combined_data:
            for stock in combined_data.get("stocks", []):
                if (stock.get("match_status") == "match"
                        and stock.get("vision_signal") == "적극매수"):
                    categories["combined"].append({
                        "code": stock["code"],
                        "name": stock["name"],
                        "market": stock.get("market", ""),
                    })

        for cat, stocks in categories.items():
            print(f"[Simulation] {cat} 적극매수: {len(stocks)}개")

        return categories

    def fetch_price(self, stock_code: str) -> Optional[dict]:
        """종목의 현재가(시가/종가) 조회

        Returns:
            {"open_price": int, "close_price": int} or None
        """
        try:
            result = self.kis.get_stock_price(stock_code)
            if result.get("rt_cd") != "0":
                print(f"[Simulation] 가격 조회 실패 ({stock_code}): {result.get('msg1', '')}")
                return None

            output = result.get("output", {})
            open_price = int(output.get("stck_oprc", 0))
            close_price = int(output.get("stck_prpr", 0))
            high_price = int(output.get("stck_hgpr", 0))

            if open_price == 0:
                return None

            return {
                "open_price": open_price,
                "close_price": close_price or None,
                "high_price": high_price or None,
            }
        except Exception as e:
            print(f"[Simulation] 가격 조회 에러 ({stock_code}): {e}")
            return None

    def fetch_daily_price(self, stock_code: str, target_date: str) -> Optional[dict]:
        """과거 날짜의 시가/종가 조회 (backfill용)

        Args:
            stock_code: 종목코드
            target_date: "YYYY-MM-DD" 형식

        Returns:
            {"open_price": int, "close_price": int, "high_price": int} or None
        """
        try:
            result = self.kis.get_stock_daily_price(stock_code)
            if result.get("rt_cd") != "0":
                return None

            date_key = target_date.replace("-", "")
            for item in result.get("output2", []):
                if item.get("stck_bsop_date") == date_key:
                    open_price = int(item.get("stck_oprc", 0))
                    close_price = int(item.get("stck_clpr", 0))
                    high_price = int(item.get("stck_hgpr", 0))
                    if open_price == 0:
                        return None
                    return {
                        "open_price": open_price,
                        "close_price": close_price or None,
                        "high_price": high_price or None,
                    }

            return None
        except Exception as e:
            print(f"[Simulation] 일봉 조회 에러 ({stock_code}, {target_date}): {e}")
            return None

    def collect_today(self) -> dict:
        """오늘의 시뮬레이션 데이터 수집"""
        import pytz

        kst = pytz.timezone("Asia/Seoul")
        now = datetime.now(kst)
        today_str = now.strftime("%Y-%m-%d")

        print(f"\n[Simulation] 당일 수집 시작: {today_str}")
        print("=" * 60)

        categories = self.get_strong_buy_stocks()

        # 전체 종목코드 중복 제거 (API 호출 최소화)
        all_codes: dict[str, dict] = {}
        for cat, stocks in categories.items():
            for stock in stocks:
                code = stock["code"]
                if code not in all_codes:
                    all_codes[code] = stock

        print(f"\n[Simulation] 중복 제거 후 총 {len(all_codes)}개 종목 가격 수집")

        # 가격 수집
        prices: dict[str, Optional[dict]] = {}
        for i, (code, stock) in enumerate(all_codes.items(), 1):
            print(f"  [{i}/{len(all_codes)}] {stock['name']} ({code})...", end=" ")
            price = self.fetch_price(code)
            prices[code] = price
            if price:
                ret = (price["close_price"] - price["open_price"]) / price["open_price"] * 100
                print(f"시가:{price['open_price']:,} 종가:{price['close_price']:,} 수익률:{ret:+.2f}%")
            else:
                print("가격 미수집")
            time.sleep(0.1)  # API rate limit

        # 카테고리별 결과 조립
        result_categories = {}
        for cat, stocks in categories.items():
            cat_results = []
            for stock in stocks:
                code = stock["code"]
                price = prices.get(code)
                open_p = price["open_price"] if price else None
                close_p = price["close_price"] if price else None
                high_p = price["high_price"] if price else None
                entry: dict = {
                    "code": code,
                    "name": stock["name"],
                    "market": stock["market"],
                    "open_price": open_p,
                    "close_price": close_p,
                    "high_price": high_p,
                    "return_pct": round(
                        (close_p - open_p) / open_p * 100, 2
                    ) if open_p and close_p and open_p > 0 else None,
                    "high_return_pct": round(
                        (high_p - open_p) / open_p * 100, 2
                    ) if open_p and high_p and open_p > 0 else None,
                }
                cat_results.append(entry)
            result_categories[cat] = cat_results

        simulation_data = {
            "date": today_str,
            "collected_at": now.isoformat(),
            "categories": result_categories,
        }

        return self._save_simulation(simulation_data)

    def collect_backfill(self, target_date: str) -> dict:
        """과거 날짜의 시뮬레이션 데이터 수집 (히스토리 기반)

        Args:
            target_date: "YYYY-MM-DD" 형식
        """
        import pytz

        kst = pytz.timezone("Asia/Seoul")
        now = datetime.now(kst)

        print(f"\n[Simulation] 백필 수집: {target_date}")
        print("=" * 60)

        # 해당 날짜의 히스토리 파일에서 적극매수 종목 추출
        categories = self._get_strong_buy_from_history(target_date)

        # 전체 종목코드 중복 제거
        all_codes: dict[str, dict] = {}
        for cat, stocks in categories.items():
            for stock in stocks:
                code = stock["code"]
                if code not in all_codes:
                    all_codes[code] = stock

        print(f"\n[Simulation] 중복 제거 후 총 {len(all_codes)}개 종목 일봉 조회")

        # 일봉 데이터에서 해당 날짜의 시가/종가 추출
        prices: dict[str, Optional[dict]] = {}
        for i, (code, stock) in enumerate(all_codes.items(), 1):
            print(f"  [{i}/{len(all_codes)}] {stock['name']} ({code})...", end=" ")
            price = self.fetch_daily_price(code, target_date)
            prices[code] = price
            if price:
                ret = (price["close_price"] - price["open_price"]) / price["open_price"] * 100
                print(f"시가:{price['open_price']:,} 종가:{price['close_price']:,} 수익률:{ret:+.2f}%")
            else:
                print("데이터 없음")
            time.sleep(0.1)

        # 카테고리별 결과 조립
        result_categories = {}
        for cat, stocks in categories.items():
            cat_results = []
            for stock in stocks:
                code = stock["code"]
                price = prices.get(code)
                open_p = price["open_price"] if price else None
                close_p = price["close_price"] if price else None
                high_p = price["high_price"] if price else None
                entry: dict = {
                    "code": code,
                    "name": stock["name"],
                    "market": stock["market"],
                    "open_price": open_p,
                    "close_price": close_p,
                    "high_price": high_p,
                    "return_pct": round(
                        (close_p - open_p) / open_p * 100, 2
                    ) if open_p and close_p and open_p > 0 else None,
                    "high_return_pct": round(
                        (high_p - open_p) / open_p * 100, 2
                    ) if open_p and high_p and open_p > 0 else None,
                }
                cat_results.append(entry)
            result_categories[cat] = cat_results

        simulation_data = {
            "date": target_date,
            "collected_at": now.isoformat(),
            "categories": result_categories,
        }

        return self._save_simulation(simulation_data)

    def _get_strong_buy_from_history(self, target_date: str) -> dict[str, list[dict]]:
        """히스토리 파일에서 해당 날짜의 적극매수 종목 추출"""
        categories: dict[str, list[dict]] = {"vision": [], "kis": [], "combined": []}

        # Vision 히스토리
        vision_index = self._load_json(self.RESULTS_DIR / "vision" / "history_index.json")
        if vision_index:
            for item in vision_index.get("history", []):
                if item.get("date") == target_date:
                    data = self._load_json(
                        self.RESULTS_DIR / "vision" / "history" / item["filename"]
                    )
                    if data:
                        for stock in data.get("results", []):
                            if stock.get("signal") == "적극매수":
                                market = stock.get("market", "")
                                if market in ("코스피", "KOSPI"):
                                    market = "KOSPI"
                                elif market in ("코스닥", "KOSDAQ"):
                                    market = "KOSDAQ"
                                categories["vision"].append({
                                    "code": stock["code"],
                                    "name": stock["name"],
                                    "market": market,
                                })
                    break

        # KIS 히스토리
        kis_index = self._load_json(self.RESULTS_DIR / "kis" / "history_index.json")
        if kis_index:
            for item in kis_index.get("history", []):
                if item.get("date") == target_date:
                    data = self._load_json(
                        self.RESULTS_DIR / "kis" / "history" / item["filename"]
                    )
                    if data:
                        for stock in data.get("results", []):
                            if stock.get("signal") == "적극매수":
                                categories["kis"].append({
                                    "code": stock["code"],
                                    "name": stock["name"],
                                    "market": stock.get("market", ""),
                                })
                    break

        # Combined 히스토리
        combined_index = self._load_json(self.RESULTS_DIR / "combined" / "history_index.json")
        if combined_index:
            for item in combined_index.get("history", []):
                if item.get("date") == target_date:
                    data = self._load_json(
                        self.RESULTS_DIR / "combined" / "history" / item["filename"]
                    )
                    if data:
                        for stock in data.get("stocks", []):
                            if (stock.get("match_status") == "match"
                                    and stock.get("vision_signal") == "적극매수"):
                                categories["combined"].append({
                                    "code": stock["code"],
                                    "name": stock["name"],
                                    "market": stock.get("market", ""),
                                })
                    break

        for cat, stocks in categories.items():
            print(f"[Simulation] {cat} 적극매수 ({target_date}): {len(stocks)}개")

        return categories

    def _save_simulation(self, data: dict) -> dict:
        """시뮬레이션 결과 저장 & 인덱스 갱신"""
        date_str = data["date"]
        filename = f"simulation_{date_str}.json"
        filepath = self.SIMULATION_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n[Simulation] 저장: {filepath}")

        # 인덱스 갱신
        self._update_index(data, filename)

        return data

    def _update_index(self, data: dict, filename: str):
        """simulation_index.json 갱신"""
        index_path = self.SIMULATION_DIR / "simulation_index.json"

        index = self._load_json(index_path) or {
            "updated_at": "",
            "total_records": 0,
            "history": [],
        }

        date_str = data["date"]
        # 카테고리별 종목 수 집계
        category_counts = {}
        total_stocks = 0
        for cat, stocks in data.get("categories", {}).items():
            category_counts[cat] = len(stocks)
            total_stocks += len(stocks)

        # 기존 같은 날짜 항목 제거
        index["history"] = [
            h for h in index["history"] if h.get("date") != date_str
        ]

        # 새 항목 추가
        index["history"].insert(0, {
            "date": date_str,
            "filename": filename,
            "total_stocks": total_stocks,
            "category_counts": category_counts,
        })

        # 날짜순 정렬 (최신 먼저)
        index["history"].sort(key=lambda x: x["date"], reverse=True)
        index["updated_at"] = data["collected_at"]
        index["total_records"] = len(index["history"])

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        print(f"[Simulation] 인덱스 갱신: {index['total_records']}개 기록")
