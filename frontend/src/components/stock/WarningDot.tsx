import type { StockCriteria } from '@/services/types';

const ALERTS = [
  { key: 'short_selling_alert', color: 'bg-red-500' },
  { key: 'overheating_alert', color: 'bg-orange-500' },
  { key: 'reverse_ma_alert', color: 'bg-violet-500' },
] as const;

export function WarningDot({ criteria, className }: {
  criteria: StockCriteria | null | undefined;
  className?: string;
}) {
  const active = ALERTS.filter(
    (a) => (criteria?.[a.key as keyof StockCriteria] as { met?: boolean } | undefined)?.met
  );
  if (active.length === 0) return null;

  const pos = className || '-top-1 -right-1';

  return (
    <span className={`absolute flex items-center gap-0.5 ${pos}`}>
      {active.map((a) => (
        <span key={a.key} className="relative flex h-3 w-3">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${a.color} opacity-75`} />
          <span className={`relative inline-flex rounded-full h-3 w-3 ${a.color}`} />
        </span>
      ))}
    </span>
  );
}
