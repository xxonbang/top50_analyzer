import { useEffect, useRef, useMemo, useState } from 'react';
import { useSimulationIndex, useSimulationMultipleDates } from '@/hooks/useSimulationData';
import { useSimulationStore } from '@/store/simulationStore';
import { useAuthStore } from '@/store/authStore';
import type { SimulationMode } from '@/store/simulationStore';
import { SimulationSummary, DateSelector, CategorySection, CollectionTrigger, AnalysisTimeSelector } from '@/components/simulation';
import { useAnalysisTimeOverride } from '@/hooks/useAnalysisTimeOverride';
import { LoadingSpinner, EmptyState } from '@/components/common';
import { cn } from '@/lib/utils';
import { isMarketOpen } from '@/lib/marketCalendar';
import type { AvailableTime } from '@/hooks/useAnalysisTimeOverride';
import type { SimulationData, SimulationCategory } from '@/services/types';

export function SimulationPage() {
  const { data: index, isLoading: indexLoading } = useSimulationIndex();
  const { activeDetailDate, selectAllDates, setAnalysisTime } = useSimulationStore();
  const initializedRef = useRef(false);

  // 주말/공휴일 제외한 거래일 데이터만 사용
  const tradingDayHistory = useMemo(() => {
    if (!index) return [];
    return index.history.filter((h) => isMarketOpen(h.date));
  }, [index]);

  // 인덱스 최초 로드 시에만 전체 선택 (이후 사용자 조작은 존중)
  useEffect(() => {
    if (tradingDayHistory.length > 0 && !initializedRef.current) {
      initializedRef.current = true;
      selectAllDates(tradingDayHistory.map((h) => h.date));
    }
  }, [tradingDayHistory, selectAllDates]);

  // 모든 날짜의 데이터 병렬 로딩 (선택 여부와 무관하게 통계 표시용)
  const filenames = useMemo(() => {
    return tradingDayHistory
      .map((h) => h.filename)
      .filter((f): f is string => !!f);
  }, [tradingDayHistory]);

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

  // 분석 시간대 오버라이드 훅
  const {
    availableTimes,
    selectedTime,
    overriddenData,
    isLoading: timeOverrideLoading,
  } = useAnalysisTimeOverride(activeDetailDate, detailData);

  // 오버라이드 반영된 데이터맵 (종합수익률·날짜 컴포넌트에 전달)
  const effectiveDataByDate = useMemo(() => {
    if (!overriddenData || !activeDetailDate) return dataByDate;
    return { ...dataByDate, [activeDetailDate]: overriddenData };
  }, [dataByDate, overriddenData, activeDetailDate]);

  if (indexLoading) {
    return <LoadingSpinner message="시뮬레이션 데이터 로딩 중..." />;
  }

  if (!index || tradingDayHistory.length === 0) {
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
    <div className="space-y-3 md:space-y-4">
      <PageHeader allDates={tradingDayHistory.map((h) => h.date)} />
      <SimulationModeTabs />

      {/* 종합 수익률 */}
      <SimulationSummary dataByDate={effectiveDataByDate} />

      {/* 날짜 선택 */}
      <DateSelector items={tradingDayHistory} dataByDate={effectiveDataByDate} />

      {/* 로딩 */}
      {isAnyLoading && (
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin w-5 h-5 border-2 border-accent-primary border-t-transparent rounded-full" />
          <span className="ml-2 text-sm text-text-muted">데이터 로딩 중...</span>
        </div>
      )}

      {/* 상세보기 */}
      {activeDetailDate && detailData && (
        <DetailSection
          date={activeDetailDate}
          data={effectiveDataByDate[activeDetailDate]}
          availableTimes={availableTimes}
          selectedTime={selectedTime}
          onSelectTime={(time) => setAnalysisTime(activeDetailDate, time)}
          isTimeLoading={timeOverrideLoading}
        />
      )}

      {activeDetailDate && !detailData && !isAnyLoading && (
        <p className="text-sm text-text-muted text-center py-4">
          {activeDetailDate} 데이터를 로딩할 수 없습니다.
        </p>
      )}
    </div>
  );
}

