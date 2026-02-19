import { StockTable } from './StockTable';
import { StockCard } from './StockCard';
import { useUIStore } from '@/store/uiStore';
import type { StockResult, StockCriteria } from '@/services/types';

interface StockListProps {
  stocks: StockResult[];
  criteriaData?: Record<string, StockCriteria> | null;
}

export function StockList({ stocks, criteriaData }: StockListProps) {
  const { isCompactView } = useUIStore();

  return (
    <>
      {/* Desktop Table */}
      <StockTable stocks={stocks} isCompact={isCompactView} criteriaData={criteriaData} />

      {/* Mobile Cards */}
      <div className="md:hidden">
        {stocks.map((stock) => (
          <StockCard key={stock.code} stock={stock} isCompact={isCompactView} criteria={criteriaData?.[stock.code] ?? null} />
        ))}
      </div>
    </>
  );
}
