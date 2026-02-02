"""
AI Vision Stock Signal Analyzer - 메인 실행 파일
"""
import asyncio
import shutil
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config.settings import CAPTURES_DIR, OUTPUT_DIR, ROOT_DIR
from modules.scraper import run_scraper
from modules.ai_engine import analyze_stocks_batch
from modules.utils import get_today_capture_dir, save_json, generate_markdown_report

# KST 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))

# Vision 배치 처리 설정
VISION_BATCH_SIZE = 40  # 40개씩 배치 처리


# 분석 결과 보존 기간 (일)
RESULTS_RETENTION_DAYS = 30


def cleanup_captures():
    """캡처 이미지 정리 (매 실행 전 모두 삭제)"""
    cleaned = 0

    if CAPTURES_DIR.exists():
        for item in CAPTURES_DIR.iterdir():
            if item.is_dir():
                try:
                    shutil.rmtree(item)
                    cleaned += 1
                except Exception as e:
                    print(f"  [WARN] 삭제 실패: {item} - {e}")

    return cleaned


def cleanup_old_results(results_dir: Path, retention_days: int = RESULTS_RETENTION_DAYS):
    """오래된 분석 결과 정리 (retention_days 이전 파일 삭제)"""
    history_dir = results_dir / "history"
    if not history_dir.exists():
        return 0

    cutoff_date = datetime.now(KST).replace(tzinfo=None) - timedelta(days=retention_days)
    cleaned = 0

    for item in history_dir.iterdir():
        if item.is_file() and item.suffix == ".json":
            try:
                # 파일명에서 날짜 추출 (vision_YYYY-MM-DD.json)
                date_str = item.stem.replace("vision_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if file_date < cutoff_date:
                    item.unlink()
                    cleaned += 1
                    print(f"  [삭제] {item.name} ({retention_days}일 초과)")
            except (ValueError, Exception) as e:
                continue

    return cleaned


def update_history_index(results_dir: Path):
    """히스토리 인덱스 파일 생성/갱신"""
    history_dir = results_dir / "history"
    if not history_dir.exists():
        history_dir.mkdir(parents=True, exist_ok=True)

    # 히스토리 파일 목록 수집
    history_files = []
    for item in sorted(history_dir.iterdir(), reverse=True):
        if item.is_file() and item.suffix == ".json":
            try:
                date_str = item.stem.replace("vision_", "")
                # 파일에서 요약 정보 읽기
                with open(item, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 시그널 카운트 계산
                signal_counts = {}
                for r in data.get("results", []):
                    signal = r.get("signal", "중립")
                    signal_counts[signal] = signal_counts.get(signal, 0) + 1

                history_files.append({
                    "date": date_str,
                    "filename": item.name,
                    "total_stocks": data.get("total_stocks", 0),
                    "signals": signal_counts
                })
            except Exception as e:
                continue

    # 인덱스 파일 저장
    index_data = {
        "updated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
        "retention_days": RESULTS_RETENTION_DAYS,
        "total_records": len(history_files),
        "history": history_files
    }

    index_path = results_dir / "history_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    return len(history_files)


async def main():
    """메인 파이프라인 실행"""
    # KST 기준 현재 시간
    now_kst = datetime.now(KST)

    print("=" * 60)
    print("  AI Vision Stock Signal Analyzer (AVSSA)")
    print(f"  실행 시간: {now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST")
    print("=" * 60)

    # Phase 0: 캡처 이미지 정리
    print("\n=== Phase 0: 캡처 이미지 정리 ===\n")
    cleaned_captures = cleanup_captures()
    print(f"캡처 폴더 {cleaned_captures}개 삭제")

    # results 디렉토리 준비
    results_dir = ROOT_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # 오래된 분석 결과 정리 (30일 초과)
    print(f"\n=== 오래된 분석 결과 정리 ({RESULTS_RETENTION_DAYS}일 초과) ===\n")
    cleaned_results = cleanup_old_results(results_dir)
    if cleaned_results > 0:
        print(f"총 {cleaned_results}개 파일 삭제")
    else:
        print("삭제할 파일 없음")

    # Phase 1 & 2: 종목 수집 및 스크린샷 캡처
    scrape_results = await run_scraper()

    # 캡처 디렉토리
    capture_dir = get_today_capture_dir(CAPTURES_DIR)

    # Phase 3: AI 배치 분석 (VISION_BATCH_SIZE개씩 나눠서 처리)
    print(f"\n=== Phase 3: AI 배치 분석 ({VISION_BATCH_SIZE}개씩 처리) ===\n")

    all_results = []
    total_stocks = len(scrape_results)
    total_batches = (total_stocks + VISION_BATCH_SIZE - 1) // VISION_BATCH_SIZE

    for i in range(0, total_stocks, VISION_BATCH_SIZE):
        batch_stocks = scrape_results[i:i + VISION_BATCH_SIZE]
        batch_num = i // VISION_BATCH_SIZE + 1

        print(f"\n--- Vision 배치 {batch_num}/{total_batches} ({len(batch_stocks)}개 종목) ---")

        batch_results = analyze_stocks_batch(batch_stocks, capture_dir)

        if batch_results:
            all_results.extend(batch_results)
            print(f"[배치 {batch_num}] 완료: {len(batch_results)}개 분석")
        else:
            print(f"[배치 {batch_num}] 실패: 결과 없음")

        # 배치 간 대기 (rate limit 방지)
        if i + VISION_BATCH_SIZE < total_stocks:
            print("다음 배치 대기 중... (5초)")
            time.sleep(5)

    print(f"\n총 분석 완료: {len(all_results)}/{total_stocks}개 종목")
    analysis_results = all_results

    # Phase 4: 결과 저장
    print("\n=== Phase 4: 결과 저장 ===\n")

    # KST 기준 오늘 날짜
    today = datetime.now(KST).strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 분석 데이터 구성
    output_data = {
        "date": today,
        "total_stocks": len(analysis_results),
        "results": analysis_results
    }

    # 1. output/ 에 저장 (로컬 백업)
    json_path = OUTPUT_DIR / f"analysis_{today}.json"
    save_json(output_data, json_path)
    print(f"JSON 저장: {json_path}")

    # 2. results/vision_analysis.json 저장 (분석 결과)
    analysis_path = results_dir / "vision_analysis.json"
    save_json(output_data, analysis_path)
    print(f"Vision 분석 결과 저장: {analysis_path}")

    # 3. results/history/ 에 날짜별 저장 (30일 보관)
    history_dir = results_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = history_dir / f"vision_{today}.json"
    save_json(output_data, history_path)
    print(f"Vision History 저장: {history_path}")

    # 4. 히스토리 인덱스 갱신
    history_count = update_history_index(results_dir)
    print(f"히스토리 인덱스 갱신: {history_count}개 기록")

    # 마크다운 리포트 저장
    md_path = OUTPUT_DIR / f"report_{today}.md"
    generate_markdown_report(analysis_results, md_path)
    print(f"리포트 저장: {md_path}")

    # 시그널 요약
    print("\n=== 시그널 요약 ===\n")
    signal_count = {}
    for r in analysis_results:
        signal = r.get("signal", "N/A")
        signal_count[signal] = signal_count.get(signal, 0) + 1

    for signal, count in sorted(signal_count.items()):
        print(f"  {signal}: {count}개")

    print("\n" + "=" * 60)
    print("  분석 완료!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
