import { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchKISData, fetchKISAnalysis } from '@/services/api';
import { useKISHistoryData } from '@/hooks/useKISHistoryData';
import { useCriteriaData } from '@/hooks/useCriteriaData';
import type { KISStockData, KISAnalysisResult, KISAnalysisData, MarketType, SignalType, SignalCounts, StockCriteria } from '@/services/types';
import { EmptyState, AnimatedNumber, KosdaqStatusBanner, TipText, ViewingHistoryBanner, FilterIndicator, AnalysisSkeleton } from '@/components/common';
import { SignalSummary, SignalBadge } from '@/components/signal';
import { MarketTabs, NewsAnalysisSection, CriteriaLegend, RecentChanges } from '@/components/stock';
import { CriteriaIndicator } from '@/components/stock/CriteriaIndicator';
import { NewsSection } from '@/components/news';
import { useUIStore } from '@/store/uiStore';
import { useAuthStore } from '@/store/authStore';
import { WarningDot } from '@/components/stock/WarningDot';
import { cn, getWarningRingClass } from '@/lib/utils';
import { matchStock } from '@/lib/koreanSearch';

// 숫자 포맷
function formatNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return '-';
  return num.toLocaleString();
}

function formatPercent(num: number | null | undefined): string {
  if (num === null || num === undefined) return '-';
  const sign = num > 0 ? '+' : '';
  return `${sign}${num.toFixed(2)}%`;
}

