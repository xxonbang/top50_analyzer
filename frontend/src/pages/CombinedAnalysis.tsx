import { useState, useMemo, memo } from 'react';
import { useCombinedData, useCombinedHistoryData } from '@/hooks/useCombinedData';
import type { CombinedStock, CombinedAnalysisData, MarketType, SignalType, MatchStatus, StockCriteria } from '@/services/types';
import { LoadingSpinner, EmptyState, AnimatedNumber, KosdaqStatusBanner, TipText, ViewingHistoryBanner } from '@/components/common';
import { SignalBadge } from '@/components/signal';
import { MarketTabs } from '@/components/stock';
import { NewsAnalysisSection } from '@/components/stock/NewsAnalysisSection';
import { CriteriaIndicator } from '@/components/stock/CriteriaIndicator';
import { CriteriaLegend } from '@/components/stock/CriteriaLegend';
import { NewsSection } from '@/components/news';
import { useUIStore } from '@/store/uiStore';
import { useAuthStore } from '@/store/authStore';
import { WarningDot } from '@/components/stock/WarningDot';
import { cn, getWarningRingClass } from '@/lib/utils';

// 시그널 타입 리스트
const SIGNAL_TYPES: SignalType[] = ['적극매수', '매수', '중립', '매도', '적극매도'];

// 일치 상태 뱃지
function MatchStatusBadge({ status }: { status: MatchStatus }) {
  const config: Record<MatchStatus, { label: string; shortLabel: string; className: string; icon: string }> = {
    'match': { label: '완전 일치', shortLabel: '일치', className: 'bg-emerald-100 text-emerald-700 border-emerald-200', icon: '✓' },
    'partial': { label: '유사', shortLabel: '유사', className: 'bg-blue-100 text-blue-700 border-blue-200', icon: '≈' },
    'mismatch': { label: '불일치', shortLabel: '불일치', className: 'bg-red-100 text-red-700 border-red-200', icon: '✗' },
    'vision-only': { label: 'Vision만', shortLabel: 'V', className: 'bg-purple-100 text-purple-700 border-purple-200', icon: '👁' },
    'api-only': { label: 'API만', shortLabel: 'A', className: 'bg-cyan-100 text-cyan-700 border-cyan-200', icon: '📡' },
    'no_data': { label: '데이터 없음', shortLabel: '—', className: 'bg-gray-100 text-gray-500 border-gray-200', icon: '—' },
  };

  const { label, shortLabel, className, icon } = config[status];

  return (
    <span className={cn('inline-flex items-center gap-0.5 md:gap-1 px-1.5 md:px-2 py-0.5 rounded text-[0.65rem] md:text-xs font-medium border', className)}>
      <span>{icon}</span>
      <span className="hidden md:inline">{label}</span>
      <span className="md:hidden">{shortLabel}</span>
    </span>
  );
}

// 신뢰도 바
function ConfidenceBar({ score }: { score: number }) {
  const percentage = Math.round(score * 100);
  const colorClass = score >= 0.8 ? 'bg-emerald-500' : score >= 0.5 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-1.5 md:gap-2">
      <div className="flex-1 h-1 md:h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', colorClass)} style={{ width: `${percentage}%` }} />
      </div>
      <span className="text-[0.65rem] md:text-xs font-medium text-text-muted w-7 md:w-8">{percentage}%</span>
    </div>
  );
}

