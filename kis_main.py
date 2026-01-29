#!/usr/bin/env python3
"""
한국투자증권 API 데이터 수집 메인 스크립트

사용법:
    python kis_main.py                    # 전체 데이터 수집
    python kis_main.py --rank-only        # 순위 데이터만 수집
    python kis_main.py --test             # API 연결 테스트
    python kis_main.py --token-status     # 토큰 상태 확인
    python kis_main.py --stock 005930     # 특정 종목 데이터 수집

환경변수 필요:
    KIS_APP_KEY      - 한국투자증권 App Key
    KIS_APP_SECRET   - 한국투자증권 App Secret

주의사항:
    - 순위분석 API는 모의투자에서 지원되지 않습니다 (실전투자 계정 필요)
    - Access Token은 1일 1회 발급 제한이 있습니다 (자동 캐싱됨)
"""
import argparse
import json
import sys
from pathlib import Path

# 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from modules.kis_client import KISClient, TokenRefreshLimitError
from modules.kis_rank import KISRankAPI
from modules.kis_stock_detail import KISStockDetailAPI
from modules.kis_collector import KISDataCollector, print_summary
from config.settings import KIS_OUTPUT_DIR


def check_token_status():
    """토큰 상태 확인"""
    print("\n[KIS] 토큰 상태 확인")
    print("=" * 60)

    try:
        client = KISClient()
        status = client.get_token_status()

        print(f"\n토큰 보유: {'예' if status.get('has_token') else '아니오'}")
        print(f"토큰 유효: {'예' if status.get('is_valid') else '아니오'}")
        print(f"재발급 가능: {'예' if status.get('can_refresh') else '아니오 (1일 1회 제한)'}")

        if status.get('expires_at'):
            print(f"\n만료 시간: {status.get('expires_at')}")
            print(f"남은 시간: {status.get('remaining_hours', 0):.1f}시간")

        if status.get('issued_at'):
            print(f"발급 시간: {status.get('issued_at')}")

        if not status.get('is_valid') and not status.get('can_refresh'):
            print("\n[경고] 토큰이 만료되었고, 1일 1회 발급 제한으로 재발급이 불가합니다.")
            print("       API 호출 시 먼저 캐시된 토큰으로 시도하고, 실패 시 에러가 발생합니다.")

    except Exception as e:
        print(f"\n[실패] {e}")
        return 1

    return 0


def test_connection():
    """API 연결 테스트"""
    print("\n[KIS] API 연결 테스트")
    print("=" * 60)

    try:
        client = KISClient()

        # 토큰 상태 출력
        status = client.get_token_status()
        print(f"\n토큰 유효: {'예' if status.get('is_valid') else '아니오'}")
        if status.get('remaining_hours'):
            print(f"남은 시간: {status.get('remaining_hours', 0):.1f}시간")

        # 삼성전자 현재가 조회
        print("\n[삼성전자 현재가 테스트]")
        result = client.get_stock_price("005930")
        if result.get("rt_cd") == "0":
            output = result.get("output", {})
            print(f"  현재가: {int(output.get('stck_prpr', 0)):,}원")
            print(f"  등락률: {output.get('prdy_ctrt', 'N/A')}%")
            print("\n[결과] API 연결 정상")
        else:
            print(f"\n[경고] API 오류: {result.get('msg1', 'Unknown')}")

    except TokenRefreshLimitError as e:
        print(f"\n[토큰 제한] {e}")
        return 1
    except Exception as e:
        print(f"\n[실패] {e}")
        return 1

    return 0


def collect_rank_only():
    """순위 데이터만 수집"""
    print("\n[KIS] 순위 데이터 수집")
    print("=" * 60)

    try:
        collector = KISDataCollector()
        data = collector.collect_top30_stocks()

        # 저장
        output_path = KIS_OUTPUT_DIR / "rankings.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n저장 완료: {output_path}")

        # 요약 출력
        print("\n[거래량 Top 10 - 코스피]")
        for stock in data.get("volume", {}).get("kospi", [])[:10]:
            print(f"  {stock['rank']:2d}. {stock['name']:<15s} ({stock['code']}) "
                  f"{stock['current_price']:>10,}원 {stock['change_rate']:>+6.2f}%")

        print("\n[거래량 Top 10 - 코스닥]")
        for stock in data.get("volume", {}).get("kosdaq", [])[:10]:
            print(f"  {stock['rank']:2d}. {stock['name']:<15s} ({stock['code']}) "
                  f"{stock['current_price']:>10,}원 {stock['change_rate']:>+6.2f}%")

    except TokenRefreshLimitError as e:
        print(f"\n[토큰 제한] {e}")
        return 1
    except Exception as e:
        print(f"\n[실패] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


def collect_stock(stock_code: str):
    """특정 종목 데이터 수집"""
    print(f"\n[KIS] 종목 데이터 수집: {stock_code}")
    print("=" * 60)

    try:
        api = KISStockDetailAPI()
        data = api.get_all_stock_data(
            stock_code=stock_code,
            include_chart=True,
            include_ticks=True,
        )

        # 저장
        output_path = KIS_OUTPUT_DIR / f"stock_{stock_code}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n저장 완료: {output_path}")

        # 요약 출력
        price = data.get("current_price", {})
        if "error" not in price:
            print(f"\n[{price.get('stock_name', stock_code)}]")
            print(f"  현재가: {price.get('current_price', 0):,}원")
            print(f"  전일대비: {price.get('change_price', 0):+,}원 "
                  f"({price.get('change_rate', 0):+.2f}%)")
            print(f"  거래량: {price.get('volume', 0):,}")
            print(f"  시가총액: {price.get('market_cap', 0):,}억원")
            print(f"  PER: {price.get('per', 0):.2f}")
            print(f"  PBR: {price.get('pbr', 0):.2f}")

    except TokenRefreshLimitError as e:
        print(f"\n[토큰 제한] {e}")
        return 1
    except Exception as e:
        print(f"\n[실패] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


def collect_all():
    """전체 데이터 수집"""
    try:
        collector = KISDataCollector()
        data = collector.run(
            include_chart=True,
            include_ticks=False,
            save_timestamped=True,
        )
        print_summary(data)

    except TokenRefreshLimitError as e:
        print(f"\n[토큰 제한] {e}")
        return 1
    except Exception as e:
        print(f"\n[실패] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="한국투자증권 API 데이터 수집",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="API 연결 테스트"
    )
    parser.add_argument(
        "--token-status",
        action="store_true",
        help="토큰 상태 확인"
    )
    parser.add_argument(
        "--rank-only",
        action="store_true",
        help="순위 데이터만 수집"
    )
    parser.add_argument(
        "--stock",
        type=str,
        help="특정 종목 데이터 수집 (종목코드)"
    )

    args = parser.parse_args()

    # 실행
    if args.token_status:
        return check_token_status()
    elif args.test:
        return test_connection()
    elif args.rank_only:
        return collect_rank_only()
    elif args.stock:
        return collect_stock(args.stock)
    else:
        return collect_all()


if __name__ == "__main__":
    exit(main())
