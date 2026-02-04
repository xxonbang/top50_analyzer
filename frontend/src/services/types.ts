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

export interface StockResult {
  code: string;
  name: string;
  signal: SignalType;
  reason: string;
  capture_time?: string;
  analysis_time?: string;
  news?: NewsItem[];
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
    today: {
      foreign_net: number;
      institution_net: number;
      individual_net: number;
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
}

export interface KISAnalysisData {
  analysis_time: string;
  total_analyzed: number;
  results: KISAnalysisResult[];
}
