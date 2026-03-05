import { SignalCard } from './SignalCard';
import type { SignalCounts, SignalType } from '@/services/types';

interface SignalSummaryProps {
  counts: SignalCounts;
  activeSignal: SignalType | null;
  onFilter: (signal: SignalType) => void;
}

const signals: SignalType[] = ['적극매수', '매수', '중립', '매도', '적극매도'];

export function SignalSummary({ counts, activeSignal, onFilter }: SignalSummaryProps) {
  return (
    <div className="grid grid-cols-5 gap-2 md:gap-3.5 mb-6">
      {signals.map((signal) => (
        <SignalCard
          key={signal}
          signal={signal}
          count={counts[signal]}
          active={activeSignal === signal}
          onClick={() => onFilter(signal)}
        />
      ))}
    </div>
  );
}
