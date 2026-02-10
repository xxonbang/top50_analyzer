import type { SimulationStock, SimulationCategory } from '@/services/types';
import { ReturnDisplay } from './ReturnDisplay';
import { useSimulationStore, stockKey } from '@/store/simulationStore';

interface StockBadgeProps {
  stock: SimulationStock;
  category: SimulationCategory;
  date: string;
}

export function StockBadge({ stock, category, date }: StockBadgeProps) {
  const { excludedStocks, toggleStock } = useSimulationStore();
  const key = stockKey(date, category, stock.code);
  const isExcluded = excludedStocks.has(key);

  return (
    <label
      className={`
        flex items-center gap-2 px-3 py-2.5
        bg-bg-secondary border rounded-xl
        cursor-pointer select-none transition-all
        ${isExcluded
          ? 'border-border opacity-40'
          : 'border-border hover:border-accent-primary/50 hover:shadow-sm'
        }
      `}
    >
      <input
        type="checkbox"
        checked={!isExcluded}
        onChange={() => toggleStock(date, category, stock.code)}
        className="w-3.5 h-3.5 rounded accent-accent-primary flex-shrink-0"
      />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className={`text-sm font-medium truncate ${isExcluded ? 'line-through' : ''}`}>
            {stock.name}
          </span>
          <a
            href={`https://finance.naver.com/item/main.naver?code=${stock.code}`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex-shrink-0 text-text-muted hover:text-accent-primary transition-colors"
            title="네이버 금융에서 보기"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
              <polyline points="15 3 21 3 21 9"/>
              <line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
          </a>
          <span className="text-[0.65rem] text-text-muted">{stock.code}</span>
        </div>
        <div className="flex items-center gap-2 mt-0.5 text-xs text-text-muted">
          {stock.open_price !== null ? (
            <>
              <span>시가 {stock.open_price.toLocaleString()}</span>
              <span>→</span>
              <span>종가 {stock.close_price?.toLocaleString()}</span>
            </>
          ) : (
            <span>가격 미수집</span>
          )}
        </div>
      </div>

      <ReturnDisplay value={stock.return_pct} size="sm" />
    </label>
  );
}