// 투자자 동향 뱃지
function FlowBadge({ value, label, isEstimated }: { value: number | null | undefined; label: string; isEstimated?: boolean }) {
  // null이면 추정 모드에서 개인 데이터 없음
  if (value === null && isEstimated) {
    return (
      <span className="inline-flex items-center px-1.5 md:px-2 py-0.5 rounded text-[0.75rem] md:text-xs font-medium bg-gray-100 text-gray-400">
        {label}: 추정불가
      </span>
    );
  }

  if (value === null || value === undefined) return null;

  // 값이 0이고 추정 모드가 아니면 "장중" 표시
  if (value === 0 && !isEstimated) {
    return (
      <span className="inline-flex items-center px-1.5 md:px-2 py-0.5 rounded text-[0.75rem] md:text-xs font-medium bg-gray-100 text-gray-500">
        {label}: 장중
      </span>
    );
  }

  const isPositive = value > 0;
  // 추정 데이터는 amber 계열 배경
  const bgColor = isEstimated
    ? (isPositive ? 'bg-amber-100 text-amber-800' : 'bg-amber-50 text-amber-700')
    : (isPositive ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700');
  // 모바일에서는 숫자를 간략화
  const displayValue = Math.abs(value) >= 10000
    ? `${(value / 10000).toFixed(0)}만`
    : formatNumber(value);
  const estimateLabel = isEstimated ? '(추정)' : '';
  return (
    <span className={`inline-flex items-center px-1.5 md:px-2 py-0.5 rounded text-[0.75rem] md:text-xs font-medium ${bgColor}`}>
      {label}: {isPositive ? '+' : ''}{displayValue}{estimateLabel}
    </span>
  );
}

// 데이터 제공 현황 안내 컴포넌트
function DataAvailabilityNotice() {
  return (
    <div className="mb-5 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl overflow-hidden">
      <div className="px-3 md:px-4 py-2 md:py-2.5 bg-blue-100/50 border-b border-blue-200">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-blue-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 16v-4M12 8h.01"/>
          </svg>
          <span className="text-xs md:text-sm font-semibold text-blue-800">KIS API 데이터 제공 현황</span>
        </div>
      </div>
      <div className="px-3 md:px-4 py-2.5 md:py-3">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 md:gap-3 text-[0.75rem] md:text-xs">
          <div className="flex items-start gap-2">
            <span className="text-green-500 font-bold mt-0.5">✓</span>
            <div>
              <span className="font-medium text-gray-700">장중 실시간 제공</span>
              <p className="text-gray-500 mt-0.5">현재가, 등락률, 거래량, 거래대금, 호가</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-amber-500 font-bold mt-0.5">!</span>
            <div>
              <span className="font-medium text-gray-700">장 마감 후 확정</span>
              <p className="text-gray-500 mt-0.5">외인/기관/개인 순매수 (장중 "장중" 표시)</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-amber-500 font-bold mt-0.5">~</span>
            <div>
              <span className="font-medium text-gray-700">장중 추정 제공</span>
              <p className="text-gray-500 mt-0.5">외인/기관 추정 순매수 (장중 실시간 추정치)</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// 개별 종목 카드
function StockCard({
  stock,
  analysis,
  isExpanded,
  onToggle,
  criteria
}: {
  stock: KISStockData;
  analysis?: KISAnalysisResult;
  isExpanded: boolean;
  onToggle: () => void;
  criteria?: StockCriteria | null;
}) {
  const changeRate = stock.price?.change_rate_pct ?? 0;
  const priceChangeColor = changeRate > 0 ? 'text-red-500' : changeRate < 0 ? 'text-blue-500' : 'text-text-secondary';

  return (
    <div className={cn(
      'relative bg-bg-secondary border border-border rounded-xl p-3 md:p-4 hover:border-accent-primary transition-all',
      getWarningRingClass(criteria),
    )}>
      <WarningDot criteria={criteria} />
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
            <span className={`text-[0.75rem] md:text-xs px-1 md:px-1.5 py-0.5 rounded flex-shrink-0 ${stock.market === 'KOSPI' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'}`}>
              {stock.market}
            </span>
          </div>
          <div className="flex items-baseline gap-1.5 md:gap-2">
            <span className="text-base md:text-lg font-bold">{formatNumber(stock.price?.current)}원</span>
            <span className={`text-xs md:text-sm font-medium ${priceChangeColor}`}>
              {formatPercent(stock.price?.change_rate_pct)}
            </span>
          </div>
        </div>
        <div className="text-right flex-shrink-0 ml-2">
          {analysis ? (
            <SignalBadge signal={analysis.signal} />
          ) : (
            <span className="inline-block text-[0.75rem] md:text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-400 font-medium">
              AI 분석 실패
            </span>
          )}
          <div className="text-[0.75rem] md:text-xs text-text-muted mt-1">
            #{stock.ranking?.volume_rank ?? '-'}위
          </div>
        </div>
      </div>

      {/* 핵심 지표 */}
      <div className="grid grid-cols-4 gap-1 md:gap-2 mb-2 md:mb-3 text-[0.75rem] md:text-xs">
        <div className="bg-bg-primary rounded-lg p-1.5 md:p-2 text-center">
          <div className="text-text-muted mb-0.5">PER</div>
          <div className="font-medium">{stock.valuation?.per && stock.valuation.per > 0 ? stock.valuation.per.toFixed(1) : '-'}</div>
        </div>
        <div className="bg-bg-primary rounded-lg p-1.5 md:p-2 text-center">
          <div className="text-text-muted mb-0.5">PBR</div>
          <div className="font-medium">{stock.valuation?.pbr && stock.valuation.pbr > 0 ? stock.valuation.pbr.toFixed(2) : '-'}</div>
        </div>
        <div className="bg-bg-primary rounded-lg p-1.5 md:p-2 text-center">
          <div className="text-text-muted mb-0.5">거래량</div>
          <div className="font-medium text-amber-600">+{stock.ranking?.volume_rate_vs_prev?.toFixed(0) ?? '-'}%</div>
        </div>
        <div className="bg-bg-primary rounded-lg p-1.5 md:p-2 text-center">
          <div className="text-text-muted mb-0.5">52주</div>
          <div className="font-medium">
            {stock.price?.high_52week ? ((stock.price.current / stock.price.high_52week) * 100).toFixed(0) : '-'}%
          </div>
        </div>
      </div>

      {/* 투자자 동향 */}
      <div className="flex flex-wrap gap-1 mb-2 md:mb-3">
        <FlowBadge value={stock.investor_flow?.today?.foreign_net} label="외인" isEstimated={stock.investor_flow?.is_estimated} />
        <FlowBadge value={stock.investor_flow?.today?.institution_net} label="기관" isEstimated={stock.investor_flow?.is_estimated} />
        <FlowBadge value={stock.investor_flow?.today?.individual_net} label="개인" isEstimated={stock.investor_flow?.is_estimated} />
      </div>

      {/* 최근 6일 등락률 */}
      {stock.recent_changes && stock.recent_changes.length > 0 && (
        <div className="mb-2 md:mb-3">
          <RecentChanges changes={stock.recent_changes} />
        </div>
      )}

      {/* Criteria 인디케이터 */}
      {criteria && (
        <>
          <CriteriaIndicator criteria={criteria} />
          {criteria.short_selling_alert?.met && (
            <span className="text-[11px] text-red-600 font-medium">
              공매도 주의 ({criteria.short_selling_alert.reason})
            </span>
          )}
          {criteria.overheating_alert?.met && (
            <span className="text-[11px] text-orange-600 font-medium">
              과열 주의 ({criteria.overheating_alert.reason})
            </span>
          )}
          {criteria.reverse_ma_alert?.met && (
            <span className="text-[11px] text-violet-600 font-medium">
              역배열 주의 ({criteria.reverse_ma_alert.reason})
            </span>
          )}
        </>
      )}

      {/* 분석 근거 (있는 경우) */}
      {analysis && (
        <div
          className="cursor-pointer"
          onClick={onToggle}
        >
          <div className="flex items-center justify-between text-[0.75rem] md:text-xs text-text-muted mb-1">
            <span>AI 분석 근거</span>
            <span className="transition-transform duration-200" style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
          </div>
          <div
            className={`overflow-hidden transition-all duration-300 ease-in-out ${isExpanded ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}
          >
            <div className="bg-bg-primary rounded-lg p-2 md:p-3 text-xs md:text-sm">
              <p className="text-text-secondary mb-2">{analysis.reason}</p>
              {analysis.key_factors && (
                <div className="grid grid-cols-2 gap-1.5 md:gap-2 text-[0.75rem] md:text-xs">
                  <div><span className="text-text-muted">추세:</span> {analysis.key_factors.price_trend}</div>
                  <div><span className="text-text-muted">거래량:</span> {analysis.key_factors.volume_signal}</div>
                  <div><span className="text-text-muted">외인:</span> {analysis.key_factors.foreign_flow}</div>
                  <div><span className="text-text-muted">밸류:</span> {analysis.key_factors.valuation}</div>
                </div>
              )}
              {analysis.confidence != null && (
                <div className="mt-2 text-[0.75rem] md:text-xs text-text-muted">
                  신뢰도: {((analysis.confidence ?? 0) * 100).toFixed(0)}% | 위험도: {analysis.risk_level || '-'}
                </div>
              )}
              <NewsAnalysisSection newsAnalysis={analysis.news_analysis} />
            </div>
          </div>
        </div>
      )}

      {/* 뉴스 섹션 */}
      <div className="md:hidden">
        <NewsSection news={analysis?.news} isMobile={true} />
      </div>
      <div className="hidden md:block">
        <NewsSection news={analysis?.news} isMobile={false} />
      </div>
    </div>
  );
}

// 결과 메타 정보
function ResultsMeta({ analysisTime, totalStocks, analyzedCount }: {
  analysisTime: string;
  totalStocks: number;
  analyzedCount: number;
}) {
  const dateOnly = analysisTime?.slice(0, 10) || '-';
  const timeOnly = analysisTime?.slice(11, 19) || '';

  return (
    <div className="grid grid-cols-3 gap-2 md:gap-3 mb-5">
      <div className="bg-bg-secondary border border-border rounded-xl px-3 py-2.5 md:px-4 md:py-3 flex items-center gap-2 md:gap-3 shadow-sm">
        <div className="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 md:w-5 md:h-5 text-blue-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[0.75rem] md:text-xs text-text-muted uppercase tracking-wide font-semibold">
            분석 일시
          </div>
          <div className="text-xs md:text-base font-bold text-text-primary">
            {dateOnly}
          </div>
          {timeOnly && (
            <div className="text-[0.75rem] md:text-xs text-text-muted font-medium">{timeOnly}</div>
          )}
        </div>
      </div>
      <div className="bg-bg-secondary border border-border rounded-xl px-3 py-2.5 md:px-4 md:py-3 flex items-center gap-2 md:gap-3 shadow-sm">
        <div className="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-emerald-100 flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 md:w-5 md:h-5 text-emerald-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
          </svg>
        </div>
        <div className="min-w-0">
          <div className="text-[0.75rem] md:text-xs text-text-muted uppercase tracking-wide font-semibold">
            수집 종목
          </div>
          <div className="text-xs md:text-base font-bold text-text-primary"><AnimatedNumber value={totalStocks} duration={500} />개</div>
        </div>
      </div>
      <div className="bg-bg-secondary border border-border rounded-xl px-3 py-2.5 md:px-4 md:py-3 flex items-center gap-2 md:gap-3 shadow-sm">
        <div className="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-purple-100 flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 md:w-5 md:h-5 text-purple-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 8V4H8"/><rect x="2" y="8" width="20" height="12" rx="2"/><path d="M6 12h.01M10 12h.01"/><path d="M14 16h4"/>
          </svg>
        </div>
        <div className="min-w-0">
          <div className="text-[0.75rem] md:text-xs text-text-muted uppercase tracking-wide font-semibold">
            AI 분석
          </div>
          <div className="text-xs md:text-base font-bold text-text-primary"><AnimatedNumber value={analyzedCount} duration={500} />개</div>
        </div>
      </div>
    </div>
  );
}

export function APIAnalysis() {
  const [marketFilter, setMarketFilter] = useState<MarketType>('all');
  const [signalFilter, setSignalFilter] = useState<SignalType | null>(null);
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<'volume_rank' | 'change_rate' | 'signal'>('volume_rank');
  const { isViewingHistory, viewingHistoryDateTime, isCompactView, searchQuery } = useUIStore();
  const { data: criteriaData } = useCriteriaData();
  const isAdmin = useAuthStore((s) => s.isAdmin);

  // viewingHistoryDateTime: "2026-02-04_0700" → filename: "kis_2026-02-04_0700.json"
  const historyFilename = viewingHistoryDateTime ? `kis_${viewingHistoryDateTime}.json` : null;

  // 필터 변경 시 확장된 카드 초기화
  useEffect(() => {
    setExpandedCards(new Set());
  }, [marketFilter, signalFilter]);

  // KIS 데이터 로드 (최신)
  const { data: latestKisData, isLoading: isLoadingLatestKIS } = useQuery({
    queryKey: ['kis-data'],
    queryFn: fetchKISData,
  });

  // 분석 결과 로드 (최신)
  const { data: latestAnalysisData, isLoading: isLoadingLatestAnalysis } = useQuery({
    queryKey: ['kis-analysis'],
    queryFn: fetchKISAnalysis,
  });

  // 히스토리 데이터 로드
  const { data: historyData, isLoading: isLoadingHistory } = useKISHistoryData(
    isViewingHistory ? historyFilename : null
  );

  // 실제 사용할 데이터 선택
  // 히스토리 모드에서는 KIS 분석 결과만 사용 (kis_gemini.json은 히스토리 저장 안 함)
  const analysisData: KISAnalysisData | null | undefined = isViewingHistory ? historyData : latestAnalysisData;
  const kisData = isViewingHistory ? null : latestKisData; // 히스토리에서는 주가 데이터 없음
  const isLoading = isViewingHistory ? isLoadingHistory : (isLoadingLatestKIS || isLoadingLatestAnalysis);

  // 분석 결과를 코드별 맵으로 변환
  const analysisMap = useMemo(() => {
    if (!analysisData?.results) return {};
    return analysisData.results.reduce((acc, item) => {
      acc[item.code] = item;
      return acc;
    }, {} as Record<string, KISAnalysisResult>);
  }, [analysisData]);

  // 필터링된 종목 리스트
  const filteredStocks = useMemo(() => {
    // 히스토리 모드에서는 분석 결과만 표시
    if (isViewingHistory) {
      if (!analysisData?.results) return [];
      let results = [...analysisData.results];

      // 시장 필터
      if (marketFilter !== 'all') {
        results = results.filter(r => r.market?.toLowerCase() === marketFilter);
      }

      // 시그널 필터
      if (signalFilter) {
        results = results.filter(r => r.signal === signalFilter);
      }

      // 검색 필터
      if (searchQuery) {
        results = results.filter(r => matchStock(searchQuery, r.name, r.code));
      }

      return results;
    }

    // 최신 데이터 모드
    if (!kisData?.stocks) return [];

    let stocks = Object.values(kisData.stocks);

    // 시장 필터
    if (marketFilter !== 'all') {
      stocks = stocks.filter(s => s.market.toLowerCase() === marketFilter);
    }

    // 시그널 필터
    if (signalFilter) {
      stocks = stocks.filter(s => {
        const analysis = analysisMap[s.code];
        return analysis?.signal === signalFilter;
      });
    }

    // 검색 필터
    if (searchQuery) {
      stocks = stocks.filter(s => matchStock(searchQuery, s.name, s.code));
    }

    // 정렬
    const signalOrder: Record<string, number> = { '적극매수': 0, '매수': 1, '중립': 2, '매도': 3, '적극매도': 4 };
    if (sortBy === 'change_rate') {
      return stocks.sort((a, b) => (b.price?.change_rate_pct ?? 0) - (a.price?.change_rate_pct ?? 0));
    } else if (sortBy === 'signal') {
      return stocks.sort((a, b) => (signalOrder[analysisMap[a.code]?.signal ?? '중립'] ?? 2) - (signalOrder[analysisMap[b.code]?.signal ?? '중립'] ?? 2));
    }
    return stocks.sort((a, b) => (a.ranking.volume_rank || 999) - (b.ranking.volume_rank || 999));
  }, [kisData, analysisData, isViewingHistory, marketFilter, signalFilter, analysisMap, searchQuery, sortBy]);

  // 시그널 카운트 (SignalCounts 타입에 맞춤)
  const signalCounts: SignalCounts = useMemo(() => {
    const counts: SignalCounts = {
      '적극매수': 0, '매수': 0, '중립': 0, '매도': 0, '적극매도': 0
    };
    if (analysisData?.results) {
      analysisData.results.forEach(r => {
        if (counts[r.signal] !== undefined) {
          counts[r.signal]++;
        }
      });
    }
    return counts;
  }, [analysisData]);

  // 시장별 카운트
  const marketCounts = useMemo(() => {
    if (isViewingHistory) {
      if (!analysisData?.results) return { all: 0, kospi: 0, kosdaq: 0 };
      const results = analysisData.results;
      return {
        all: results.length,
        kospi: results.filter(r => r.market === 'KOSPI').length,
        kosdaq: results.filter(r => r.market === 'KOSDAQ').length,
      };
    }

    if (!kisData?.stocks) return { all: 0, kospi: 0, kosdaq: 0 };
    const stocks = Object.values(kisData.stocks);
    return {
      all: stocks.length,
      kospi: stocks.filter(s => s.market === 'KOSPI').length,
      kosdaq: stocks.filter(s => s.market === 'KOSDAQ').length,
    };
  }, [kisData, analysisData, isViewingHistory]);

  // 카드 확장/축소 토글
  const toggleCard = (code: string) => {
    setExpandedCards(prev => {
      const next = new Set(prev);
      if (next.has(code)) {
        next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  };

  // 시그널 필터 토글
  const handleSignalFilter = (signal: SignalType) => {
    setSignalFilter(prev => prev === signal ? null : signal);
  };

  if (isLoading) {
    return (
      <section id="api-analysis" className="mb-10">
        <AnalysisSkeleton />
      </section>
    );
  }

  // 히스토리 모드에서 데이터 없음
  if (isViewingHistory && !analysisData) {
    return (
      <section id="api-analysis" className="mb-10">
        <div className="flex justify-between items-center mb-4 md:mb-5 flex-wrap gap-2 md:gap-3">
          <div className="flex-1 min-w-0">
            <h2 className="text-lg md:text-xl font-bold text-text-primary mb-0.5 md:mb-1">한국투자증권 API 분석</h2>
            <p className="text-xs md:text-sm text-text-muted">실시간 API 기반 주식 데이터 분석</p>
          </div>
        </div>
        {isViewingHistory && viewingHistoryDateTime && <ViewingHistoryBanner dateTime={viewingHistoryDateTime} />}
        <EmptyState
          icon="📡"
          title="해당 시점의 KIS 분석 데이터가 없습니다"
          description="이 시점에는 KIS API 분석이 실행되지 않았습니다."
        />
      </section>
    );
  }

  // 최신 모드에서 데이터 없음
  if (!isViewingHistory && !kisData) {
    return (
      <section id="api-analysis" className="mb-10">
        <EmptyState
          icon="📡"
          title="KIS API 데이터가 아직 없습니다"
          description="한국투자증권 API 연동이 설정되지 않았거나, 아직 데이터가 수집되지 않았습니다. GitHub Secrets에 KIS_APP_KEY, KIS_APP_SECRET을 설정한 후 워크플로우를 실행해주세요."
        />
      </section>
    );
  }

  const hasAnalysis = analysisData && analysisData.results.length > 0;
  const totalStocks = isViewingHistory ? (analysisData?.total_analyzed || 0) : (kisData?.meta.total_stocks || 0);

  return (
    <section id="api-analysis" className="mb-10">
      {/* 헤더 */}
      <div className="flex justify-between items-center mb-4 md:mb-5 flex-wrap gap-2 md:gap-3">
        <div className="flex-1 min-w-0">
          <h2 className="text-lg md:text-xl font-bold text-text-primary mb-0.5 md:mb-1">한국투자증권 API 분석</h2>
          <p className="text-xs md:text-sm text-text-muted">실시간 API 기반 주식 데이터 분석</p>
        </div>
      </div>

      {/* 히스토리 배너 */}
      {isViewingHistory && viewingHistoryDateTime && (
        <ViewingHistoryBanner dateTime={viewingHistoryDateTime} />
      )}

      <KosdaqStatusBanner />

      {/* 메타 정보 */}
      <ResultsMeta
        analysisTime={analysisData?.analysis_time || kisData?.meta.original_collected_at || ''}
        totalStocks={totalStocks}
        analyzedCount={analysisData?.total_analyzed || 0}
      />

      {/* 데이터 제공 현황 안내 - 최신 모드에서만 */}
      {!isViewingHistory && <DataAvailabilityNotice />}

      {/* 시그널 요약 - Vision AI와 동일한 컴포넌트 사용 */}
      {hasAnalysis && (
        <>
          <SignalSummary
            counts={signalCounts}
            activeSignal={signalFilter}
            onFilter={handleSignalFilter}
          />
          <CriteriaLegend isAdmin={isAdmin} hasCriteriaData={!!criteriaData} />
          <TipText id="api-signal-filter">
            시그널 카드를 클릭하면 필터가 적용되어, 해당되는 종목만 확인 가능합니다
          </TipText>
        </>
      )}

      {!hasAnalysis && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-5">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🤖</span>
            <div>
              <div className="font-medium text-amber-800">AI 분석 대기 중</div>
              <div className="text-sm text-amber-600">
                수집된 데이터에 대한 Gemini AI 분석이 아직 실행되지 않았습니다.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 시장 탭 */}
      <MarketTabs
        active={marketFilter}
        counts={marketCounts}
        onChange={setMarketFilter}
      />

      {/* 정렬 + 필터 인디케이터 */}
      <div className="flex items-center justify-between mb-2">
        <FilterIndicator
          signal={signalFilter}
          onClear={() => setSignalFilter(null)}
        />
        {!isViewingHistory && (
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="text-xs bg-bg-secondary border border-border rounded-lg px-2 py-1 text-text-secondary"
          >
            <option value="volume_rank">거래량 순위</option>
            <option value="change_rate">등락률</option>
            <option value="signal">시그널</option>
          </select>
        )}
      </div>

      {/* 종목 그리드 */}
      {filteredStocks.length > 0 ? (
        <>
          {!isCompactView && (
            <>
              <TipText id="api-stock-link">
                종목명을 클릭하면 네이버 금융으로 이동합니다
              </TipText>
              <div className="flex justify-end gap-2 mb-2">
                <button
                  onClick={() => {
                    const allCodes = new Set(
                      isViewingHistory
                        ? (filteredStocks as KISAnalysisResult[]).map(a => a.code)
                        : (filteredStocks as KISStockData[]).map(s => s.code)
                    );
                    setExpandedCards(allCodes);
                  }}
                  className="px-2.5 py-1 text-xs font-medium text-text-muted hover:text-text-secondary bg-bg-secondary hover:bg-bg-primary border border-border rounded-lg transition-all"
                >
                  전체 펼치기
                </button>
                <button
                  onClick={() => setExpandedCards(new Set())}
                  className="px-2.5 py-1 text-xs font-medium text-text-muted hover:text-text-secondary bg-bg-secondary hover:bg-bg-primary border border-border rounded-lg transition-all"
                >
                  전체 접기
                </button>
              </div>
            </>
          )}
          {isCompactView ? (
            // Compact 보기
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
              {isViewingHistory ? (
                (filteredStocks as KISAnalysisResult[]).map(analysis => (
                  <a
                    key={analysis.code}
                    href={`https://m.stock.naver.com/domestic/stock/${analysis.code}/total`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={cn(
                      'relative flex items-center justify-between gap-2 px-3 py-2 bg-bg-secondary border border-border rounded-lg hover:border-accent-primary transition-all no-underline',
                      isAdmin && getWarningRingClass(criteriaData?.[analysis.code]),
                    )}
                  >
                    {isAdmin && <WarningDot criteria={criteriaData?.[analysis.code]} />}
                    <div className="min-w-0 flex-1">
                      <div className="font-medium text-sm text-text-primary truncate">{analysis.name}</div>
                      <div className="text-xs text-text-muted font-mono">{analysis.code}</div>
                      {isAdmin && criteriaData?.[analysis.code] && (
                        <CriteriaIndicator criteria={criteriaData[analysis.code]} isCompact />
                      )}
                    </div>
                    <SignalBadge signal={analysis.signal} size="sm" />
                  </a>
                ))
              ) : (
                (filteredStocks as KISStockData[]).map(stock => (
                  <a
                    key={stock.code}
                    href={`https://m.stock.naver.com/domestic/stock/${stock.code}/total`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={cn(
                      'relative flex items-center justify-between gap-2 px-3 py-2 bg-bg-secondary border border-border rounded-lg hover:border-accent-primary transition-all no-underline',
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
                    {analysisMap[stock.code] && (
                      <SignalBadge signal={analysisMap[stock.code].signal} size="sm" />
                    )}
                  </a>
                ))
              )}
            </div>
          ) : (
            // 일반 보기
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 md:gap-4 items-start">
              {isViewingHistory ? (
                // 히스토리 모드: 분석 결과만 표시
                (filteredStocks as KISAnalysisResult[]).map(analysis => (
                  <HistoryStockCard
                    key={analysis.code}
                    analysis={analysis}
                    isExpanded={expandedCards.has(analysis.code)}
                    onToggle={() => toggleCard(analysis.code)}
                    criteria={isAdmin ? criteriaData?.[analysis.code] ?? null : null}
                  />
                ))
              ) : (
                // 최신 모드: 주가 데이터 + 분석 결과
                (filteredStocks as KISStockData[]).map(stock => (
                  <StockCard
                    key={stock.code}
                    stock={stock}
                    analysis={analysisMap[stock.code]}
                    isExpanded={expandedCards.has(stock.code)}
                    onToggle={() => toggleCard(stock.code)}
                    criteria={isAdmin ? criteriaData?.[stock.code] ?? null : null}
                  />
                ))
              )}
            </div>
          )}
        </>
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

// 히스토리 모드 전용 카드 (주가 데이터 없이 분석 결과만)
function HistoryStockCard({
  analysis,
  isExpanded,
  onToggle,
  criteria
}: {
  analysis: KISAnalysisResult;
  isExpanded: boolean;
  onToggle: () => void;
  criteria?: StockCriteria | null;
}) {
  const changeRate = analysis.change_rate ?? 0;
  const priceChangeColor = changeRate > 0 ? 'text-red-500' : changeRate < 0 ? 'text-blue-500' : 'text-text-secondary';

  return (
    <div className={cn(
      'relative bg-bg-secondary border border-border rounded-xl p-3 md:p-4 hover:border-accent-primary transition-all',
      getWarningRingClass(criteria),
    )}>
      <WarningDot criteria={criteria} />
      {/* 헤더 */}
      <div className="flex justify-between items-start mb-2 md:mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 md:gap-2 mb-1 flex-wrap">
            <a
              href={`https://m.stock.naver.com/domestic/stock/${analysis.code}/total`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-bold text-base md:text-lg text-text-primary hover:text-accent-primary transition-colors truncate"
            >
              {analysis.name}
            </a>
            {analysis.market && (
              <span className={`text-[0.75rem] md:text-xs px-1 md:px-1.5 py-0.5 rounded flex-shrink-0 ${analysis.market === 'KOSPI' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'}`}>
                {analysis.market}
              </span>
            )}
          </div>
          {analysis.current_price != null && (
            <div className="flex items-baseline gap-1.5 md:gap-2">
              <span className="text-base md:text-lg font-bold">{analysis.current_price.toLocaleString()}원</span>
              <span className={`text-xs md:text-sm font-medium ${priceChangeColor}`}>
                {changeRate > 0 ? '+' : ''}{changeRate.toFixed(2)}%
              </span>
            </div>
          )}
        </div>
        <div className="text-right flex-shrink-0 ml-2">
          <SignalBadge signal={analysis.signal} />
        </div>
      </div>

      {/* Criteria 인디케이터 */}
      {criteria && (
        <>
          <CriteriaIndicator criteria={criteria} />
          {criteria.short_selling_alert?.met && (
            <span className="text-[11px] text-red-600 font-medium">
              공매도 주의 ({criteria.short_selling_alert.reason})
            </span>
          )}
          {criteria.overheating_alert?.met && (
            <span className="text-[11px] text-orange-600 font-medium">
              과열 주의 ({criteria.overheating_alert.reason})
            </span>
          )}
          {criteria.reverse_ma_alert?.met && (
            <span className="text-[11px] text-violet-600 font-medium">
              역배열 주의 ({criteria.reverse_ma_alert.reason})
            </span>
          )}
        </>
      )}

      {/* 분석 근거 */}
      <div
        className="cursor-pointer"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between text-[0.75rem] md:text-xs text-text-muted mb-1">
          <span>AI 분석 근거</span>
          <span className="transition-transform duration-200" style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
        </div>
        <div
          className={`overflow-hidden transition-all duration-300 ease-in-out ${isExpanded ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}
        >
          <div className="bg-bg-primary rounded-lg p-2 md:p-3 text-xs md:text-sm">
            <p className="text-text-secondary mb-2">{analysis.reason}</p>
            {analysis.key_factors && (
              <div className="grid grid-cols-2 gap-1.5 md:gap-2 text-[0.75rem] md:text-xs">
                <div><span className="text-text-muted">추세:</span> {analysis.key_factors.price_trend}</div>
                <div><span className="text-text-muted">거래량:</span> {analysis.key_factors.volume_signal}</div>
                <div><span className="text-text-muted">외인:</span> {analysis.key_factors.foreign_flow}</div>
                <div><span className="text-text-muted">밸류:</span> {analysis.key_factors.valuation}</div>
              </div>
            )}
            {analysis.confidence != null && (
              <div className="mt-2 text-[0.75rem] md:text-xs text-text-muted">
                신뢰도: {((analysis.confidence ?? 0) * 100).toFixed(0)}% | 위험도: {analysis.risk_level || '-'}
              </div>
            )}
            <NewsAnalysisSection newsAnalysis={analysis.news_analysis} />
          </div>
        </div>
      </div>

      {/* 뉴스 섹션 */}
      <div className="md:hidden">
        <NewsSection news={analysis?.news} isMobile={true} />
      </div>
      <div className="hidden md:block">
        <NewsSection news={analysis?.news} isMobile={false} />
      </div>
    </div>
  );
}
