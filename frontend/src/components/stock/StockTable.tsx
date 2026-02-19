import { SignalBadge } from '@/components/signal';
import { NewsSection } from '@/components/news';
import { NewsAnalysisSection } from './NewsAnalysisSection';
import { CriteriaIndicator } from './CriteriaIndicator';
import { formatTimeOnly } from '@/lib/utils';
import type { StockResult, StockCriteria } from '@/services/types';

interface StockTableProps {
  stocks: StockResult[];
  isCompact?: boolean;
  criteriaData?: Record<string, StockCriteria> | null;
}

export function StockTable({ stocks, isCompact = false, criteriaData }: StockTableProps) {
  if (isCompact) {
    // Compact 보기: 그리드 형태로 간단하게 표시
    return (
      <div className="hidden md:grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
        {stocks.map((stock) => (
          <a
            key={stock.code}
            href={`https://m.stock.naver.com/domestic/stock/${stock.code}/total`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between gap-2 px-3 py-2 bg-bg-secondary border border-border rounded-lg hover:border-accent-primary hover:bg-bg-primary transition-all no-underline"
          >
            <div className="min-w-0 flex-1">
              <div className="font-medium text-sm text-text-primary truncate">{stock.name}</div>
              <div className="text-xs text-text-muted font-mono">{stock.code}</div>
              {criteriaData?.[stock.code] && (
                <CriteriaIndicator criteria={criteriaData[stock.code]} isCompact />
              )}
            </div>
            <SignalBadge signal={stock.signal} size="sm" />
          </a>
        ))}
      </div>
    );
  }

  // 일반 보기: 테이블 형태
  return (
    <div className="bg-bg-secondary border border-border rounded-2xl overflow-hidden shadow-sm hidden md:block">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="bg-bg-primary px-4 py-3 text-left text-xs font-bold text-text-muted uppercase border-b border-border whitespace-nowrap">
              종목
            </th>
            <th className="bg-bg-primary px-4 py-3 text-left text-xs font-bold text-text-muted uppercase border-b border-border whitespace-nowrap">
              시그널
            </th>
            <th className="bg-bg-primary px-4 py-3 text-left text-xs font-bold text-text-muted uppercase border-b border-border">
              분석 근거
            </th>
            <th className="bg-bg-primary px-4 py-3 text-left text-xs font-bold text-text-muted uppercase border-b border-border whitespace-nowrap">
              시각
            </th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock) => (
            <tr key={stock.code} className="hover:bg-bg-primary group">
              <td className="px-4 py-3.5 border-b border-border-light align-top whitespace-nowrap">
                <a
                  href={`https://m.stock.naver.com/domestic/stock/${stock.code}/total`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-inherit no-underline hover:text-accent-primary hover:underline transition-colors"
                >
                  <div className="font-semibold text-text-primary text-base">{stock.name}</div>
                  <div className="text-xs text-text-muted font-mono mt-0.5">{stock.code}</div>
                </a>
                {criteriaData?.[stock.code] && (
                  <CriteriaIndicator criteria={criteriaData[stock.code]} isCompact />
                )}
              </td>
              <td className="px-4 py-3.5 border-b border-border-light align-top whitespace-nowrap">
                <SignalBadge signal={stock.signal} />
              </td>
              <td className="px-4 py-3.5 border-b border-border-light align-top">
                <div className="text-sm text-text-secondary leading-relaxed">
                  {stock.reason || '-'}
                </div>
                <NewsAnalysisSection newsAnalysis={stock.news_analysis} />
                {/* 데스크톱용 뉴스 섹션 */}
                <NewsSection news={stock.news} isMobile={false} />
              </td>
              <td className="px-4 py-3.5 border-b border-border-light align-top whitespace-nowrap">
                <div className="text-xs text-text-muted leading-relaxed">
                  {stock.capture_time && (
                    <div>캡처: {formatTimeOnly(stock.capture_time)}</div>
                  )}
                  {stock.analysis_time && (
                    <div>분석: {formatTimeOnly(stock.analysis_time)}</div>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
