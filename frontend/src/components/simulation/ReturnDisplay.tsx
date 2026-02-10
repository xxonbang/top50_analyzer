interface ReturnDisplayProps {
  value: number | null;
  size?: 'sm' | 'md' | 'lg';
}

export function ReturnDisplay({ value, size = 'md' }: ReturnDisplayProps) {
  if (value === null) {
    return <span className="text-text-muted text-xs">-</span>;
  }

  const isPositive = value > 0;
  const isNegative = value < 0;

  const colorClass = isPositive
    ? 'text-signal-strong-buy'
    : isNegative
      ? 'text-signal-strong-sell'
      : 'text-text-secondary';

  const sizeClass = size === 'lg'
    ? 'text-2xl font-bold'
    : size === 'md'
      ? 'text-sm font-semibold'
      : 'text-xs font-medium';

  return (
    <span className={`${colorClass} ${sizeClass} tabular-nums`}>
      {isPositive ? '+' : ''}{value.toFixed(2)}%
    </span>
  );
}
