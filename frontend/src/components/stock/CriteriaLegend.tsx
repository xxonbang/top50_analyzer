import { cn } from '@/lib/utils';

interface CriteriaLegendProps {
  isAdmin: boolean;
  hasCriteriaData: boolean;
}

const LEGEND_ITEMS = [
  { dotColor: 'bg-red-500', label: '전고점 돌파' },
  { dotColor: 'bg-orange-500', label: '끼 보유' },
  { dotColor: 'bg-yellow-400', label: '저항선 돌파' },
  { dotColor: 'bg-teal-500', label: '정배열' },
  { dotColor: 'bg-blue-500', label: '외국인/기관 수급' },
  { dotColor: 'bg-violet-500', label: '프로그램 매매' },
  { dotColor: 'bg-fuchsia-500', label: '거래대금 TOP30' },
];

export function CriteriaLegend({ isAdmin, hasCriteriaData }: CriteriaLegendProps) {
  if (!isAdmin || !hasCriteriaData) return null;

  return (
    <div className="bg-bg-primary/40 rounded-lg p-2 sm:p-3 mb-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-[10px] sm:text-xs font-semibold text-text-secondary mr-1">선정 기준:</span>
        {LEGEND_ITEMS.map((item) => (
          <span key={item.label} className="inline-flex items-center gap-1">
            <span className={cn('inline-block w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full', item.dotColor)} />
            <span className="text-[10px] sm:text-xs text-text-muted">{item.label}</span>
          </span>
        ))}
        <span className="inline-flex items-center gap-1">
          <span className="inline-block w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full bg-yellow-400/30 ring-1 ring-yellow-400" />
          <span className="text-[10px] sm:text-xs text-text-muted">전체 충족</span>
        </span>
      </div>
    </div>
  );
}