function PageHeader({ allDates }: { allDates?: string[] }) {
  const { simulationMode, resetAll } = useSimulationStore();
  const { isAdmin } = useAuthStore();
  const desc = simulationMode === 'close'
    ? '적극매수 시그널 종목의 시가 매수 → 종가 매도 수익률'
    : '적극매수 시그널 종목의 시가 매수 → 장중 최고가 매도 수익률';

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h2 className="text-lg md:text-xl font-bold">모의투자 시뮬레이션</h2>
        <p className="text-xs text-text-muted mt-0.5">{desc}</p>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {allDates && (
          <button
            onClick={() => resetAll(allDates)}
            className="px-3 py-1.5 text-xs font-medium text-text-muted hover:text-text-secondary bg-bg-secondary hover:bg-bg-primary border border-border rounded-lg transition-all whitespace-nowrap"
          >
            초기화
          </button>
        )}
        {isAdmin && <CollectionTrigger />}
      </div>
    </div>
  );
}

const MODE_TABS: { key: SimulationMode; label: string; shortLabel: string }[] = [
  { key: 'close', label: '종가 매도', shortLabel: '종가' },
  { key: 'high', label: '최고가 매도', shortLabel: '최고가' },
];

function SimulationModeTabs() {
  const { simulationMode, setSimulationMode } = useSimulationStore();

  return (
    <div className="flex gap-1 bg-bg-secondary p-1 rounded-xl border border-border">
      {MODE_TABS.map((tab) => (
        <button
          key={tab.key}
          onClick={() => setSimulationMode(tab.key)}
          className={cn(
            'flex-1 py-2 md:py-2.5 px-3 md:px-4 rounded-lg text-xs md:text-sm font-semibold transition-all text-center',
            simulationMode === tab.key
              ? 'bg-accent-primary text-white'
              : 'text-text-muted hover:text-text-secondary hover:bg-bg-primary'
          )}
        >
          <span className="hidden sm:inline">{tab.label}</span>
          <span className="sm:hidden">{tab.shortLabel}</span>
        </button>
      ))}
    </div>
  );
}

interface DetailSectionProps {
  date: string;
  data: SimulationData | undefined;
  availableTimes: AvailableTime[];
  selectedTime: string | null;
  onSelectTime: (time: string | null) => void;
  isTimeLoading: boolean;
}

function DetailSection({ date, data, availableTimes, selectedTime, onSelectTime, isTimeLoading }: DetailSectionProps) {
  const allCategories: SimulationCategory[] = ['vision', 'kis', 'combined'];
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    () => new Set(allCategories)
  );

  const allExpanded = allCategories.every((cat) => expandedCategories.has(cat));

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-secondary flex items-center gap-2">
          <span className="w-2 h-2 bg-accent-primary rounded-full" />
          {date} 상세
        </h3>
        <button
          onClick={() =>
            setExpandedCategories(allExpanded ? new Set() : new Set(allCategories))
          }
          className="px-2.5 py-1 text-xs font-medium text-text-muted hover:text-text-secondary bg-bg-secondary hover:bg-bg-primary border border-border rounded-lg transition-all"
        >
          {allExpanded ? '전체 접기' : '전체 펼치기'}
        </button>
      </div>

      <AnalysisTimeSelector
        availableTimes={availableTimes}
        selectedTime={selectedTime}
        onSelect={onSelectTime}
        isLoading={isTimeLoading}
      />

      {allCategories.map((cat) => (
        <CategorySection
          key={cat}
          category={cat}
          stocks={data?.categories[cat] || []}
          date={date}
          expanded={expandedCategories.has(cat)}
          onToggleExpand={() =>
            setExpandedCategories((prev) => {
              const next = new Set(prev);
              next.has(cat) ? next.delete(cat) : next.add(cat);
              return next;
            })
          }
        />
      ))}
    </div>
  );
}
