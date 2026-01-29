import { cn } from '@/lib/utils';
import type { MarketType } from '@/services/types';

interface MarketTabsProps {
  active: MarketType;
  counts: {
    all: number;
    kospi: number;
    kosdaq: number;
  };
  onChange: (market: MarketType) => void;
}

const tabs: { key: MarketType; label: string }[] = [
  { key: 'all', label: '전체' },
  { key: 'kospi', label: '코스피' },
  { key: 'kosdaq', label: '코스닥' },
];

export function MarketTabs({ active, counts, onChange }: MarketTabsProps) {
  return (
    <div className="flex gap-1 md:gap-2 mb-4 bg-bg-secondary p-1 md:p-1.5 rounded-xl border border-border">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={cn(
            'flex-1 py-2 md:py-3 px-2 md:px-4 rounded-lg text-xs md:text-sm font-semibold transition-all flex items-center justify-center gap-1 md:gap-2',
            active === tab.key
              ? 'bg-accent-primary text-white'
              : 'text-text-muted hover:text-text-secondary hover:bg-bg-primary'
          )}
        >
          {tab.label}
          <span
            className={cn(
              'px-1.5 md:px-2 py-0.5 rounded-full text-[0.65rem] md:text-xs',
              active === tab.key
                ? 'bg-white/30'
                : 'bg-bg-primary'
            )}
          >
            {counts[tab.key]}
          </span>
        </button>
      ))}
    </div>
  );
}
