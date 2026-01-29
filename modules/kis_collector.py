"""
한국투자증권 API 통합 데이터 수집기
- 거래량/등락률 Top30 종목 수집
- 종목별 상세 데이터 수집
- JSON 형태로 저장
"""
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import KIS_OUTPUT_DIR
from modules.kis_client import KISClient
from modules.kis_rank import KISRankAPI
from modules.kis_stock_detail import KISStockDetailAPI


class KISDataCollector:
    """KIS API 데이터 통합 수집기"""

    def __init__(self):
        self.client = KISClient()
        self.rank_api = KISRankAPI(self.client)
        self.detail_api = KISStockDetailAPI(self.client)

        # 출력 디렉토리 생성
        self.output_dir = KIS_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def collect_top30_stocks(self, exclude_etf: bool = True) -> Dict[str, Any]:
        """코스피/코스닥 Top30 종목 수집 (거래량 + 등락률)

        Args:
            exclude_etf: ETF/ETN 제외 여부

        Returns:
            {
                "volume": {...},
                "fluctuation": {...},
                "unique_stock_codes": [...],
                "unique_stock_count": int,
                "collected_at": str,
            }
        """
        print("\n" + "=" * 60)
        print(f"[KIS] Top30 종목 수집 시작 (ETF 제외: {exclude_etf})")
        print("=" * 60)

        return self.rank_api.get_all_top30(exclude_etf=exclude_etf)

    def collect_top_stocks(
        self,
        limit: int = 50,
        exclude_etf: bool = True,
    ) -> Dict[str, Any]:
        """코스피/코스닥 Top N 종목 수집 (거래량 기준)

        Args:
            limit: 시장별 종목 수 (기본 50)
            exclude_etf: ETF/ETN 제외 여부

        Returns:
            {
                "kospi": [...],
                "kosdaq": [...],
                "unique_stock_codes": [...],
                "unique_stock_count": int,
                "collected_at": str,
            }
        """
        print("\n" + "=" * 60)
        print(f"[KIS] 코스피/코스닥 Top{limit} 종목 수집 (ETF 제외: {exclude_etf})")
        print("=" * 60)

        # 코스피 Top N
        kospi = self.rank_api.get_volume_rank(
            market="KOSPI", limit=limit, exclude_etf=exclude_etf
        )
        print(f"  코스피: {len(kospi)}개")

        # 코스닥 Top N
        kosdaq = self.rank_api.get_volume_rank(
            market="KOSDAQ", limit=limit, exclude_etf=exclude_etf
        )
        print(f"  코스닥: {len(kosdaq)}개")

        # 고유 종목 코드
        unique_codes = list(set(
            [s["code"] for s in kospi] + [s["code"] for s in kosdaq]
        ))

        return {
            "kospi": kospi,
            "kosdaq": kosdaq,
            "kospi_count": len(kospi),
            "kosdaq_count": len(kosdaq),
            "unique_stock_codes": unique_codes,
            "unique_stock_count": len(unique_codes),
            "collected_at": datetime.now().isoformat(),
            "exclude_etf": exclude_etf,
        }

    def collect_stock_details(
        self,
        stock_codes: List[str],
        include_chart: bool = True,
        include_ticks: bool = False,
        include_extended: bool = True,
    ) -> List[Dict[str, Any]]:
        """종목별 상세 데이터 수집

        Args:
            stock_codes: 종목코드 리스트
            include_chart: 차트 데이터 포함 여부
            include_ticks: 틱 데이터 포함 여부
            include_extended: 확장 데이터 포함 (재무, 프로그램매매 등)

        Returns:
            종목별 상세 데이터 리스트
        """
        print(f"\n[KIS] {len(stock_codes)}개 종목 상세 데이터 수집 시작")
        print("-" * 60)

        return self.detail_api.get_multiple_stocks_data(
            stock_codes=stock_codes,
            include_chart=include_chart,
            include_ticks=include_ticks,
            include_extended=include_extended,
            delay=0.2,  # API 호출 간 0.2초 지연
        )

    def collect_all(
        self,
        include_chart: bool = True,
        include_ticks: bool = False,
        exclude_etf: bool = True,
    ) -> Dict[str, Any]:
        """전체 데이터 수집 (Top30 + 상세 데이터)

        Args:
            include_chart: 차트 데이터 포함 여부
            include_ticks: 틱 데이터 포함 여부
            exclude_etf: ETF/ETN 제외 여부

        Returns:
            종합 데이터
        """
        start_time = datetime.now()
        print("\n" + "=" * 60)
        print(f"[KIS] 전체 데이터 수집 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # 1. Top30 종목 수집
        top30_data = self.collect_top30_stocks(exclude_etf=exclude_etf)
        unique_codes = top30_data.get("unique_stock_codes", [])

        print(f"\n[KIS] 총 {len(unique_codes)}개 고유 종목 발견")

        # 2. 종목별 상세 데이터 수집
        print(f"\n[KIS] 상세 데이터 수집 시작...")
        stock_details = self.collect_stock_details(
            stock_codes=unique_codes,
            include_chart=include_chart,
            include_ticks=include_ticks,
        )

        # 3. 데이터 통합
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = {
            "meta": {
                "collected_at": end_time.isoformat(),
                "collection_duration_seconds": duration,
                "total_unique_stocks": len(unique_codes),
                "exclude_etf": exclude_etf,
            },
            "rankings": top30_data,
            "stock_details": {
                detail["stock_code"]: detail
                for detail in stock_details
                if "stock_code" in detail
            },
        }

        print("\n" + "=" * 60)
        print(f"[KIS] 데이터 수집 완료: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[KIS] 소요 시간: {duration:.1f}초")
        print("=" * 60)

        return result

    def collect_top50_full(
        self,
        include_chart: bool = True,
        include_ticks: bool = False,
        include_extended: bool = True,
        exclude_etf: bool = True,
    ) -> Dict[str, Any]:
        """코스피/코스닥 Top50 전체 데이터 수집

        Args:
            include_chart: 차트 데이터 포함 여부
            include_ticks: 틱 데이터 포함 여부
            include_extended: 확장 데이터 포함 (재무, 프로그램매매 등)
            exclude_etf: ETF/ETN 제외 여부

        Returns:
            {
                "meta": {...},
                "rankings": {
                    "kospi": [...],
                    "kosdaq": [...],
                },
                "stock_details": {
                    "005930": {...},
                    ...
                }
            }
        """
        start_time = datetime.now()
        print("\n" + "=" * 60)
        print(f"[KIS] Top50 전체 데이터 수집 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[KIS] ETF 제외: {exclude_etf}, 확장 데이터: {include_extended}")
        print("=" * 60)

        # 1. 코스피/코스닥 Top50 종목 수집
        top_stocks = self.collect_top_stocks(limit=50, exclude_etf=exclude_etf)
        unique_codes = top_stocks.get("unique_stock_codes", [])

        print(f"\n[KIS] 총 {len(unique_codes)}개 고유 종목 발견")
        print(f"  코스피: {top_stocks['kospi_count']}개")
        print(f"  코스닥: {top_stocks['kosdaq_count']}개")

        # 2. 종목별 상세 데이터 수집
        print(f"\n[KIS] 상세 데이터 수집 시작...")
        stock_details = self.collect_stock_details(
            stock_codes=unique_codes,
            include_chart=include_chart,
            include_ticks=include_ticks,
            include_extended=include_extended,
        )

        # 3. 데이터 통합
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = {
            "meta": {
                "collected_at": end_time.isoformat(),
                "collection_duration_seconds": duration,
                "total_unique_stocks": len(unique_codes),
                "kospi_count": top_stocks["kospi_count"],
                "kosdaq_count": top_stocks["kosdaq_count"],
                "exclude_etf": exclude_etf,
                "include_extended": include_extended,
            },
            "rankings": {
                "kospi": top_stocks["kospi"],
                "kosdaq": top_stocks["kosdaq"],
            },
            "stock_details": {
                detail["stock_code"]: detail
                for detail in stock_details
                if "stock_code" in detail
            },
        }

        print("\n" + "=" * 60)
        print(f"[KIS] 데이터 수집 완료: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[KIS] 소요 시간: {duration:.1f}초")
        print(f"[KIS] 수집 종목: {len(unique_codes)}개")
        print("=" * 60)

        return result

    def save_to_json(self, data: Dict[str, Any], filename: str = None) -> Path:
        """데이터를 JSON 파일로 저장

        Args:
            data: 저장할 데이터
            filename: 파일명 (없으면 타임스탬프 사용)

        Returns:
            저장된 파일 경로
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"kis_data_{timestamp}.json"

        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n[KIS] 데이터 저장 완료: {filepath}")
        return filepath

    def save_latest(self, data: Dict[str, Any]) -> Path:
        """최신 데이터로 저장 (latest.json)

        Args:
            data: 저장할 데이터

        Returns:
            저장된 파일 경로
        """
        return self.save_to_json(data, "latest.json")

    def run(
        self,
        include_chart: bool = True,
        include_ticks: bool = False,
        save_timestamped: bool = True,
        exclude_etf: bool = True,
    ) -> Dict[str, Any]:
        """데이터 수집 실행 및 저장

        Args:
            include_chart: 차트 데이터 포함 여부
            include_ticks: 틱 데이터 포함 여부
            save_timestamped: 타임스탬프 파일도 저장 여부
            exclude_etf: ETF/ETN 제외 여부

        Returns:
            수집된 데이터
        """
        # 데이터 수집
        data = self.collect_all(
            include_chart=include_chart,
            include_ticks=include_ticks,
            exclude_etf=exclude_etf,
        )

        # 최신 파일로 저장
        self.save_latest(data)

        # 타임스탬프 파일 저장 (선택)
        if save_timestamped:
            self.save_to_json(data)

        return data

    def run_top50(
        self,
        include_chart: bool = True,
        include_ticks: bool = False,
        include_extended: bool = True,
        exclude_etf: bool = True,
        save_timestamped: bool = True,
    ) -> Dict[str, Any]:
        """Top50 데이터 수집 실행 및 저장

        Args:
            include_chart: 차트 데이터 포함 여부
            include_ticks: 틱 데이터 포함 여부
            include_extended: 확장 데이터 포함 (재무, 프로그램매매 등)
            exclude_etf: ETF/ETN 제외 여부
            save_timestamped: 타임스탬프 파일도 저장 여부

        Returns:
            수집된 데이터
        """
        # 데이터 수집
        data = self.collect_top50_full(
            include_chart=include_chart,
            include_ticks=include_ticks,
            include_extended=include_extended,
            exclude_etf=exclude_etf,
        )

        # 최신 파일로 저장
        self.save_to_json(data, "top50_latest.json")

        # 타임스탬프 파일 저장 (선택)
        if save_timestamped:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.save_to_json(data, f"top50_{timestamp}.json")

        return data


def print_summary(data: Dict[str, Any]):
    """수집 결과 요약 출력"""
    print("\n" + "=" * 60)
    print("[KIS] 수집 결과 요약")
    print("=" * 60)

    meta = data.get("meta", {})
    print(f"\n수집 시간: {meta.get('collected_at', 'N/A')}")
    print(f"소요 시간: {meta.get('collection_duration_seconds', 0):.1f}초")
    print(f"총 종목 수: {meta.get('total_unique_stocks', 0)}개")

    # 순위 요약
    rankings = data.get("rankings", {})

    print("\n[거래량 Top 5]")
    vol_kospi = rankings.get("volume", {}).get("kospi", [])[:5]
    for stock in vol_kospi:
        print(f"  KOSPI: {stock['rank']:2d}. {stock['name']:<12s} "
              f"({stock['code']}) {stock['current_price']:>10,}원 "
              f"{stock['change_rate']:>+6.2f}%")

    vol_kosdaq = rankings.get("volume", {}).get("kosdaq", [])[:5]
    for stock in vol_kosdaq:
        print(f"  KOSDAQ: {stock['rank']:2d}. {stock['name']:<12s} "
              f"({stock['code']}) {stock['current_price']:>10,}원 "
              f"{stock['change_rate']:>+6.2f}%")

    print("\n[상승률 Top 5]")
    fluc_kospi_up = rankings.get("fluctuation", {}).get("kospi_up", [])[:5]
    for stock in fluc_kospi_up:
        print(f"  KOSPI: {stock['rank']:2d}. {stock['name']:<12s} "
              f"({stock['code']}) {stock['current_price']:>10,}원 "
              f"{stock['change_rate']:>+6.2f}%")

    print("\n[하락률 Top 5]")
    fluc_kospi_down = rankings.get("fluctuation", {}).get("kospi_down", [])[:5]
    for stock in fluc_kospi_down:
        print(f"  KOSPI: {stock['rank']:2d}. {stock['name']:<12s} "
              f"({stock['code']}) {stock['current_price']:>10,}원 "
              f"{stock['change_rate']:>+6.2f}%")


def main():
    """메인 실행"""
    try:
        collector = KISDataCollector()

        # 전체 데이터 수집 실행
        data = collector.run(
            include_chart=True,     # 일봉 차트 포함
            include_ticks=False,    # 틱 데이터는 양이 많아서 제외
            save_timestamped=True,  # 타임스탬프 파일도 저장
        )

        # 결과 요약 출력
        print_summary(data)

    except Exception as e:
        print(f"\n[ERROR] 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
