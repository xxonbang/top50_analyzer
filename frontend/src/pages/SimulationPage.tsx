import { useEffect, useRef, useMemo, useState } from 'react';
import { useSimulationIndex, useSimulationMultipleDates } from '@/hooks/useSimulationData';
import { useSimulationStore } from '@/store/simulationStore';
import { useAuthStore } from '@/store/authStore';
import type { SimulationMode } from '@/store/simulationStore';
import { SimulationSummary, DateSelector, CategorySection, CollectionTrigger, AnalysisTimeSelector } from '@/components/simulation';
import { useAnalysisTimeOverride } from '@/hooks/useAnalysisTimeOverride';
import { LoadingSpinner, EmptyState } from '@/components/common';
import { cn } from '@/lib/utils';
import { matchStock } from '@/lib/koreanSearch';
import type { AvailableTime } from '@/hooks/useAnalysisTimeOverride';
import type { SimulationData, SimulationStock, SimulationCategory } from '@/services/types';

export function SimulationPage() {
  const { data: index, isLoading: indexLoading } = useSimulationIndex();
  const { activeDetailDate, selectAllDates, setAnalysisTime } = useSimulationStore();
  const initializedRef = useRef(false);
  const [searchQuery, setSearchQuery] = useState('');

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
    <div className="space-y-3 md:space-y-4">
      <PageHeader allDates={index.history.map((h) => h.date)} searchQuery={searchQuery} onSearchChange={setSearchQuery} />
      <SimulationModeTabs />

      {/* 종합 수익률 */}
      <SimulationSummary dataByDate={effectiveDataByDate} />

      {/* 날짜 선택 */}
      <DateSelector items={index.history} dataByDate={effectiveDataByDate} />

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
          searchQuery={searchQuery}
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

function PageHeader({ allDates, searchQuery, onSearchChange }: { allDates?: string[]; searchQuery?: string; onSearchChange?: (q: string) => void }) {
  const { simulationMode, resetAll } = useSimulationStore();
  const { isAdmin } = useAuthStore();
  const desc = simulationMode === 'close'
    ? '적극매수 시그널 종목의 시가 매수 → 종가 매도 수익률'
    : '적극매수 시그널 종목의 시가 매수 → 장중 최고가 매도 수익률';

  return (
    <div className="space-y-2">
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

      {onSearchChange && (
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none"
            viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            value={searchQuery ?? ''}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="종목 검색 (이름, 코드, 초성 예: ㅅㅅㅈㅈ)"
            className="w-full pl-9 pr-9 py-2 text-sm
              bg-bg-secondary border border-border rounded-xl
              placeholder:text-text-muted/50
              focus:outline-none focus:border-accent-primary/50 focus:ring-1 focus:ring-accent-primary/20
              transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>
      )}
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
  searchQuery: string;
}

function DetailSection({ date, data, availableTimes, selectedTime, onSelectTime, isTimeLoading, searchQuery }: DetailSectionProps) {
  // 검색 필터링된 종목 (카테고리별)
  const filteredCategories = useMemo(() => {
    const cats = data?.categories;
    if (!cats) return { vision: [], kis: [], combined: [] };

    const filter = (stocks: SimulationStock[]) =>
      searchQuery
        ? stocks.filter((s) => matchStock(searchQuery, s.name, s.code))
        : stocks;

    return {
      vision: filter(cats.vision || []),
      kis: filter(cats.kis || []),
      combined: filter(cats.combined || []),
    };
  }, [data, searchQuery]);

  const totalFiltered = filteredCategories.vision.length + filteredCategories.kis.length + filteredCategories.combined.length;
  const totalAll = (data?.categories.vision?.length || 0) + (data?.categories.kis?.length || 0) + (data?.categories.combined?.length || 0);
  const isFiltering = searchQuery.length > 0;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-text-secondary flex items-center gap-2">
        <span className="w-2 h-2 bg-accent-primary rounded-full" />
        {date} 상세
        {isFiltering && (
          <span className="text-[0.65rem] font-normal text-text-muted">
            ({totalFiltered}/{totalAll}개)
          </span>
        )}
      </h3>

      <AnalysisTimeSelector
        availableTimes={availableTimes}
        selectedTime={selectedTime}
        onSelect={onSelectTime}
        isLoading={isTimeLoading}
      />

      {(['vision', 'kis', 'combined'] as SimulationCategory[]).map((cat) => (
        <CategorySection
          key={cat}
          category={cat}
          stocks={filteredCategories[cat]}
          date={date}
        />
      ))}
    </div>
  );
}
