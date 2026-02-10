#!/usr/bin/env python3
"""
모의투자 시뮬레이션 데이터 수집 메인 스크립트

사용법:
    python simulation_main.py                    # 당일 시뮬레이션 데이터 수집
    python simulation_main.py --backfill         # 히스토리 기반 과거 데이터 일괄 수집
    python simulation_main.py --date 2026-02-07  # 특정 날짜 수집
    python simulation_main.py --test             # 적극매수 종목 목록만 확인

환경변수 필요:
    KIS_APP_KEY      - 한국투자증권 App Key
    KIS_APP_SECRET   - 한국투자증권 App Secret
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.simulation_collector import SimulationCollector
from modules.kis_client import KISClient, TokenRefreshLimitError


def collect_today():
    """당일 시뮬레이션 데이터 수집"""
    print("\n[Simulation] 당일 수집 모드")
    print("=" * 60)

    try:
        collector = SimulationCollector()
        data = collector.collect_today()

        # 결과 요약
        print("\n" + "=" * 60)
        print("[결과 요약]")
        for cat, stocks in data.get("categories", {}).items():
            priced = [s for s in stocks if s.get("return_pct") is not None]
            if priced:
                avg_ret = sum(s["return_pct"] for s in priced) / len(priced)
                print(f"  {cat}: {len(stocks)}종목 (수집: {len(priced)}), 평균 수익률: {avg_ret:+.2f}%")
            else:
                print(f"  {cat}: {len(stocks)}종목 (수집: 0)")

    except TokenRefreshLimitError as e:
        print(f"\n[토큰 제한] {e}")
        return 1
    except Exception as e:
        print(f"\n[실패] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


def collect_date(target_date: str):
    """특정 날짜 시뮬레이션 데이터 수집"""
    print(f"\n[Simulation] 특정 날짜 수집: {target_date}")
    print("=" * 60)

    try:
        collector = SimulationCollector()
        data = collector.collect_backfill(target_date)

        # 결과 요약
        print("\n" + "=" * 60)
        print("[결과 요약]")
        for cat, stocks in data.get("categories", {}).items():
            priced = [s for s in stocks if s.get("return_pct") is not None]
            if priced:
                avg_ret = sum(s["return_pct"] for s in priced) / len(priced)
                print(f"  {cat}: {len(stocks)}종목 (수집: {len(priced)}), 평균 수익률: {avg_ret:+.2f}%")
            else:
                print(f"  {cat}: {len(stocks)}종목 (수집: 0)")

    except TokenRefreshLimitError as e:
        print(f"\n[토큰 제한] {e}")
        return 1
    except Exception as e:
        print(f"\n[실패] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


def backfill():
    """히스토리 기반 과거 데이터 일괄 수집"""
    import json

    print("\n[Simulation] 백필 모드 (히스토리 기반)")
    print("=" * 60)

    try:
        collector = SimulationCollector()
        results_dir = Path(__file__).parent / "results"

        # 히스토리 인덱스에서 모든 날짜 수집
        all_dates = set()
        for source in ["vision", "kis", "combined"]:
            index_path = results_dir / source / "history_index.json"
            if index_path.exists():
                with open(index_path, "r", encoding="utf-8") as f:
                    index = json.load(f)
                for item in index.get("history", []):
                    all_dates.add(item["date"])

        # 이미 수집된 날짜 제외
        sim_index_path = results_dir / "simulation" / "simulation_index.json"
        existing_dates = set()
        if sim_index_path.exists():
            with open(sim_index_path, "r", encoding="utf-8") as f:
                sim_index = json.load(f)
            for item in sim_index.get("history", []):
                existing_dates.add(item["date"])

        new_dates = sorted(all_dates - existing_dates)
        if not new_dates:
            print("[Simulation] 수집할 새로운 날짜가 없습니다.")
            return 0

        print(f"[Simulation] 수집 대상: {len(new_dates)}일")
        for date in new_dates:
            print(f"  - {date}")

        # 날짜별 수집
        success = 0
        for i, date in enumerate(new_dates, 1):
            print(f"\n--- [{i}/{len(new_dates)}] {date} ---")
            try:
                collector.collect_backfill(date)
                success += 1
            except Exception as e:
                print(f"[실패] {date}: {e}")
            import time
            time.sleep(0.5)  # API rate limit

        print(f"\n[Simulation] 백필 완료: {success}/{len(new_dates)}일 수집")

    except TokenRefreshLimitError as e:
        print(f"\n[토큰 제한] {e}")
        return 1
    except Exception as e:
        print(f"\n[실패] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


def test_stocks():
    """적극매수 종목 목록만 확인 (가격 수집 없음)"""
    print("\n[Simulation] 테스트 모드 (적극매수 종목 확인)")
    print("=" * 60)

    try:
        collector = SimulationCollector()
        categories = collector.get_strong_buy_stocks()

        for cat, stocks in categories.items():
            print(f"\n[{cat.upper()}] 적극매수 {len(stocks)}개:")
            for s in stocks:
                print(f"  {s['name']} ({s['code']}) - {s['market']}")

    except Exception as e:
        print(f"\n[실패] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="모의투자 시뮬레이션 데이터 수집",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--backfill",
        action="store_true",
        help="히스토리 기반 과거 데이터 일괄 수집",
    )
    parser.add_argument(
        "--date",
        type=str,
        help="특정 날짜 수집 (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="적극매수 종목 목록만 확인 (가격 수집 없음)",
    )

    args = parser.parse_args()

    if args.test:
        return test_stocks()
    elif args.backfill:
        return backfill()
    elif args.date:
        return collect_date(args.date)
    else:
        return collect_today()


if __name__ == "__main__":
    exit(main())
