import { SignalBadge } from '@/components/signal';
import { NewsSection } from '@/components/news';
import { NewsAnalysisSection } from './NewsAnalysisSection';
import { CriteriaIndicator } from './CriteriaIndicator';
import { formatTimeOnly } from '@/lib/utils';
import type { StockResult, StockCriteria } from '@/services/types';

interface StockCardProps {
  stock: StockResult;
  isCompact?: boolean;
  criteria?: StockCriteria | null;
}

export function StockCard({ stock, isCompact = false, criteria }: StockCardProps) {
  if (isCompact) {
    // Compact 보기: 간단한 한 줄 형태
    return (
      <a
        href={`https://m.stock.naver.com/domestic/stock/${stock.code}/total`}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-between gap-2 px-3 py-2.5 bg-bg-secondary border border-border rounded-lg mb-1.5 hover:border-accent-primary transition-all no-underline"
      >
        <div className="min-w-0 flex-1">
          <div className="font-medium text-sm text-text-primary truncate">{stock.name}</div>
          <div className="text-xs text-text-muted font-mono">{stock.code}</div>
          {criteria && <CriteriaIndicator criteria={criteria} isCompact />}
        </div>
        <SignalBadge signal={stock.signal} size="sm" />
      </a>
    );
  }

  // 일반 보기: 상세 카드 형태
  return (
    <div className="bg-bg-secondary border border-border rounded-xl p-3 md:p-4 mb-2.5 md:mb-3">
      <div className="flex justify-between items-start mb-2.5 md:mb-3">
        <a
          href={`https://m.stock.naver.com/domestic/stock/${stock.code}/total`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 min-w-0 text-inherit no-underline hover:text-accent-primary transition-colors"
        >
          <div className="font-semibold text-base md:text-lg text-text-primary truncate">{stock.name}</div>
          <div className="text-xs md:text-sm text-text-muted font-mono">{stock.code}</div>
        </a>
        <SignalBadge signal={stock.signal} />
      </div>
      {criteria && <CriteriaIndicator criteria={criteria} />}
      <div className="text-xs md:text-sm text-text-secondary leading-relaxed pt-2.5 md:pt-3 border-t border-border-light">
        {stock.reason || '-'}
      </div>
      <NewsAnalysisSection newsAnalysis={stock.news_analysis} />
      <div className="text-[0.65rem] md:text-xs text-text-muted mt-2 md:mt-2.5 flex gap-2 md:gap-3">
        {stock.capture_time && <span>캡처 {formatTimeOnly(stock.capture_time)}</span>}
        {stock.analysis_time && <span>분석 {formatTimeOnly(stock.analysis_time)}</span>}
      </div>
      {/* 모바일용 뉴스 섹션 (md 미만에서만 표시) */}
      <div className="md:hidden">
        <NewsSection news={stock.news} isMobile={true} />
      </div>
    </div>
  );
}
