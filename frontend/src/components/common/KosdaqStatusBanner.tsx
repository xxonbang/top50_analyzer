import { useState, useRef, useEffect } from 'react';
import { useMarketStatus, useFearGreedIndex, useVixIndex } from '@/hooks/useMarketStatus';
import { useAuthStore } from '@/store/authStore';
import type { MarketIndexStatus, FearGreedData, VixData } from '@/services/types';

function LegendPopup({ items, onClose }: { items: { label: string; range: string; color: string }[]; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [onClose]);

  return (
    <div ref={ref} className="absolute z-50 top-full mt-1 left-0 sm:left-auto sm:right-0 bg-white border border-gray-200 rounded-lg shadow-lg p-2.5 min-w-[160px] text-xs">
      {items.map(({ label, range, color }) => (
        <div key={label} className="flex items-center gap-2 py-0.5">
          <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${color}`} />
          <span className="font-medium">{label}</span>
          <span className="ml-auto text-gray-400 tabular-nums">{range}</span>
        </div>
      ))}
    </div>
  );
}

function HelpButton({ onClick }: { onClick: (e: React.MouseEvent) => void }) {
  return (
    <span
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={e => { if (e.key === 'Enter') onClick(e as unknown as React.MouseEvent); }}
      className="inline-flex items-center justify-center w-4 h-4 rounded-full border border-current opacity-40 hover:opacity-70 cursor-pointer text-[9px] font-bold leading-none flex-shrink-0 transition-opacity"
    >
      ?
    </span>
  );
}

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
        <div className="px-3 pb-2.5 grid grid-cols-3 gap-x-3 gap-y-1.5 sm:flex sm:justify-between text-xs sm:text-sm">
          <div className="flex flex-col">
            <span className="text-[10px] uppercase tracking-wider opacity-40 font-medium">현재</span>
            <span className="tabular-nums font-bold">{data.current?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          </div>
          {Object.entries(data.ma_values).map(([k, v]) => {
            const diff = data.current ? v - data.current : 0;
            const colorClass = diff > 0 ? 'text-red-500' : diff < 0 ? 'text-emerald-600' : '';
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

const FEAR_GREED_LEGEND = [
  { label: '극단적 공포', range: '0–24', color: 'bg-red-500' },
  { label: '공포', range: '25–44', color: 'bg-orange-400' },
  { label: '중립', range: '45–55', color: 'bg-gray-400' },
  { label: '탐욕', range: '56–75', color: 'bg-green-500' },
  { label: '극단적 탐욕', range: '76–100', color: 'bg-emerald-600' },
];

function FearGreedCard({ data }: { data: FearGreedData }) {
  const [open, setOpen] = useState(false);
  const [showLegend, setShowLegend] = useState(false);

  const style = FEAR_GREED_STYLES[data.rating] ?? FEAR_GREED_STYLES['neutral']!;
  const label = FEAR_GREED_LABELS[data.rating] ?? data.rating;

  const pct = Math.max(0, Math.min(100, data.score));

  return (
    <div className={`bg-gradient-to-r ${style.bg} ${style.text} border rounded-lg relative`}>
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
        <HelpButton onClick={e => { e.stopPropagation(); setShowLegend(v => !v); }} />
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
      <div className={`overflow-hidden transition-all duration-200 ${open ? 'max-h-40' : 'max-h-0'}`}>
        <div className="px-3 pb-2.5 grid grid-cols-3 gap-x-3 gap-y-1.5 sm:flex sm:justify-between text-xs sm:text-sm">
          {[
            { label: '현재', value: data.score },
            { label: '전일', value: data.previous_close },
            { label: '1주전', value: data.previous_1_week },
            { label: '1개월전', value: data.previous_1_month },
            { label: '1년전', value: data.previous_1_year },
          ].map(({ label, value }) => {
            const diff = value - data.score;
            const colorClass = label === '현재' ? '' : diff > 0 ? 'text-emerald-600' : diff < 0 ? 'text-red-500' : '';
            return (
              <div key={label} className="flex flex-col">
                <span className="text-[10px] uppercase tracking-wider opacity-40 font-medium">{label}</span>
                <span className={`tabular-nums ${label === '현재' ? 'font-bold' : `font-semibold ${colorClass}`}`}>
                  {value.toFixed(1)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
      {showLegend && <LegendPopup items={FEAR_GREED_LEGEND} onClose={() => setShowLegend(false)} />}
    </div>
  );
}

const VIX_THRESHOLDS = [
  { max: 12, label: '매우 안정', bg: 'from-emerald-600/15 to-emerald-700/5 border-emerald-400/60', text: 'text-emerald-800', badge: 'bg-emerald-100 text-emerald-700 border-emerald-300' },
  { max: 20, label: '안정', bg: 'from-green-500/10 to-green-600/5 border-green-300/60', text: 'text-green-800', badge: 'bg-green-100 text-green-700 border-green-300' },
  { max: 25, label: '보통', bg: 'from-gray-400/10 to-gray-500/5 border-gray-300/60', text: 'text-gray-700', badge: 'bg-gray-100 text-gray-600 border-gray-300' },
  { max: 30, label: '불안', bg: 'from-orange-500/10 to-orange-600/5 border-orange-300/60', text: 'text-orange-800', badge: 'bg-orange-100 text-orange-700 border-orange-300' },
  { max: Infinity, label: '공포', bg: 'from-red-600/15 to-red-700/5 border-red-400/60', text: 'text-red-800', badge: 'bg-red-100 text-red-700 border-red-300' },
] as const;

function getVixStyle(current: number) {
  return VIX_THRESHOLDS.find(t => current <= t.max)!;
}

const VIX_LEGEND = [
  { label: '매우 안정', range: '~12', color: 'bg-emerald-600' },
  { label: '안정', range: '12–20', color: 'bg-green-500' },
  { label: '보통', range: '20–25', color: 'bg-gray-400' },
  { label: '불안', range: '25–30', color: 'bg-orange-400' },
  { label: '공포', range: '30+', color: 'bg-red-500' },
];

function VixCard({ data }: { data: VixData }) {
  const [open, setOpen] = useState(false);
  const [showLegend, setShowLegend] = useState(false);

  const style = getVixStyle(data.current);
  const changeColor = data.change > 0 ? 'text-red-500' : data.change < 0 ? 'text-emerald-600' : '';

  // VIX 게이지: 10~50 범위를 0~100%로 매핑
  const vixPct = Math.max(0, Math.min(100, ((data.current - 10) / 40) * 100));

  return (
    <div className={`bg-gradient-to-r ${style.bg} ${style.text} border rounded-lg relative`}>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 cursor-pointer"
      >
        <span className="text-base flex-shrink-0">📉</span>
        <span className="font-semibold text-xs sm:text-sm whitespace-nowrap">VIX</span>
        <span className={`text-[10px] sm:text-xs px-1.5 py-0.5 rounded border font-medium flex-shrink-0 ${style.badge}`}>
          {style.label}
        </span>
        <HelpButton onClick={e => { e.stopPropagation(); setShowLegend(v => !v); }} />
        <div className="flex-1 mx-1 h-2 bg-black/10 rounded-full overflow-hidden min-w-[40px]">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${vixPct}%`,
              background: `linear-gradient(90deg, #059669 0%, #22c55e 25%, #6b7280 50%, #f97316 75%, #dc2626 100%)`,
              backgroundSize: '100vw',
            }}
          />
        </div>
        <span className="ml-auto font-bold text-sm sm:text-base tabular-nums flex-shrink-0">
          {data.current.toFixed(2)}
        </span>
        <svg
          className={`w-4 h-4 flex-shrink-0 opacity-50 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div className={`overflow-hidden transition-all duration-200 ${open ? 'max-h-40' : 'max-h-0'}`}>
        <div className="px-3 pb-2.5 grid grid-cols-3 gap-x-3 gap-y-1.5 text-xs sm:text-sm">
          <div className="flex flex-col">
            <span className="text-[10px] uppercase tracking-wider opacity-40 font-medium">현재</span>
            <span className="tabular-nums font-bold">{data.current.toFixed(2)}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] uppercase tracking-wider opacity-40 font-medium">전일</span>
            <span className="tabular-nums font-semibold">{data.previous_close.toFixed(2)}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] uppercase tracking-wider opacity-40 font-medium">변동</span>
            <span className={`tabular-nums font-semibold ${changeColor}`}>
              {data.change >= 0 ? '+' : ''}{data.change.toFixed(2)} ({data.change_pct >= 0 ? '+' : ''}{data.change_pct.toFixed(2)}%)
            </span>
          </div>
        </div>
      </div>
      {showLegend && <LegendPopup items={VIX_LEGEND} onClose={() => setShowLegend(false)} />}
    </div>
  );
}

export function KosdaqStatusBanner() {
  const { isAdmin } = useAuthStore();
  const { data: marketStatus } = useMarketStatus();
  const { data: fearGreed } = useFearGreedIndex();
  const { data: vix } = useVixIndex();

  if (!isAdmin) return null;

  const hasKospi = marketStatus?.kospi?.status && marketStatus.kospi.status !== 'unknown';
  const hasKosdaq = marketStatus?.kosdaq?.status && marketStatus.kosdaq.status !== 'unknown';
  const hasFearGreed = fearGreed && typeof fearGreed.score === 'number';
  const hasVix = vix && typeof vix.current === 'number';

  if (!hasKospi && !hasKosdaq && !hasFearGreed && !hasVix) return null;

  return (
    <div className="flex flex-col gap-2 mb-3">
      {(hasFearGreed || hasVix) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {hasFearGreed && <FearGreedCard data={fearGreed} />}
          {hasVix && <VixCard data={vix} />}
        </div>
      )}
      {(hasKospi || hasKosdaq) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {hasKospi && <IndexCard data={marketStatus!.kospi} label="코스피" icon="📈" />}
          {hasKosdaq && <IndexCard data={marketStatus!.kosdaq} label="코스닥" icon="📊" />}
        </div>
      )}
    </div>
  );
}
