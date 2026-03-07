import type { SimulationStock, SimulationCategory } from '@/services/types';
import { ReturnDisplay } from './ReturnDisplay';
import { useSimulationStore, stockKey } from '@/store/simulationStore';

interface StockBadgeProps {
  stock: SimulationStock;
  category: SimulationCategory;
  date: string;
  isExpanded: boolean;
  onToggle: () => void;
}

export function StockBadge({ stock, category, date, isExpanded, onToggle }: StockBadgeProps) {
  const { excludedStocks, toggleStock, simulationMode } = useSimulationStore();
  const key = stockKey(date, category, stock.code);
  const isExcluded = excludedStocks.has(key);
  const isHighMode = simulationMode === 'high';

  const sellLabel = isHighMode ? '고가' : '종가';
  const sellPrice = isHighMode ? stock.high_price : stock.close_price;

  return (
    <div
      className={`
        bg-bg-secondary border rounded-xl transition-all
        ${isExcluded
          ? 'border-border opacity-40'
          : 'border-border hover:border-accent-primary/50 hover:shadow-sm'
        }
      `}
    >
      <label
        className="flex items-center gap-1.5 md:gap-2 px-2.5 md:px-3 py-2 md:py-2.5 cursor-pointer select-none"
      >
        <input
          type="checkbox"
          checked={!isExcluded}
          onChange={() => toggleStock(date, category, stock.code)}
          className="w-3.5 h-3.5 rounded accent-accent-primary flex-shrink-0"
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1">
            <span className={`text-xs md:text-sm font-medium truncate ${isExcluded ? 'line-through' : ''}`}>
              {stock.name}
            </span>
            <a
              href={`https://m.stock.naver.com/domestic/stock/${stock.code}/total`}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="flex-shrink-0 text-text-muted hover:text-accent-primary transition-colors"
              title="네이버 금융에서 보기"
            >
              <svg className="w-3 h-3 md:w-3.5 md:h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
                <polyline points="15 3 21 3 21 9"/>
                <line x1="10" y1="14" x2="21" y2="3"/>
              </svg>
            </a>
            <span className="text-[0.75rem] md:text-xs text-text-muted">{stock.code}</span>
          </div>
          <div className="flex items-center gap-1 md:gap-2 mt-0.5 text-[0.75rem] md:text-xs text-text-muted tabular-nums">
            {stock.open_price !== null ? (
              sellPrice !== null && sellPrice !== undefined ? (
                <>
                  <span>시가 {stock.open_price.toLocaleString()}</span>
                  <span>&rarr;</span>
                  <span>{sellLabel} {sellPrice.toLocaleString()}</span>
                </>
              ) : (
                <>
                  <span>시가 {stock.open_price.toLocaleString()}</span>
                  <span className="text-text-muted/60">{sellLabel} 미수집</span>
                </>
              )
            ) : (
              <span>가격 미수집</span>
            )}
          </div>
        </div>

        <ReturnDisplay value={isHighMode ? stock.high_return_pct : stock.return_pct} size="sm" />

        <button
          type="button"
          onClick={(e) => { e.preventDefault(); onToggle(); }}
          className="p-0.5 text-text-muted hover:text-text-secondary transition-colors flex-shrink-0"
        >
          <svg
            className={`w-3.5 h-3.5 transition-transform duration-200 ${isExpanded ? '' : '-rotate-90'}`}
            viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      </label>

      {/* 상세 정보 */}
      <div className={`overflow-hidden transition-all duration-300 ease-in-out ${isExpanded ? 'max-h-[200px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="px-2.5 md:px-3 pb-2 md:pb-2.5 pt-0 text-[0.75rem] md:text-xs text-text-muted tabular-nums">
          <div className="border-t border-border/50 pt-1.5">
            <div className="flex items-center gap-2 px-1.5 py-0.5 rounded">
              <span className="w-7 text-text-muted/70">시장</span>
              <span className="text-text-secondary">{stock.market || '-'}</span>
            </div>
            <div className="flex items-center gap-2 px-1.5 py-0.5 rounded bg-black/[0.03]">
              <span className="w-7 text-text-muted/70">시가</span>
              <span className="text-text-secondary">{stock.open_price !== null ? stock.open_price.toLocaleString() : '-'}</span>
            </div>
            <div className="flex items-center gap-2 px-1.5 py-0.5 rounded">
              <span className="w-7 text-text-muted/70">종가</span>
              <span className="text-text-secondary">{stock.close_price !== null ? stock.close_price.toLocaleString() : '-'}</span>
              {stock.return_pct !== null && <ReturnDisplay value={stock.return_pct} size="sm" />}
            </div>
            <div className="flex items-center gap-2 px-1.5 py-0.5 rounded bg-black/[0.03]">
              <span className="w-7 text-text-muted/70">고가</span>
              <span className="text-text-secondary">{stock.high_price !== null ? stock.high_price.toLocaleString() : '-'}</span>
              {stock.high_return_pct !== null && <ReturnDisplay value={stock.high_return_pct} size="sm" />}
              {stock.high_price_time && <span className="text-text-muted/50">{stock.high_price_time}</span>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
