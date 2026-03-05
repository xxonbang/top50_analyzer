import { cn } from '@/lib/utils';
import { AnimatedNumber } from '@/components/common';
import type { SignalType } from '@/services/types';

interface SignalCardProps {
  signal: SignalType;
  count: number;
  active?: boolean;
  onClick?: () => void;
}

const signalConfig: Record<SignalType, {
  label: string;
  colorClass: string;
  icon: React.ReactNode;
}> = {
  '적극매수': {
    label: '적극매수',
    colorClass: 'strong-buy',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 11l-5-5-5 5M17 18l-5-5-5 5"/>
      </svg>
    ),
  },
  '매수': {
    label: '매수',
    colorClass: 'buy',
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 15l-6-6-6 6"/>
      </svg>
    ),
  },
  '중립': {
    label: '중립',
    colorClass: 'neutral',
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M5 12h14"/>
      </svg>
    ),
  },
  '매도': {
    label: '매도',
    colorClass: 'sell',
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M6 9l6 6 6-6"/>
      </svg>
    ),
  },
  '적극매도': {
    label: '적극매도',
    colorClass: 'strong-sell',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M7 13l5 5 5-5M7 6l5 5 5-5"/>
      </svg>
    ),
  },
};

const colorStyles: Record<string, {
  base: string;
  hover: string;
  active: string;
  bar: string;
  icon: string;
  text: string;
}> = {
  'strong-buy': {
    base: 'border-emerald-600/20',
    hover: 'hover:border-emerald-600/40 hover:shadow-emerald-600/10',
    active: 'border-emerald-600 bg-emerald-600/5',
    bar: 'bg-emerald-600',
    icon: 'bg-emerald-600/10 text-emerald-600',
    text: 'text-emerald-600',
  },
  'buy': {
    base: 'border-emerald-500/20',
    hover: 'hover:border-emerald-500/40 hover:shadow-emerald-500/10',
    active: 'border-emerald-500 bg-emerald-500/5',
    bar: 'bg-emerald-500',
    icon: 'bg-emerald-500/10 text-emerald-500',
    text: 'text-emerald-500',
  },
  'neutral': {
    base: 'border-amber-600/20',
    hover: 'hover:border-amber-600/40 hover:shadow-amber-600/10',
    active: 'border-amber-600 bg-amber-600/5',
    bar: 'bg-amber-600',
    icon: 'bg-amber-600/10 text-amber-600',
    text: 'text-amber-600',
  },
  'sell': {
    base: 'border-orange-600/20',
    hover: 'hover:border-orange-600/40 hover:shadow-orange-600/10',
    active: 'border-orange-600 bg-orange-600/5',
    bar: 'bg-orange-600',
    icon: 'bg-orange-600/10 text-orange-600',
    text: 'text-orange-600',
  },
  'strong-sell': {
    base: 'border-red-600/20',
    hover: 'hover:border-red-600/40 hover:shadow-red-600/10',
    active: 'border-red-600 bg-red-600/5',
    bar: 'bg-red-600',
    icon: 'bg-red-600/10 text-red-600',
    text: 'text-red-600',
  },
};

export function SignalCard({ signal, count, active = false, onClick }: SignalCardProps) {
  const config = signalConfig[signal];
  const styles = colorStyles[config.colorClass];

  return (
    <div
      onClick={onClick}
      className={cn(
        'relative bg-bg-secondary rounded-xl md:rounded-2xl py-3 px-1 md:py-5 md:px-4 text-center',
        'transition-all duration-300 ease-out cursor-pointer overflow-hidden border',
        'shadow-sm hover:-translate-y-1 hover:shadow-lg',
        styles.base,
        styles.hover,
        active && styles.active,
      )}
    >
      {/* Top bar */}
      <div className={cn('absolute top-0 left-0 right-0 h-1 md:h-1.5 rounded-t-xl md:rounded-t-2xl', styles.bar)} />

      {/* Icon */}
      <div className={cn(
        'w-7 h-7 md:w-10 md:h-10 rounded-lg flex items-center justify-center mx-auto mb-1.5 md:mb-3 transition-transform',
        styles.icon,
        'group-hover:scale-105'
      )}>
        {config.icon}
      </div>

      {/* Count */}
      <div className={cn('text-lg md:text-4xl font-extrabold mb-0.5 md:mb-1 tracking-tight', styles.text)}>
        <AnimatedNumber value={count} duration={500} />
      </div>

      {/* Label */}
      <div className={cn('text-[0.65rem] md:text-xs font-semibold uppercase tracking-wide', styles.text)}>
        {config.label}
      </div>

      {/* Active indicator */}
      {active && (
        <div className={cn('absolute bottom-2 left-1/2 -translate-x-1/2 w-6 h-0.5 rounded-full opacity-50', styles.bar)} />
      )}
    </div>
  );
}
