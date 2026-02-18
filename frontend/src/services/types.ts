export type SignalType = '적극매수' | '매수' | '중립' | '매도' | '적극매도';

export type MarketType = 'all' | 'kospi' | 'kosdaq';

export type AnalysisTab = 'vision' | 'api' | 'combined';

// 뉴스 아이템 타입
export interface NewsItem {
  title: string;
  link: string;
  description: string;
  pubDate: string;
  originallink?: string;
}

// AI 재료분석 결과 타입
export interface NewsAnalysis {
  sentiment: string;      // "긍정" | "중립" | "부정"
  key_news: string[];     // 주요 뉴스 1줄 요약 리스트
  catalyst: string;       // 핵심 재료 요약
}

export interface StockResult {
  code: string;
  name: string;
  market?: string;  // 코스피/코스닥
  current_price?: number;
  change_rate?: number;
  signal: SignalType;
  reason: string;
  key_factors?: {
    price_trend: string;
    volume_signal: string;
    foreign_flow: string;
    institution_flow: string;
    valuation: string;
  };
  risk_level?: string;
  confidence?: number;
  capture_time?: string;
  analysis_time?: string;
  news?: NewsItem[];
  news_analysis?: NewsAnalysis;
}

export interface AnalysisData {
  date: string;
  total_stocks: number;
  results: StockResult[];
}

export interface HistoryItem {
  date: string;
  time?: string;  // KIS 히스토리용 (HHMM 형식)
  filename: string;
  total_stocks: number;
  signals: Record<SignalType, number>;
}

export interface HistoryIndex {
  last_updated: string;
  total_records: number;
  retention_days: number;
  history: HistoryItem[];
}

export interface SignalCounts {
  적극매수: number;
  매수: number;
  중립: number;
  매도: number;
  적극매도: number;
}

// KIS API 데이터 타입
export interface KISStockData {
  code: string;
  name: string;
  market: 'KOSPI' | 'KOSDAQ';
  ranking: {
    volume_rank: number;
    volume: number;
    volume_rate_vs_prev: number;
    trading_value: number;
  };
  price: {
    current: number;
    change: number;
    change_rate_pct: number;
    open: number;
    high: number;
    low: number;
    prev_close: number;
    high_52week: number;
    low_52week: number;
  };
  valuation: {
    per: number;
    pbr: number;
    eps: number;
    bps: number;
  };
  investor_flow: {
    is_estimated?: boolean;
    today: {
      foreign_net: number | null;
      institution_net: number | null;
      individual_net: number | null;
    };
    sum_5_days: {
      foreign_net: number;
      institution_net: number;
      individual_net: number;
    };
  };
}

export interface KISGeminiData {
  meta: {
    format_version: string;
    original_collected_at: string;
    transformed_at: string;
    total_stocks: number;
    kospi_count: number;
    kosdaq_count: number;
  };
  stocks: Record<string, KISStockData>;
}

export interface KISAnalysisResult {
  code: string;
  name: string;
  market: string;
  current_price: number;
  change_rate: number;
  signal: SignalType;
  reason: string;
  key_factors?: {
    price_trend: string;
    volume_signal: string;
    foreign_flow: string;
    institution_flow: string;
    valuation: string;
  };
  risk_level?: string;
  confidence?: number;
  analysis_time?: string;
  news?: NewsItem[];
  news_analysis?: NewsAnalysis;
}

export interface KISAnalysisData {
  analysis_time: string;
  total_analyzed: number;
  results: KISAnalysisResult[];
}

// 기준 평가 결과 (단일)
export interface CriterionResult {
  met: boolean;
  reason?: string | null;
  is_52w_high?: boolean;
  had_limit_up?: boolean;
  had_15pct_rise?: boolean;
  ma_values?: Record<string, number | null>;
}

// 종목별 전체 평가 결과
export interface StockCriteria {
  high_breakout: CriterionResult;
  momentum_history: CriterionResult;
  resistance_breakout: CriterionResult;
  ma_alignment: CriterionResult;
  supply_demand: CriterionResult;
  program_trading: CriterionResult;
  top30_trading_value: CriterionResult;
  all_met: boolean;
}

// Combined 분석 타입
export type MatchStatus = 'match' | 'partial' | 'mismatch' | 'vision-only' | 'api-only';

export interface CombinedStock {
  code: string;
  name: string;
  market: 'KOSPI' | 'KOSDAQ' | 'UNKNOWN';
  vision_signal: SignalType | null;
  vision_reason: string | null;
  vision_news: NewsItem[];
  api_signal: SignalType | null;
  api_reason: string | null;
  api_news: NewsItem[];
  api_data: {
    price?: {
      current: number;
      change_rate_pct: number;
    };
    ranking?: {
      volume_rank: number;
    };
    valuation?: {
      per: number;
      pbr: number;
    };
  } | null;
  vision_news_analysis?: NewsAnalysis;
  api_news_analysis?: NewsAnalysis;
  api_key_factors?: {
    price_trend: string;
    volume_signal: string;
    foreign_flow: string;
    institution_flow: string;
    valuation: string;
  };
  api_risk_level?: string;
  api_confidence?: number;
  match_status: MatchStatus;
  confidence: number;
}

export interface CombinedAnalysisStats {
  total: number;
  match: number;
  partial: number;
  mismatch: number;
  vision_only: number;
  api_only: number;
  avg_confidence: number;
}

export interface CombinedAnalysisData {
  generated_at: string;
  date: string;
  time: string;
  stats: CombinedAnalysisStats;
  signal_counts: Record<SignalType, number>;
  stocks: CombinedStock[];
  source: {
    vision: string | null;
    kis_analysis: string | null;
  };
  criteria_data?: Record<string, StockCriteria> | null;
}

// 모의투자 시뮬레이션 타입
export interface SimulationStock {
  code: string;
  name: string;
  market: string;
  open_price: number | null;
  close_price: number | null;
  high_price: number | null;
  return_pct: number | null;
  high_return_pct: number | null;
}

export type SimulationCategory = 'vision' | 'kis' | 'combined';

export interface SimulationPriceEntry {
  open_price: number;
  close_price: number | null;
  high_price: number | null;
}

export interface SimulationData {
  date: string;
  collected_at: string;
  categories: Record<SimulationCategory, SimulationStock[]>;
  all_prices?: Record<string, SimulationPriceEntry>;
}

export interface SimulationIndexItem {
  date: string;
  filename: string;
  total_stocks: number;
  category_counts: Record<SimulationCategory, number>;
}

export interface SimulationIndex {
  updated_at: string;
  total_records: number;
  history: SimulationIndexItem[];
}
