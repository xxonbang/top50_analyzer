import { useState } from 'react';
import { useMarketStatus, useFearGreedIndex } from '@/hooks/useMarketStatus';
import { useAuthStore } from '@/store/authStore';
import type { MarketIndexStatus, FearGreedData } from '@/services/types';

const STATUS_STYLES = {
  bullish: 'from-emerald-500/10 to-emerald-600/5 border-emerald-300/60 text-emerald-800',
  bearish: 'from-red-500/10 to-red-600/5 border-red-300/60 text-red-800',
  mixed: 'from-gray-400/10 to-gray-500/5 border-gray-300/60 text-gray-700',
  unknown: '',
} as const;

const STATUS_LABELS = {
  bullish: '정배열',
  bearish: '역배열',
  mixed: '혼조',
  unknown: '',
} as const;

const STATUS_BADGE = {
  bullish: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  bearish: 'bg-red-100 text-red-700 border-red-300',
  mixed: 'bg-gray-100 text-gray-600 border-gray-300',
  unknown: '',
} as const;

function IndexCard({ data, label, icon }: { data: MarketIndexStatus; label: string; icon: string }) {
  const [open, setOpen] = useState(false);

  if (data.status === 'unknown') return null;

  const style = STATUS_STYLES[data.status];
  const badge = STATUS_BADGE[data.status];
  const statusLabel = STATUS_LABELS[data.status];

  return (
    <div className={`bg-gradient-to-r ${style} border rounded-lg overflow-hidden`}>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 cursor-pointer"
      >
        <span className="text-base flex-shrink-0">{icon}</span>
        <span className="font-semibold text-xs sm:text-sm whitespace-nowrap">{label} 지수 이동평균선</span>
        <span className={`text-[10px] sm:text-xs px-1.5 py-0.5 rounded border font-medium flex-shrink-0 ${badge}`}>
          {statusLabel}
        </span>
        <span className="ml-auto font-bold text-sm sm:text-base tabular-nums flex-shrink-0">
          {data.current?.toFixed(2)}
        </span>
        <svg
          className={`w-4 h-4 flex-shrink-0 opacity-50 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div className={`overflow-hidden transition-all duration-200 ${open ? 'max-h-40' : 'max-h-0'}`}>
        <div className="px-3 pb-2.5 grid grid-cols-3 sm:grid-cols-6 gap-x-3 gap-y-1.5 text-xs sm:text-sm">
          <div className="flex flex-col">
            <span className="text-[10px] uppercase tracking-wider opacity-40 font-medium">현재</span>
            <span className="tabular-nums font-bold">{data.current?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          </div>
          {Object.entries(data.ma_values).map(([k, v]) => {
            const diff = data.current ? v - data.current : 0;
            const colorClass = diff > 0 ? 'text-emerald-600' : diff < 0 ? 'text-red-500' : '';
            return (
              <div key={k} className="flex flex-col">
                <span className="text-[10px] uppercase tracking-wider opacity-40 font-medium">{k}</span>
                <span className={`tabular-nums font-semibold ${colorClass}`}>
                  {v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

const FEAR_GREED_STYLES: Record<string, { bg: string; text: string; badge: string }> = {
  'extreme fear': { bg: 'from-red-600/15 to-red-700/5 border-red-400/60', text: 'text-red-800', badge: 'bg-red-100 text-red-700 border-red-300' },
  'fear': { bg: 'from-orange-500/10 to-orange-600/5 border-orange-300/60', text: 'text-orange-800', badge: 'bg-orange-100 text-orange-700 border-orange-300' },
  'neutral': { bg: 'from-gray-400/10 to-gray-500/5 border-gray-300/60', text: 'text-gray-700', badge: 'bg-gray-100 text-gray-600 border-gray-300' },
  'greed': { bg: 'from-green-500/10 to-green-600/5 border-green-300/60', text: 'text-green-800', badge: 'bg-green-100 text-green-700 border-green-300' },
  'extreme greed': { bg: 'from-emerald-600/15 to-emerald-700/5 border-emerald-400/60', text: 'text-emerald-800', badge: 'bg-emerald-100 text-emerald-700 border-emerald-300' },
};

const FEAR_GREED_LABELS: Record<string, string> = {
  'extreme fear': '극단적 공포',
  'fear': '공포',
  'neutral': '중립',
  'greed': '탐욕',
  'extreme greed': '극단적 탐욕',
};

function FearGreedCard({ data }: { data: FearGreedData }) {
  const [open, setOpen] = useState(false);

  const style = FEAR_GREED_STYLES[data.rating] ?? FEAR_GREED_STYLES['neutral']!;
  const label = FEAR_GREED_LABELS[data.rating] ?? data.rating;

  // 게이지 퍼센트 (0~100)
  const pct = Math.max(0, Math.min(100, data.score));

  return (
    <div className={`bg-gradient-to-r ${style.bg} ${style.text} border rounded-lg overflow-hidden`}>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 cursor-pointer"
      >
        <span className="text-base flex-shrink-0">🎭</span>
        <span className="font-semibold text-xs sm:text-sm whitespace-nowrap">Fear & Greed</span>
        <span className={`text-[10px] sm:text-xs px-1.5 py-0.5 rounded border font-medium flex-shrink-0 ${style.badge}`}>
          {label}
        </span>
        {/* 미니 게이지 바 */}
        <div className="flex-1 mx-1 h-2 bg-black/10 rounded-full overflow-hidden min-w-[40px]">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${pct}%`,
              background: `linear-gradient(90deg, #dc2626 0%, #f97316 25%, #6b7280 50%, #22c55e 75%, #059669 100%)`,
              backgroundSize: '100vw',
            }}
          />
        </div>
        <span className="ml-auto font-bold text-sm sm:text-base tabular-nums flex-shrink-0">
          {data.score.toFixed(0)}
        </span>
        <svg
          className={`w-4 h-4 flex-shrink-0 opacity-50 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div className={`overflow-hidden transition-all duration-200 ${open ? 'max-h-24' : 'max-h-0'}`}>
        <div className="px-3 pb-2.5 flex flex-wrap gap-x-4 gap-y-0.5 text-xs sm:text-sm">
          <span><span className="font-semibold">현재</span> <span className="tabular-nums">{data.score.toFixed(1)}</span></span>
          <span className="opacity-75"><span className="font-medium">전일</span> <span className="tabular-nums">{data.previous_close.toFixed(1)}</span></span>
          <span className="opacity-75"><span className="font-medium">1주전</span> <span className="tabular-nums">{data.previous_1_week.toFixed(1)}</span></span>
          <span className="opacity-75"><span className="font-medium">1개월전</span> <span className="tabular-nums">{data.previous_1_month.toFixed(1)}</span></span>
          <span className="opacity-75"><span className="font-medium">1년전</span> <span className="tabular-nums">{data.previous_1_year.toFixed(1)}</span></span>
        </div>
      </div>
    </div>
  );
}

export function KosdaqStatusBanner() {
  const { isAdmin } = useAuthStore();
  const { data: marketStatus } = useMarketStatus();
  const { data: fearGreed } = useFearGreedIndex();

  if (!isAdmin) return null;

  const hasKospi = marketStatus?.kospi?.status && marketStatus.kospi.status !== 'unknown';
  const hasKosdaq = marketStatus?.kosdaq?.status && marketStatus.kosdaq.status !== 'unknown';
  const hasFearGreed = fearGreed && typeof fearGreed.score === 'number';

  if (!hasKospi && !hasKosdaq && !hasFearGreed) return null;

  return (
    <div className="flex flex-col gap-2 mb-3">
      {hasFearGreed && <FearGreedCard data={fearGreed} />}
      {hasKospi && <IndexCard data={marketStatus!.kospi} label="코스피" icon="📈" />}
      {hasKosdaq && <IndexCard data={marketStatus!.kosdaq} label="코스닥" icon="📊" />}
    </div>
  );
}
