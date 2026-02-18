import { useState } from 'react';
import type { StockCriteria, CriterionResult } from '@/services/types';
import { cn } from '@/lib/utils';

const CRITERIA_CONFIG = [
  { key: 'high_breakout', dotColor: 'bg-red-500', badgeBg: 'bg-red-100', badgeText: 'text-red-700', label: '전고점', fullLabel: '전고점 돌파' },
  { key: 'momentum_history', dotColor: 'bg-orange-500', badgeBg: 'bg-orange-100', badgeText: 'text-orange-700', label: '끼', fullLabel: '끼 보유' },
  { key: 'resistance_breakout', dotColor: 'bg-yellow-400', badgeBg: 'bg-yellow-100', badgeText: 'text-yellow-700', label: '저항선', fullLabel: '저항선 돌파' },
  { key: 'ma_alignment', dotColor: 'bg-teal-500', badgeBg: 'bg-teal-100', badgeText: 'text-teal-700', label: '정배열', fullLabel: '이동평균선 정배열' },
  { key: 'supply_demand', dotColor: 'bg-blue-500', badgeBg: 'bg-blue-100', badgeText: 'text-blue-700', label: '수급', fullLabel: '외국인/기관 수급' },
  { key: 'program_trading', dotColor: 'bg-violet-500', badgeBg: 'bg-violet-100', badgeText: 'text-violet-700', label: '프로그램', fullLabel: '프로그램 매매' },
  { key: 'top30_trading_value', dotColor: 'bg-fuchsia-500', badgeBg: 'bg-fuchsia-100', badgeText: 'text-fuchsia-700', label: 'TOP30', fullLabel: '거래대금 TOP30' },
] as const;

interface CriteriaIndicatorProps {
  criteria: StockCriteria;
  isCompact?: boolean;
}

export function CriteriaIndicator({ criteria, isCompact = false }: CriteriaIndicatorProps) {
  const [activePopup, setActivePopup] = useState<string | null>(null);

  const metCriteria = CRITERIA_CONFIG.filter(
    (c) => (criteria[c.key as keyof StockCriteria] as CriterionResult)?.met
  );

  if (metCriteria.length === 0) return null;

  const handleClick = (e: React.MouseEvent, key: string) => {
    if (isCompact) return;
    e.preventDefault();
    e.stopPropagation();
    setActivePopup(activePopup === key ? null : key);
  };

  const handleClose = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setActivePopup(null);
  };

  return (
    <div className="relative flex flex-wrap items-center gap-1 sm:gap-1.5 my-1">
      {metCriteria.map((config) => {
        const result = criteria[config.key as keyof StockCriteria] as CriterionResult;
        const is52w = config.key === 'high_breakout' && result.is_52w_high;

        return (
          <div key={config.key} className="relative">
            {/* Compact: 작은 도트만 */}
            {isCompact ? (
              <span className={cn('inline-block w-1.5 h-1.5 rounded-full', config.dotColor)} />
            ) : (
              <>
                {/* 모바일: 도트 */}
                <button
                  onClick={(e) => handleClick(e, config.key)}
                  className={cn(
                    'sm:hidden inline-block w-2.5 h-2.5 rounded-full',
                    config.dotColor,
                  )}
                />
                {/* PC: 뱃지 */}
                <button
                  onClick={(e) => handleClick(e, config.key)}
                  className={cn(
                    'hidden sm:inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-medium leading-none',
                    config.badgeBg, config.badgeText,
                  )}
                >
                  <span className={cn('inline-block w-1.5 h-1.5 rounded-full', config.dotColor)} />
                  {is52w ? '52주 신고가' : config.label}
                </button>
              </>
            )}

            {/* 팝업 */}
            {!isCompact && activePopup === config.key && (
              <div
                className="absolute top-full left-0 mt-1 z-50 w-64 sm:w-72 bg-white border border-border rounded-lg shadow-lg p-3"
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); }}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <span className={cn('inline-block w-2.5 h-2.5 rounded-full', config.dotColor)} />
                    <span className="text-xs font-semibold text-text-primary">{config.fullLabel}</span>
                  </div>
                  <button
                    onClick={handleClose}
                    className="text-text-muted hover:text-text-primary text-xs"
                  >
                    X
                  </button>
                </div>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  {result.reason || '근거 없음'}
                </p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
