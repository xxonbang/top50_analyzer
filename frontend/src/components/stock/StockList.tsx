import { useRef, useEffect, useState } from 'react';
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
  const [fadeIn, setFadeIn] = useState(false);
  const prevCompact = useRef(isCompactView);

  useEffect(() => {
    if (prevCompact.current !== isCompactView) {
      setFadeIn(true);
      prevCompact.current = isCompactView;
      const t = setTimeout(() => setFadeIn(false), 200);
      return () => clearTimeout(t);
    }
  }, [isCompactView]);

  return (
    <div className={`transition-opacity duration-200 ${fadeIn ? 'opacity-0' : 'opacity-100'}`}>
      {/* Desktop Table */}
      <StockTable stocks={stocks} isCompact={isCompactView} criteriaData={criteriaData} />

      {/* Mobile Cards */}
      <div className="md:hidden">
        {stocks.map((stock) => (
          <StockCard key={stock.code} stock={stock} isCompact={isCompactView} criteria={criteriaData?.[stock.code] ?? null} />
        ))}
      </div>
    </div>
  );
}
