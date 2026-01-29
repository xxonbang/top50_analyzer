import { cn } from '@/lib/utils';
import type { SignalType } from '@/services/types';

interface SignalBadgeProps {
  signal: SignalType;
  className?: string;
}

export function SignalBadge({ signal, className }: SignalBadgeProps) {
  const colorClasses: Record<SignalType, string> = {
    '적극매수': 'bg-emerald-100 text-signal-strong-buy',
    '매수': 'bg-emerald-100 text-signal-buy',
    '중립': 'bg-amber-100 text-signal-neutral',
    '매도': 'bg-orange-100 text-signal-sell',
    '적극매도': 'bg-red-100 text-signal-strong-sell',
  };

  return (
    <span
      className={cn(
        'inline-block px-2 md:px-3 py-0.5 md:py-1 rounded-2xl text-[0.65rem] md:text-xs font-semibold whitespace-nowrap',
        colorClasses[signal],
        className
      )}
    >
      {signal}
    </span>
  );
}