// 통합 종목 카드 (메모화)
const CombinedStockCard = memo(function CombinedStockCard({ stock, criteria, isAdmin }: { stock: CombinedStock; criteria: StockCriteria | null; isAdmin: boolean }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isVisionDetailOpen, setIsVisionDetailOpen] = useState(false);
  const [isApiDetailOpen, setIsApiDetailOpen] = useState(false);

  const changeRate = stock.api_data?.price?.change_rate_pct ?? 0;
  const priceChangeColor = changeRate > 0 ? 'text-red-500' : changeRate < 0 ? 'text-blue-500' : 'text-text-secondary';

  return (
    <div className={cn(
      'relative bg-bg-secondary border rounded-xl p-3 md:p-4',
      stock.match_status === 'match' ? 'border-emerald-300 bg-emerald-50/30' :
      stock.match_status === 'mismatch' ? 'border-red-300 bg-red-50/30' :
      'border-border',
      isAdmin && getWarningRingClass(criteria),
    )}>
      {isAdmin && <WarningDot criteria={criteria} />}
      {/* 헤더 */}
      <div className="flex justify-between items-start mb-2 md:mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 md:gap-2 mb-1 flex-wrap">
            <a
              href={`https://m.stock.naver.com/domestic/stock/${stock.code}/total`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-bold text-base md:text-lg text-text-primary hover:text-accent-primary transition-colors truncate"
            >
              {stock.name}
            </a>
            <span className={`text-[0.65rem] md:text-xs px-1 md:px-1.5 py-0.5 rounded flex-shrink-0 ${stock.market === 'KOSPI' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'}`}>
              {stock.market}
            </span>
          </div>
          {stock.api_data?.price?.current != null && (
            <div className="flex items-baseline gap-1.5 md:gap-2">
              <span className="text-base md:text-lg font-bold">{stock.api_data.price.current.toLocaleString()}원</span>
              <span className={cn('text-xs md:text-sm font-medium', priceChangeColor)}>
                {changeRate > 0 ? '+' : ''}{changeRate.toFixed(2)}%
              </span>
            </div>
          )}
        </div>
        <MatchStatusBadge status={stock.match_status} />
      </div>

      {/* 기준 인디케이터 (Admin 전용) */}
      {isAdmin && criteria && (
        <>
          <CriteriaIndicator criteria={criteria} />
          {criteria.short_selling_alert?.met && (
            <span className="text-[9px] text-red-600 font-medium">
              공매도 주의 ({criteria.short_selling_alert.reason})
            </span>
          )}
          {criteria.overheating_alert?.met && (
            <span className="text-[9px] text-orange-600 font-medium">
              과열 주의 ({criteria.overheating_alert.reason})
            </span>
          )}
          {criteria.reverse_ma_alert?.met && (
            <span className="text-[9px] text-violet-600 font-medium">
              역배열 주의 ({criteria.reverse_ma_alert.reason})
            </span>
          )}
        </>
      )}

      {/* 시그널 비교 */}
      <div className="grid grid-cols-2 gap-2 md:gap-3 mb-2 md:mb-3">
        <div className="bg-bg-primary rounded-lg p-2 md:p-3">
          <div className="text-[0.65rem] md:text-xs text-text-muted mb-1 md:mb-1.5 flex items-center gap-1">
            <span>👁</span> <span className="hidden md:inline">Vision AI</span><span className="md:hidden">Vision</span>
          </div>
          {stock.vision_signal ? (
            <SignalBadge signal={stock.vision_signal} />
          ) : (
            <span className="text-[0.65rem] md:text-xs text-text-muted">없음</span>
          )}
        </div>
        <div className="bg-bg-primary rounded-lg p-2 md:p-3">
          <div className="text-[0.65rem] md:text-xs text-text-muted mb-1 md:mb-1.5 flex items-center gap-1">
            <span>📡</span> <span className="hidden md:inline">한투 API</span><span className="md:hidden">API</span>
          </div>
          {stock.api_signal ? (
            <SignalBadge signal={stock.api_signal} />
          ) : (
            <span className="text-[0.65rem] md:text-xs text-text-muted">없음</span>
          )}
        </div>
      </div>

      {/* 신뢰도 */}
      <div className="mb-2 md:mb-3">
        <div className="text-[0.65rem] md:text-xs text-text-muted mb-1">신뢰도</div>
        <ConfidenceBar score={stock.confidence} />
      </div>

      {/* 분석 근거 토글 */}
      {(stock.vision_reason || stock.api_reason) && (
        <div className="cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
          <div className="flex items-center justify-between text-[0.65rem] md:text-xs text-text-muted mb-1">
            <span>분석 근거</span>
            <span className="transition-transform duration-200" style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
          </div>
          <div className={cn('overflow-hidden transition-all duration-300 ease-in-out', isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0')}>
            <div className="space-y-1.5 md:space-y-2">
              {stock.vision_reason && (
                <div className="bg-purple-50 border border-purple-100 rounded-lg p-2 md:p-3">
                  <div className="text-[0.65rem] md:text-xs font-medium text-purple-700 mb-1">👁 Vision</div>
                  <p className="text-xs md:text-sm text-text-secondary">{stock.vision_reason}</p>
                  {stock.vision_news_analysis && (
                    <div className="mt-2 pt-2 border-t border-purple-100">
                      <div
                        className="flex items-center justify-between cursor-pointer"
                        onClick={(e) => { e.stopPropagation(); setIsVisionDetailOpen(!isVisionDetailOpen); }}
                      >
                        <span className="text-[0.65rem] md:text-xs font-semibold text-text-muted">재료분석</span>
                        <span className="text-[0.6rem] text-text-muted transition-transform duration-200" style={{ transform: isVisionDetailOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
                      </div>
                      <div className={cn('overflow-hidden transition-all duration-300 ease-in-out', isVisionDetailOpen ? 'max-h-[800px] opacity-100' : 'max-h-0 opacity-0')}>
                        <NewsAnalysisSection newsAnalysis={stock.vision_news_analysis} />
                      </div>
                    </div>
                  )}
                </div>
              )}
              {stock.api_reason && (
                <div className="bg-cyan-50 border border-cyan-100 rounded-lg p-2 md:p-3">
                  <div className="text-[0.65rem] md:text-xs font-medium text-cyan-700 mb-1">📡 API</div>
                  <p className="text-xs md:text-sm text-text-secondary">{stock.api_reason}</p>
                  {(stock.api_key_factors || stock.api_confidence != null || stock.api_risk_level || stock.api_news_analysis) && (
                    <div className="mt-2 pt-2 border-t border-cyan-100">
                      <div
                        className="flex items-center justify-between cursor-pointer"
                        onClick={(e) => { e.stopPropagation(); setIsApiDetailOpen(!isApiDetailOpen); }}
                      >
                        <span className="text-[0.65rem] md:text-xs font-semibold text-text-muted">분석지표 + 재료분석</span>
                        <span className="text-[0.6rem] text-text-muted transition-transform duration-200" style={{ transform: isApiDetailOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
                      </div>
                      <div className={cn('overflow-hidden transition-all duration-300 ease-in-out', isApiDetailOpen ? 'max-h-[800px] opacity-100' : 'max-h-0 opacity-0')}>
                        {stock.api_key_factors && (
                          <div className="mt-2">
                            <div className="grid grid-cols-2 gap-1.5 md:gap-2 text-[0.65rem] md:text-xs">
                              <div><span className="text-text-muted">추세:</span> {stock.api_key_factors.price_trend}</div>
                              <div><span className="text-text-muted">거래량:</span> {stock.api_key_factors.volume_signal}</div>
                              <div><span className="text-text-muted">외인:</span> {stock.api_key_factors.foreign_flow}</div>
                              <div><span className="text-text-muted">밸류:</span> {stock.api_key_factors.valuation}</div>
                            </div>
                          </div>
                        )}
                        {(stock.api_confidence != null || stock.api_risk_level) && (
                          <div className="mt-2 text-[0.65rem] md:text-xs text-text-muted">
                            {stock.api_confidence != null && <>신뢰도: {((stock.api_confidence ?? 0) * 100).toFixed(0)}%</>}
                            {stock.api_confidence != null && stock.api_risk_level && ' | '}
                            {stock.api_risk_level && <>위험도: {stock.api_risk_level}</>}
                          </div>
                        )}
                        <NewsAnalysisSection newsAnalysis={stock.api_news_analysis} />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 뉴스 섹션 - Vision 뉴스와 API 뉴스 중 있는 것 표시 (Vision 우선) */}
      {(() => {
        const combinedNews = stock.vision_news?.length ? stock.vision_news : stock.api_news;
        return combinedNews && combinedNews.length > 0 ? (
          <>
            <div className="md:hidden">
              <NewsSection news={combinedNews} isMobile={true} />
            </div>
            <div className="hidden md:block">
              <NewsSection news={combinedNews} isMobile={false} />
            </div>
          </>
        ) : null;
      })()}
    </div>
  );
});

// 통계 요약 카드
function StatCard({ icon, label, value, subValue, colorClass }: {
  icon: string;
  label: string;
  value: string | number;
  subValue?: string;
  colorClass?: string;
}) {
  return (
    <div className="bg-bg-secondary border border-border rounded-xl px-2 py-2 md:px-4 md:py-3 flex items-center gap-1.5 md:gap-3 shadow-sm">
      <div className={cn('w-7 h-7 md:w-10 md:h-10 rounded-lg flex items-center justify-center text-sm md:text-xl flex-shrink-0', colorClass || 'bg-gray-100')}>
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[0.55rem] md:text-[0.65rem] text-text-muted uppercase tracking-wide font-semibold">
          {label}
        </div>
        <div className="text-sm md:text-base font-bold text-text-primary">
          {typeof value === 'number' ? <AnimatedNumber value={value} duration={500} /> : value}
          {subValue && <span className="text-[0.65rem] md:text-sm text-text-muted font-medium ml-0.5 md:ml-1">({subValue})</span>}
        </div>
      </div>
    </div>
  );
}

export function CombinedAnalysis() {
  const [marketFilter, setMarketFilter] = useState<MarketType>('all');
  // 멀티셀렉트: 빈 Set = 전체 선택
  const [matchFilters, setMatchFilters] = useState<Set<MatchStatus>>(new Set());
  const [signalFilters, setSignalFilters] = useState<Set<SignalType>>(new Set());
  const { isViewingHistory, viewingHistoryDateTime, isCompactView } = useUIStore();
  const isAdmin = useAuthStore((s) => s.isAdmin);

  // viewingHistoryDateTime: "2026-02-04_0700" → filename: "combined_2026-02-04_0700.json"
  const historyFilename = viewingHistoryDateTime ? `combined_${viewingHistoryDateTime}.json` : null;

  // 최신 데이터
  const { data: latestData, isLoading: isLoadingLatest } = useCombinedData();

  // 히스토리 데이터
  const { data: historyData, isLoading: isLoadingHistory } = useCombinedHistoryData(
    isViewingHistory ? historyFilename : null
  );

  // 실제 사용할 데이터 선택
  const data: CombinedAnalysisData | null | undefined = isViewingHistory ? historyData : latestData;
  const isLoading = isViewingHistory ? isLoadingHistory : isLoadingLatest;
  const criteriaData = data?.criteria_data ?? null;

  // 필터 토글 함수
  const toggleMatchFilter = (status: MatchStatus) => {
    setMatchFilters(prev => {
      const next = new Set(prev);
      if (next.has(status)) {
        next.delete(status);
      } else {
        next.add(status);
      }
      return next;
    });
  };

  const toggleSignalFilter = (signal: SignalType) => {
    setSignalFilters(prev => {
      const next = new Set(prev);
      if (next.has(signal)) {
        next.delete(signal);
      } else {
        next.add(signal);
      }
      return next;
    });
  };

  const clearAllFilters = () => {
    setMatchFilters(new Set());
    setSignalFilters(new Set());
  };

  // 필터링된 종목
  const filteredStocks = useMemo(() => {
    if (!data?.stocks) return [];

    let stocks = [...data.stocks];

    // 시장 필터
    if (marketFilter !== 'all') {
      stocks = stocks.filter(s => s.market.toLowerCase() === marketFilter);
    }

    // 일치 상태 필터 (멀티셀렉트: 빈 Set = 전체)
    if (matchFilters.size > 0) {
      stocks = stocks.filter(s => matchFilters.has(s.match_status));
    }

    // 시그널 필터 (멀티셀렉트: 빈 Set = 전체)
    // OR 로직: vision 또는 api 시그널 중 하나라도 선택된 필터에 포함되면 표시
    if (signalFilters.size > 0) {
      stocks = stocks.filter(s => {
        const visionMatch = s.vision_signal && signalFilters.has(s.vision_signal);
        const apiMatch = s.api_signal && signalFilters.has(s.api_signal);
        return visionMatch || apiMatch;
      });
    }

    // 거래대금 순위 기준 정렬 (API 데이터의 volume_rank 사용, 없으면 뒤로)
    return stocks.sort((a, b) => {
      const rankA = a.api_data?.ranking?.volume_rank ?? Infinity;
      const rankB = b.api_data?.ranking?.volume_rank ?? Infinity;
      return rankA - rankB;
    });
  }, [data, marketFilter, matchFilters, signalFilters]);

  // 통계 데이터 (pre-calculated에서 가져옴)
  const stats = data?.stats || { total: 0, match: 0, partial: 0, mismatch: 0, vision_only: 0, api_only: 0, no_data: 0, avg_confidence: 0 };

  // Faceted counts: 각 필터 차원은 다른 필터가 적용된 상태에서 자신의 카운트를 계산
  const { marketCounts, signalCounts, matchCounts } = useMemo(() => {
    const emptySignal = { '적극매수': 0, '매수': 0, '중립': 0, '매도': 0, '적극매도': 0 } as Record<SignalType, number>;
    const emptyMatch = { match: 0, partial: 0, mismatch: 0, 'vision-only': 0, 'api-only': 0, no_data: 0 } as Record<MatchStatus, number>;
    if (!data?.stocks) {
      return {
        marketCounts: { all: 0, kospi: 0, kosdaq: 0 },
        signalCounts: emptySignal,
        matchCounts: emptyMatch,
      };
    }

    const allStocks = data.stocks;
    const hasSignal = (s: CombinedStock) =>
      (s.vision_signal && signalFilters.has(s.vision_signal)) || (s.api_signal && signalFilters.has(s.api_signal));
    const hasMatch = (s: CombinedStock) => matchFilters.has(s.match_status);

    // 시장 필터 적용된 베이스
    const afterMarket = marketFilter !== 'all'
      ? allStocks.filter(s => s.market.toLowerCase() === marketFilter)
      : allStocks;

    // 일치상태 카운트: 시장 + 시그널 필터 적용, 일치상태 필터 미적용
    const forMatch = signalFilters.size > 0 ? afterMarket.filter(hasSignal) : afterMarket;
    const mc = { ...emptyMatch };
    for (const s of forMatch) mc[s.match_status]++;

    // 시그널 카운트: 시장 + 일치상태 필터 적용, 시그널 필터 미적용
    const forSignal = matchFilters.size > 0 ? afterMarket.filter(hasMatch) : afterMarket;
    const sc = { ...emptySignal };
    for (const s of forSignal) {
      if (s.vision_signal && s.vision_signal in sc) sc[s.vision_signal as SignalType]++;
      if (s.api_signal && s.api_signal in sc) sc[s.api_signal as SignalType]++;
    }

    // 시장 카운트: 일치상태 + 시그널 필터 적용, 시장 필터 미적용
    let forMarket = [...allStocks];
    if (matchFilters.size > 0) forMarket = forMarket.filter(hasMatch);
    if (signalFilters.size > 0) forMarket = forMarket.filter(hasSignal);

    return {
      marketCounts: {
        all: forMarket.length,
        kospi: forMarket.filter(s => s.market === 'KOSPI').length,
        kosdaq: forMarket.filter(s => s.market === 'KOSDAQ').length,
      },
      signalCounts: sc,
      matchCounts: mc,
    };
  }, [data, marketFilter, matchFilters, signalFilters]);

  if (isLoading) {
    return (
      <section id="combined-analysis" className="mb-10">
        <LoadingSpinner message="종합 분석 데이터 로딩 중..." />
      </section>
    );
  }

  if (!data || !data.stocks || data.stocks.length === 0) {
    return (
      <section id="combined-analysis" className="mb-10">
        <EmptyState
          icon="📊"
          title="종합 분석 데이터가 없습니다"
          description="Vision AI 분석과 한투 API 분석이 완료되면 여기에 비교 결과가 표시됩니다."
        />
      </section>
    );
  }

  return (
    <section id="combined-analysis" className="mb-10">
      {/* 헤더 */}
      <div className="flex justify-between items-center mb-4 md:mb-5 flex-wrap gap-2 md:gap-3">
        <div className="flex-1 min-w-0">
          <h2 className="text-lg md:text-xl font-bold text-text-primary mb-0.5 md:mb-1">분석 종합</h2>
          <p className="text-xs md:text-sm text-text-muted">Vision AI와 한투 API 분석 결과 비교 검증</p>
        </div>
      </div>

      {/* 히스토리 배너 */}
      {isViewingHistory && viewingHistoryDateTime && (
        <ViewingHistoryBanner dateTime={viewingHistoryDateTime} />
      )}

      <KosdaqStatusBanner />

      {/* 분석 일시 */}
      <div className="grid grid-cols-2 gap-2 md:gap-3 mb-4 md:mb-5">
        <div className="bg-bg-secondary border border-border rounded-xl px-3 md:px-4 py-2.5 md:py-3 flex items-center gap-2 md:gap-3 shadow-sm">
          <div className="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-blue-100 flex items-center justify-center text-base md:text-xl flex-shrink-0">
            📅
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[0.6rem] md:text-[0.65rem] text-text-muted uppercase tracking-wide font-semibold">
              분석 일시
            </div>
            <div className="text-sm md:text-base font-bold text-text-primary">
              {data.date}
            </div>
            {data.time && (
              <div className="text-[0.65rem] md:text-xs text-text-muted font-medium">
                {data.time.length === 4 ? `${data.time.slice(0, 2)}:${data.time.slice(2)}` : data.time}
              </div>
            )}
          </div>
        </div>
        <div className="bg-bg-secondary border border-border rounded-xl px-3 md:px-4 py-2.5 md:py-3 flex items-center gap-2 md:gap-3 shadow-sm">
          <div className="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-emerald-100 flex items-center justify-center text-base md:text-xl flex-shrink-0">
            📊
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[0.6rem] md:text-[0.65rem] text-text-muted uppercase tracking-wide font-semibold">
              분석 종목
            </div>
            <div className="text-sm md:text-base font-bold text-text-primary"><AnimatedNumber value={stats.total} duration={500} />개</div>
          </div>
        </div>
      </div>

      {/* 통계 요약 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <StatCard icon="📊" label="총 종목" value={stats.total} colorClass="bg-gray-100" />
        <StatCard icon="✓" label="완전 일치" value={stats.match} subValue={stats.total > 0 ? `${((stats.match / stats.total) * 100).toFixed(0)}%` : '0%'} colorClass="bg-emerald-100" />
        <StatCard icon="≈" label="유사" value={stats.partial} colorClass="bg-blue-100" />
        <StatCard icon="✗" label="불일치" value={stats.mismatch} colorClass="bg-red-100" />
      </div>

      {/* 평균 신뢰도 */}
      <div className="bg-bg-secondary border border-border rounded-xl p-4 mb-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium">평균 신뢰도</span>
          <span className="text-lg font-bold">{(stats.avg_confidence * 100).toFixed(0)}%</span>
        </div>
        <ConfidenceBar score={stats.avg_confidence} />
        <p className="text-xs text-text-muted mt-2">
          두 분석 소스의 일치율이 높을수록 신뢰도가 높습니다. 완전 일치=100%, 유사=70%, 단일 소스=50%, 불일치=30%
        </p>
      </div>

      <TipText>
        "완전 일치" 종목은 Vision AI와 API 분석 시그널이 동일합니다. "불일치" 종목은 추가 검토가 필요합니다.
      </TipText>

      {/* 필터 영역 */}
      <div className="bg-bg-secondary border border-border rounded-xl p-4 mb-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-text-primary">필터</span>
          {(matchFilters.size > 0 || signalFilters.size > 0) && (
            <button
              onClick={clearAllFilters}
              className="text-xs text-accent-primary hover:underline"
            >
              필터 초기화
            </button>
          )}
        </div>

        {/* 일치 상태 필터 */}
        <div className="mb-3">
          <div className="text-xs text-text-muted mb-2">일치 상태 (복수 선택 가능)</div>
          <div className="flex flex-wrap gap-2">
            {[
              { value: 'match' as MatchStatus, label: '완전 일치', icon: '✓', count: matchCounts['match'] },
              { value: 'partial' as MatchStatus, label: '유사', icon: '≈', count: matchCounts['partial'] },
              { value: 'mismatch' as MatchStatus, label: '불일치', icon: '✗', count: matchCounts['mismatch'] },
              { value: 'vision-only' as MatchStatus, label: 'Vision만', icon: '👁', count: matchCounts['vision-only'] },
              { value: 'api-only' as MatchStatus, label: 'API만', icon: '📡', count: matchCounts['api-only'] },
              { value: 'no_data' as MatchStatus, label: '데이터 없음', icon: '—', count: matchCounts['no_data'] },
            ].map(({ value, label, icon, count }) => (
              <button
                key={value}
                onClick={() => toggleMatchFilter(value)}
                className={cn(
                  'px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all border',
                  matchFilters.has(value)
                    ? 'bg-accent-primary text-white border-accent-primary'
                    : 'bg-bg-primary text-text-secondary border-border hover:border-accent-primary'
                )}
              >
                <span className="mr-1">{icon}</span>
                {label} ({count})
              </button>
            ))}
          </div>
        </div>

        {/* 시그널 필터 */}
        <div>
          <div className="text-xs text-text-muted mb-2">시그널 (복수 선택 가능)</div>
          <div className="flex flex-wrap gap-2">
            {SIGNAL_TYPES.map((signal) => {
              const signalColors: Record<SignalType, string> = {
                '적극매수': 'bg-signal-strong-buy text-white border-signal-strong-buy',
                '매수': 'bg-signal-buy text-white border-signal-buy',
                '중립': 'bg-signal-neutral text-white border-signal-neutral',
                '매도': 'bg-signal-sell text-white border-signal-sell',
                '적극매도': 'bg-signal-strong-sell text-white border-signal-strong-sell',
              };
              return (
                <button
                  key={signal}
                  onClick={() => toggleSignalFilter(signal)}
                  className={cn(
                    'px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all border',
                    signalFilters.has(signal)
                      ? signalColors[signal]
                      : 'bg-bg-primary text-text-secondary border-border hover:border-accent-primary'
                  )}
                >
                  {signal} ({signalCounts[signal]})
                </button>
              );
            })}
          </div>
        </div>

        {/* 선택된 필터 표시 */}
        {(matchFilters.size > 0 || signalFilters.size > 0) && (
          <div className="mt-3 pt-3 border-t border-border-light">
            <div className="text-sm font-medium text-accent-primary">
              선택된 필터: {' '}
              {matchFilters.size === 0 && signalFilters.size === 0 ? '전체' : (
                <>
                  {Array.from(matchFilters).map(m => {
                    const labels: Record<MatchStatus, string> = {
                      'match': '완전 일치', 'partial': '유사', 'mismatch': '불일치',
                      'vision-only': 'Vision만', 'api-only': 'API만', 'no_data': '데이터 없음'
                    };
                    return labels[m];
                  }).join(', ')}
                  {matchFilters.size > 0 && signalFilters.size > 0 && ' + '}
                  {Array.from(signalFilters).join(', ')}
                </>
              )}
              {' '}→ <span className="font-bold">{filteredStocks.length}건</span>
            </div>
          </div>
        )}
      </div>

      {/* 기준 범례 (Admin 전용) */}
      <CriteriaLegend isAdmin={isAdmin} hasCriteriaData={!!criteriaData} />

      {/* 시장 탭 */}
      <MarketTabs
        active={marketFilter}
        counts={marketCounts}
        onChange={setMarketFilter}
      />

      {/* 종목 그리드 */}
      {filteredStocks.length > 0 ? (
        isCompactView ? (
          // Compact 보기
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
            {filteredStocks.map(stock => (
              <a
                key={stock.code}
                href={`https://m.stock.naver.com/domestic/stock/${stock.code}/total`}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                  'relative flex items-center justify-between gap-2 px-3 py-2 border rounded-lg hover:border-accent-primary transition-all no-underline',
                  stock.match_status === 'match' ? 'bg-emerald-50/50 border-emerald-200' :
                  stock.match_status === 'mismatch' ? 'bg-red-50/50 border-red-200' :
                  'bg-bg-secondary border-border',
                  isAdmin && getWarningRingClass(criteriaData?.[stock.code]),
                )}
              >
                {isAdmin && <WarningDot criteria={criteriaData?.[stock.code]} />}
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-sm text-text-primary truncate">{stock.name}</div>
                  <div className="text-xs text-text-muted font-mono">{stock.code}</div>
                  {isAdmin && criteriaData?.[stock.code] && (
                    <CriteriaIndicator criteria={criteriaData[stock.code]} isCompact />
                  )}
                </div>
                <div className="flex flex-col items-end gap-0.5">
                  {stock.vision_signal && stock.api_signal && stock.vision_signal === stock.api_signal ? (
                    <SignalBadge signal={stock.vision_signal} size="sm" />
                  ) : (
                    <span className="text-[0.6rem] text-text-muted">
                      {stock.match_status === 'match' ? '✓' : stock.match_status === 'mismatch' ? '✗' : '~'}
                    </span>
                  )}
                </div>
              </a>
            ))}
          </div>
        ) : (
          // 일반 보기
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredStocks.map(stock => (
              <CombinedStockCard key={stock.code} stock={stock} criteria={criteriaData?.[stock.code] ?? null} isAdmin={isAdmin} />
            ))}
          </div>
        )
      ) : (
        <EmptyState
          icon="🔍"
          title="검색 결과가 없습니다"
          description="선택한 필터 조건에 맞는 종목이 없습니다."
        />
      )}
    </section>
  );
}
