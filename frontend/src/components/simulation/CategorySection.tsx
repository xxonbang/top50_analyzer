import { useMemo, useState } from 'react';
import type { SimulationStock, SimulationCategory } from '@/services/types';
import { StockBadge } from './StockBadge';
import { ReturnDisplay } from './ReturnDisplay';
import { useSimulationStore, stockKey } from '@/store/simulationStore';

const CATEGORY_LABELS: Record<SimulationCategory, string> = {
  vision: 'Vision AI 적극매수',
  kis: 'KIS API 적극매수',
  combined: 'Combined 완전일치',
};

const CATEGORY_ICONS: Record<SimulationCategory, string> = {
  vision: '\uD83E\uDD16',
  kis: '\uD83D\uDCCA',
  combined: '\uD83D\uDD04',
};

interface CategorySectionProps {
  category: SimulationCategory;
  stocks: SimulationStock[];
  date: string;
}

export function CategorySection({ category, stocks, date }: CategorySectionProps) {
  const { activeCategories, toggleCategory, excludedStocks, excludeAllStocks, includeAllStocks, simulationMode } = useSimulationStore();
  const isActive = activeCategories.has(category);
  const [expanded, setExpanded] = useState(true);

  const codes = useMemo(() => stocks.map((s) => s.code), [stocks]);

  const allExcluded = useMemo(
    () => codes.length > 0 && codes.every((code) => excludedStocks.has(stockKey(date, category, code))),
    [codes, excludedStocks, category, date]
  );

  const avgReturn = useMemo(() => {
    const included = stocks.filter((s) => {
      if (excludedStocks.has(stockKey(date, category, s.code))) return false;
      const sellPrice = simulationMode === 'high' ? s.high_price : s.close_price;
      return s.open_price != null && s.open_price > 0 && sellPrice != null && sellPrice > 0;
    });
    if (included.length === 0) return null;
    const invested = included.reduce((sum, s) => sum + s.open_price!, 0);
    const value = included.reduce((sum, s) => {
      const sellPrice = simulationMode === 'high' ? s.high_price! : s.close_price!;
      return sum + sellPrice;
    }, 0);
    return invested > 0 ? (value - invested) / invested * 100 : null;
  }, [stocks, excludedStocks, category, date, simulationMode]);

  const includedCount = stocks.filter(
    (s) => !excludedStocks.has(stockKey(date, category, s.code))
  ).length;

  if (stocks.length === 0) return null;

  return (
    <div className={`border rounded-2xl overflow-hidden transition-opacity ${isActive ? 'border-border' : 'border-border/50 opacity-50'}`}>
      {/* 헤더 */}
      <div className="flex items-center justify-between px-4 py-3 bg-bg-secondary/50">
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={isActive}
              onChange={() => toggleCategory(category)}
              className="w-4 h-4 rounded accent-accent-primary"
            />
            <span className="text-base">{CATEGORY_ICONS[category]}</span>
            <span className="font-semibold text-sm">{CATEGORY_LABELS[category]}</span>
            <span className="text-xs text-text-muted">
              {includedCount}/{stocks.length}
            </span>
          </label>
        </div>

        <div className="flex items-center gap-3">
          <ReturnDisplay value={isActive ? avgReturn : null} size="md" />
          <button
            onClick={() => allExcluded ? includeAllStocks(date, category, codes) : excludeAllStocks(date, category, codes)}
            className="text-[0.65rem] text-text-muted hover:text-accent-primary transition-colors"
          >
            {allExcluded ? '전체선택' : '전체해제'}
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 text-text-muted hover:text-text-secondary transition-colors"
          >
            <svg
              className={`w-4 h-4 transition-transform ${expanded ? '' : '-rotate-90'}`}
              viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
        </div>
      </div>

      {/* 종목 그리드 */}
      {isActive && expanded && (
        <div className="p-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
          {stocks.map((stock) => (
            <StockBadge key={stock.code} stock={stock} category={category} date={date} />
          ))}
        </div>
      )}
    </div>
  );
}
