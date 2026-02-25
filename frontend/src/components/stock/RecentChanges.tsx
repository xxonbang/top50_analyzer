import type { RecentChange } from '@/services/types';

/** 최근 N일 등락률 표시 (날짜: 최신→과거 순으로 입력, 과거→최신 순으로 표시) */
export function RecentChanges({ changes }: { changes?: RecentChange[] }) {
  if (!changes || changes.length === 0) return null;

  // 과거→최신 순으로 뒤집기
  const sorted = [...changes].reverse();

  return (
    <div className="flex items-center gap-0.5 md:gap-1">
      <span className="text-[0.6rem] md:text-[0.65rem] text-text-muted mr-0.5 flex-shrink-0">등락</span>
      {sorted.map((item) => {
        const rate = item.change_rate ?? 0;
        const color = rate > 0 ? 'text-red-500' : rate < 0 ? 'text-blue-500' : 'text-text-muted';
        const bg = rate > 0 ? 'bg-red-50' : rate < 0 ? 'bg-blue-50' : 'bg-gray-50';
        const sign = rate > 0 ? '+' : '';
        // 날짜: YYYYMMDD → MM/DD
        const dateLabel = item.date ? `${item.date.slice(4, 6)}/${item.date.slice(6, 8)}` : '';
        return (
          <div
            key={item.date}
            className={`flex flex-col items-center px-1 py-0.5 rounded ${bg}`}
            title={`${dateLabel}: ${sign}${rate.toFixed(2)}%`}
          >
            <span className={`text-[0.55rem] md:text-[0.6rem] font-medium leading-tight ${color}`}>
              {sign}{rate.toFixed(1)}
            </span>
            <span className="text-[0.45rem] md:text-[0.5rem] text-text-muted leading-tight">
              {dateLabel}
            </span>
          </div>
        );
      })}
    </div>
  );
}
