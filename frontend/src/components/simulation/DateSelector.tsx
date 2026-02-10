import { useMemo } from 'react';
import type { SimulationIndexItem, SimulationCategory, SimulationData } from '@/services/types';
import { useSimulationStore, stockKey } from '@/store/simulationStore';

interface DateSelectorProps {
  items: SimulationIndexItem[];
  dataByDate?: Record<string, SimulationData>;
}

function formatDateLabel(dateStr: string) {
  const d = new Date(dateStr + 'T00:00:00');
  const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
  const month = d.getMonth() + 1;
  const day = d.getDate();
  const weekday = weekdays[d.getDay()];
  return { short: `${month}/${day}`, weekday };
}

export function DateSelector({ items, dataByDate }: DateSelectorProps) {
  const { selectedDates, activeDetailDate, activeCategories, excludedStocks, toggleDate, selectAllDates, deselectAllDates, setActiveDetailDate } = useSimulationStore();

  const allDates = useMemo(() => items.map((item) => item.date), [items]);
  const allSelected = allDates.length > 0 && allDates.every((d) => selectedDates.has(d));
  const noneSelected = selectedDates.size === 0;

  // 날짜별 통계 계산 (excludedStocks, activeCategories 반영)
  const dateStats = useMemo(() => {
    const stats: Record<string, { avgReturn: number | null; includedCount: number; totalCount: number }> = {};
    items.forEach((item) => {
      const data = dataByDate?.[item.date];
      if (!data) {
        stats[item.date] = { avgReturn: null, includedCount: 0, totalCount: item.total_stocks };
        return;
      }
      let invested = 0;
      let value = 0;
      let included = 0;
      let total = 0;
      (Object.entries(data.categories) as [SimulationCategory, typeof data.categories.vision][]).forEach(
        ([cat, stocks]) => {
          stocks.forEach((s) => {
            total++;
            if (!activeCategories.has(cat)) return;
            if (excludedStocks.has(stockKey(item.date, cat, s.code))) return;
            included++;
            if (s.open_price !== null && s.close_price !== null) {
              invested += s.open_price;
              value += s.close_price;
            }
          });
        }
      );
      stats[item.date] = {
        avgReturn: invested > 0 ? (value - invested) / invested * 100 : null,
        includedCount: included,
        totalCount: total,
      };
    });
    return stats;
  }, [items, dataByDate, activeCategories, excludedStocks]);

  return (
    <div className="border border-border rounded-2xl overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-4 py-3 bg-bg-secondary/50">
        <div className="flex items-center gap-2.5">
          <svg className="w-4 h-4 text-text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <span className="font-semibold text-sm">날짜 선택</span>
          <span className="text-[0.65rem] text-text-muted bg-bg-secondary px-1.5 py-0.5 rounded-md">
            {selectedDates.size}/{items.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => selectAllDates(allDates)}
            className={`px-2 py-1 rounded-md text-[0.65rem] font-medium transition-colors
              ${allSelected
                ? 'bg-accent-primary/10 text-accent-primary'
                : 'text-text-muted hover:text-accent-primary hover:bg-accent-primary/5'
              }`}
          >
            전체선택
          </button>
          <button
            onClick={() => deselectAllDates()}
            className={`px-2 py-1 rounded-md text-[0.65rem] font-medium transition-colors
              ${noneSelected
                ? 'bg-bg-secondary text-text-muted/50 cursor-default'
                : 'text-text-muted hover:text-signal-strong-sell hover:bg-signal-strong-sell/5'
              }`}
            disabled={noneSelected}
          >
            전체해제
          </button>
        </div>
      </div>

      {/* 날짜 카드 그리드 */}
      <div className="p-3 grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-7 gap-2">
        {items.map((item) => {
          const isSelected = selectedDates.has(item.date);
          const isDetail = activeDetailDate === item.date;
          const { short, weekday } = formatDateLabel(item.date);
          const stat = dateStats[item.date];
          const avgReturn = stat?.avgReturn ?? null;

          return (
            <div key={item.date} className="relative">
              {/* 선택/해제 체크박스 - 카드 외부 좌상단 */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleDate(item.date);
                }}
                className={`
                  absolute -top-1 -left-1 z-10 w-5 h-5 rounded-md border-2
                  flex items-center justify-center transition-all
                  ${isSelected
                    ? 'bg-accent-primary border-accent-primary text-white'
                    : 'bg-white border-border/80 hover:border-accent-primary/50'
                  }
                `}
              >
                {isSelected && (
                  <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                )}
              </button>

              {/* 날짜 카드 */}
              <button
                onClick={() => {
                  if (!isSelected) toggleDate(item.date);
                  setActiveDetailDate(item.date);
                }}
                className={`
                  w-full flex flex-col items-center gap-0.5 px-2 py-3
                  rounded-xl border transition-all text-center
                  ${isDetail
                    ? 'bg-accent-primary text-white border-accent-primary shadow-md scale-[1.02]'
                    : isSelected
                      ? 'bg-accent-primary/5 text-text-primary border-accent-primary/30 hover:border-accent-primary/60'
                      : 'bg-bg-secondary/50 text-text-muted border-transparent hover:border-border hover:bg-bg-secondary'
                  }
                `}
              >
                {/* 날짜 */}
                <span className={`text-sm font-bold tabular-nums ${isDetail ? 'text-white' : ''}`}>
                  {short}
                </span>
                <span className={`text-[0.6rem] ${isDetail ? 'text-white/70' : 'text-text-muted'}`}>
                  {weekday}
                </span>

                {/* 종목수 */}
                <span className={`text-[0.6rem] mt-1 ${isDetail ? 'text-white/60' : 'text-text-muted/70'}`}>
                  {stat ? `${stat.includedCount}/${stat.totalCount}` : `${item.total_stocks}`}종목
                </span>

                {/* 수익률 */}
                {avgReturn !== null ? (
                  <span className={`text-xs font-bold tabular-nums
                    ${isDetail
                      ? 'text-white'
                      : avgReturn > 0 ? 'text-signal-strong-buy' : avgReturn < 0 ? 'text-signal-strong-sell' : 'text-text-muted'
                    }`}
                  >
                    {avgReturn > 0 ? '+' : ''}{avgReturn.toFixed(2)}%
                  </span>
                ) : (
                  <span className={`text-xs ${isDetail ? 'text-white/40' : 'text-text-muted/40'}`}>
                    -
                  </span>
                )}
              </button>
            </div>
          );
        })}

        {items.length === 0 && (
          <p className="col-span-full text-sm text-text-muted text-center py-4">
            수집된 데이터가 없습니다.
          </p>
        )}
      </div>
    </div>
  );
}
