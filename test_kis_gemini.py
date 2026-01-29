"""
KIS 데이터 Gemini 분석 테스트
"""
import json
from pathlib import Path

from modules.kis_data_transformer import KISDataTransformer
from modules.ai_engine import analyze_kis_data

def main():
    """테스트 실행"""
    # 1. 변환된 데이터 로드
    print("=== KIS 데이터 Gemini 분석 테스트 ===\n")

    transformer = KISDataTransformer()

    # gemini 파일이 있으면 로드, 없으면 변환 실행
    gemini_file = Path("results/kis/top50_gemini.json")
    if gemini_file.exists():
        print(f"[1/3] 기존 변환 데이터 로드: {gemini_file}")
        with open(gemini_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        print("[1/3] 데이터 변환 실행...")
        data = transformer.run()

    stocks = data.get("stocks", {})
    print(f"  총 {len(stocks)}개 종목 데이터 로드 완료\n")

    # 2. 테스트용으로 상위 5개 종목만 선택
    # 거래량 순위 기준으로 정렬하여 선택
    sorted_codes = sorted(
        stocks.keys(),
        key=lambda c: stocks[c].get("ranking", {}).get("volume_rank", 999)
    )
    test_codes = sorted_codes[:5]

    print("[2/3] 테스트 대상 종목 (거래량 상위 5개):")
    for code in test_codes:
        stock = stocks[code]
        print(f"  - {stock['name']} ({code}) | "
              f"현재가: {stock['price']['current']:,}원 | "
              f"등락률: {stock['price']['change_rate_pct']:+.2f}%")

    # 3. Gemini 분석 실행
    print("\n[3/3] Gemini 분석 실행...")
    results = analyze_kis_data(data, stock_codes=test_codes)

    if not results:
        print("\n[ERROR] 분석 결과가 없습니다.")
        return 1

    # 4. 결과 출력
    print("\n" + "=" * 70)
    print("분석 결과")
    print("=" * 70)

    for r in results:
        print(f"\n[{r.get('name', 'N/A')}] ({r.get('code', 'N/A')}) - {r.get('market', 'N/A')}")
        print(f"  현재가: {r.get('current_price', 0):,}원 ({r.get('change_rate', 0):+.2f}%)")
        print(f"  시그널: {r.get('signal', 'N/A')}")
        print(f"  분석근거: {r.get('reason', 'N/A')}")

        key_factors = r.get("key_factors", {})
        if key_factors:
            print(f"  핵심요인:")
            print(f"    - 가격추세: {key_factors.get('price_trend', 'N/A')}")
            print(f"    - 거래량: {key_factors.get('volume_signal', 'N/A')}")
            print(f"    - 외인동향: {key_factors.get('foreign_flow', 'N/A')}")
            print(f"    - 기관동향: {key_factors.get('institution_flow', 'N/A')}")
            print(f"    - 밸류에이션: {key_factors.get('valuation', 'N/A')}")

        print(f"  위험도: {r.get('risk_level', 'N/A')} | 신뢰도: {r.get('confidence', 0):.0%}")

    # 5. 결과 저장
    output_path = Path("results/kis/analysis_result.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "analysis_time": results[0].get("analysis_time") if results else None,
            "total_analyzed": len(results),
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장 완료: {output_path}")

    # 6. 시그널 요약
    print("\n" + "=" * 70)
    print("시그널 요약")
    print("=" * 70)

    signal_counts = {}
    for r in results:
        sig = r.get("signal", "중립")
        signal_counts[sig] = signal_counts.get(sig, 0) + 1

    for signal, count in sorted(signal_counts.items()):
        print(f"  {signal}: {count}개")

    return 0


if __name__ == "__main__":
    exit(main())
