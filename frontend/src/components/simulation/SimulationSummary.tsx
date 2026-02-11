import { useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { SimulationData, SimulationCategory } from '@/services/types';
import { ReturnDisplay } from './ReturnDisplay';
import { useSimulationStore, stockKey } from '@/store/simulationStore';

interface SimulationSummaryProps {
  dataByDate: Record<string, SimulationData>;
}

const CATEGORY_LABELS: Record<SimulationCategory, string> = {
  vision: 'Vision',
  kis: 'KIS',
  combined: 'Combined',
};

const CATEGORY_ICONS: Record<SimulationCategory, string> = {
  vision: '\uD83E\uDD16',
  kis: '\uD83D\uDCCA',
  combined: '\uD83D\uDD04',
};

export function SimulationSummary({ dataByDate }: SimulationSummaryProps) {
  const { selectedDates, activeCategories, excludedStocks, simulationMode } = useSimulationStore();
  const queryClient = useQueryClient();

  // 오늘 날짜의 마지막 수집 시각
  const latestCollectedAt = useMemo(() => {
    const now = new Date();
    const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    const todayData = dataByDate[todayStr];
    if (!todayData?.collected_at) return null;
    try {
      const d = new Date(todayData.collected_at);
      return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    } catch {
      return null;
    }
  }, [dataByDate]);

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['simulation'] });
  };

  const stats = useMemo(() => {
    let totalInvested = 0;
    let totalValue = 0;
    let totalStocks = 0;
    let pricedStocks = 0;
    let wins = 0;
    let datesWithData = 0;

    const catInvested: Record<SimulationCategory, number> = { vision: 0, kis: 0, combined: 0 };
    const catValue: Record<SimulationCategory, number> = { vision: 0, kis: 0, combined: 0 };
    const catCount: Record<SimulationCategory, number> = { vision: 0, kis: 0, combined: 0 };

    selectedDates.forEach((date) => {
      const data = dataByDate[date];
      if (!data) return;

      let dateHasData = false;

      (Object.entries(data.categories) as [SimulationCategory, typeof data.categories.vision][]).forEach(
        ([cat, stocks]) => {
          if (!activeCategories.has(cat)) return;
          stocks.forEach((stock) => {
            if (excludedStocks.has(stockKey(date, cat, stock.code))) return;
            totalStocks++;
            const sellPrice = simulationMode === 'high' ? stock.high_price : stock.close_price;
            const returnPct = simulationMode === 'high' ? stock.high_return_pct : stock.return_pct;
            if (stock.open_price != null && stock.open_price > 0 && sellPrice != null && sellPrice > 0) {
              pricedStocks++;
              totalInvested += stock.open_price;
              totalValue += sellPrice;
              catInvested[cat] += stock.open_price;
              catValue[cat] += sellPrice;
              catCount[cat]++;
              dateHasData = true;
              if (returnPct !== null && returnPct !== undefined && returnPct > 0) wins++;
            }
          });
        }
      );

      if (dateHasData) datesWithData++;
    });

    // 총 투자금 대비 총 수익금 비율
    const avg = totalInvested > 0
      ? (totalValue - totalInvested) / totalInvested * 100
      : null;

    const catAvg: Record<SimulationCategory, number | null> = {
      vision: null, kis: null, combined: null,
    };
    for (const cat of ['vision', 'kis', 'combined'] as SimulationCategory[]) {
      catAvg[cat] = catInvested[cat] > 0
        ? (catValue[cat] - catInvested[cat]) / catInvested[cat] * 100
        : null;
    }

    const losses = pricedStocks - wins;
    const winRate = pricedStocks > 0 ? (wins / pricedStocks) * 100 : null;

    return { avg, catAvg, catCount, totalStocks, pricedStocks, selectedDays: datesWithData, winRate, wins, losses };
  }, [selectedDates, dataByDate, activeCategories, excludedStocks, simulationMode]);

  return (
    <div className="border border-border rounded-2xl p-4 md:p-6 bg-bg-secondary/30">
      {/* 메인 수익률 - 모바일: 세로 정렬 */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4 md:mb-5">
        <div className="flex items-center justify-between md:block">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-text-primary">종합 수익률</h3>
              <button
                onClick={handleRefresh}
                className="text-text-muted hover:text-accent-primary transition-colors p-1 -m-1"
                title="데이터 새로고침"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
            <div className="flex items-center gap-2 text-xs md:text-sm text-text-muted mt-0.5">
              <span>{stats.selectedDays}일</span>
              <span className="text-border">|</span>
              <span>{stats.pricedStocks}/{stats.totalStocks}종목</span>
              {latestCollectedAt && (
                <>
                  <span className="text-border">|</span>
                  <span>{latestCollectedAt} 수집</span>
                </>
              )}
            </div>
          </div>
          {/* 모바일에서 수익률을 헤더 옆에 표시 */}
          <div className="md:hidden text-right">
            <ReturnDisplay value={stats.avg} size="lg" />
          </div>
        </div>

        <div className="hidden md:block text-right">
          <ReturnDisplay value={stats.avg} size="lg" />
          {stats.winRate !== null && (
            <div className="text-sm text-text-muted mt-0.5">
              승률 <span className="font-semibold text-text-secondary">{stats.winRate.toFixed(0)}%</span>
              <span className="text-text-muted/60 ml-1">({stats.wins}승 {stats.losses}패)</span>
            </div>
          )}
        </div>
      </div>

      {/* 모바일 승률 표시 */}
      {stats.winRate !== null && (
        <div className="md:hidden text-xs text-text-muted mb-3 flex items-center gap-2">
          <span>승률 <span className="font-semibold text-text-secondary">{stats.winRate.toFixed(0)}%</span></span>
          <span className="text-text-muted/60">({stats.wins}승 {stats.losses}패)</span>
        </div>
      )}

      {/* 카테고리별 수익률 */}
      <div className="grid grid-cols-3 gap-2 md:gap-3">
        {(['vision', 'kis', 'combined'] as SimulationCategory[]).map((cat) => {
          const isActive = activeCategories.has(cat);
          const avg = isActive ? stats.catAvg[cat] : null;
          const count = stats.catCount[cat];

          return (
            <div
              key={cat}
              className={`rounded-xl px-2 py-2.5 md:p-3 text-center border transition-opacity
                ${isActive ? 'bg-bg-secondary border-border/50' : 'bg-bg-secondary/30 border-transparent opacity-40'}
              `}
            >
              <div className="text-xs md:text-sm text-text-muted mb-1 md:mb-1.5 truncate">
                <span className="mr-0.5">{CATEGORY_ICONS[cat]}</span>
                {CATEGORY_LABELS[cat]}
              </div>
              <div className="mb-0.5 md:mb-1">
                <ReturnDisplay value={avg} size="md" />
              </div>
              <div className="text-[0.65rem] md:text-xs text-text-muted">
                {count}건
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
