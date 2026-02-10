import { useEffect, useRef, useMemo } from 'react';
import { useSimulationIndex, useSimulationMultipleDates } from '@/hooks/useSimulationData';
import { useSimulationStore } from '@/store/simulationStore';
import { SimulationSummary, DateSelector, CategorySection, CollectionTrigger } from '@/components/simulation';
import { LoadingSpinner, EmptyState } from '@/components/common';
import type { SimulationData, SimulationCategory } from '@/services/types';

export function SimulationPage() {
  const { data: index, isLoading: indexLoading } = useSimulationIndex();
  const { activeDetailDate, selectAllDates } = useSimulationStore();
  const initializedRef = useRef(false);

  // 인덱스 최초 로드 시에만 전체 선택 (이후 사용자 조작은 존중)
  useEffect(() => {
    if (index && index.history.length > 0 && !initializedRef.current) {
      initializedRef.current = true;
      selectAllDates(index.history.map((h) => h.date));
    }
  }, [index, selectAllDates]);

  // 모든 날짜의 데이터 병렬 로딩 (선택 여부와 무관하게 통계 표시용)
  const filenames = useMemo(() => {
    if (!index) return [];
    return index.history
      .map((h) => h.filename)
      .filter((f): f is string => !!f);
  }, [index]);

  const queryResults = useSimulationMultipleDates(filenames);

  // 날짜별 데이터 맵 구성
  const dataByDate = useMemo(() => {
    const map: Record<string, SimulationData> = {};
    queryResults.forEach((result) => {
      if (result.data) {
        map[result.data.date] = result.data;
      }
    });
    return map;
  }, [queryResults]);

  const isAnyLoading = queryResults.some((r) => r.isLoading);

  // 상세보기 날짜의 데이터
  const detailData = activeDetailDate ? dataByDate[activeDetailDate] : null;

  if (indexLoading) {
    return <LoadingSpinner message="시뮬레이션 데이터 로딩 중..." />;
  }

  if (!index || index.history.length === 0) {
    return (
      <div className="space-y-4">
        <PageHeader />
        <EmptyState
          icon="📈"
          title="시뮬레이션 데이터 없음"
          description="아직 수집된 시뮬레이션 데이터가 없습니다. GitHub Actions에서 수동으로 수집하거나, 스케줄 실행을 기다려주세요."
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader />

      {/* 종합 수익률 */}
      <SimulationSummary dataByDate={dataByDate} />

      {/* 날짜 선택 */}
      <DateSelector items={index.history} dataByDate={dataByDate} />

      {/* 로딩 */}
      {isAnyLoading && (
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin w-5 h-5 border-2 border-accent-primary border-t-transparent rounded-full" />
          <span className="ml-2 text-sm text-text-muted">데이터 로딩 중...</span>
        </div>
      )}

      {/* 상세보기 */}
      {activeDetailDate && detailData && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-text-secondary flex items-center gap-2">
            <span className="w-2 h-2 bg-accent-primary rounded-full" />
            {activeDetailDate} 상세
          </h3>

          {(['vision', 'kis', 'combined'] as SimulationCategory[]).map((cat) => (
            <CategorySection
              key={cat}
              category={cat}
              stocks={detailData.categories[cat] || []}
              date={activeDetailDate}
            />
          ))}
        </div>
      )}

      {activeDetailDate && !detailData && !isAnyLoading && (
        <p className="text-sm text-text-muted text-center py-4">
          {activeDetailDate} 데이터를 로딩할 수 없습니다.
        </p>
      )}
    </div>
  );
}

function PageHeader() {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h2 className="text-lg md:text-xl font-bold">모의투자 시뮬레이션</h2>
        <p className="text-xs text-text-muted mt-0.5">
          적극매수 시그널 종목의 시가 매수 → 종가 매도 수익률
        </p>
      </div>
      <CollectionTrigger />
    </div>
  );
}
