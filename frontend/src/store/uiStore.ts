import { create } from 'zustand';
import type { SignalType, MarketType, AnalysisTab } from '@/services/types';

// 히스토리 타입: vision 또는 kis
export type HistoryType = 'vision' | 'kis';

interface UIStore {
  // 현재 활성 탭
  activeTab: AnalysisTab;

  // 필터 상태
  activeMarket: MarketType;
  activeSignal: SignalType | null;

  // 히스토리
  isHistoryPanelOpen: boolean;
  historyType: HistoryType;  // 어떤 분석의 히스토리인지
  isViewingHistory: boolean;
  viewingHistoryFile: string | null;

  // Actions
  setActiveTab: (tab: AnalysisTab) => void;
  setMarketFilter: (market: MarketType) => void;
  setSignalFilter: (signal: SignalType | null) => void;
  toggleSignalFilter: (signal: SignalType) => void;
  clearSignalFilter: () => void;
  toggleHistoryPanel: () => void;
  openHistoryPanel: (type?: HistoryType) => void;
  closeHistoryPanel: () => void;
  setViewingHistory: (filename: string | null) => void;
  resetToLatest: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  activeTab: 'vision',
  activeMarket: 'all',
  activeSignal: null,
  isHistoryPanelOpen: false,
  historyType: 'vision',
  isViewingHistory: false,
  viewingHistoryFile: null,

  setActiveTab: (tab) => set({ activeTab: tab }),

  setMarketFilter: (market) => set({
    activeMarket: market,
    activeSignal: null // 마켓 변경 시 시그널 필터 초기화
  }),

  setSignalFilter: (signal) => set({ activeSignal: signal }),

  toggleSignalFilter: (signal) => set((state) => ({
    activeSignal: state.activeSignal === signal ? null : signal
  })),

  clearSignalFilter: () => set({ activeSignal: null }),

  toggleHistoryPanel: () => set((state) => ({
    isHistoryPanelOpen: !state.isHistoryPanelOpen
  })),

  openHistoryPanel: (type = 'vision') => set({
    isHistoryPanelOpen: true,
    historyType: type,
  }),

  closeHistoryPanel: () => set({ isHistoryPanelOpen: false }),

  setViewingHistory: (filename) => set({
    isViewingHistory: filename !== null,
    viewingHistoryFile: filename,
  }),

  resetToLatest: () => set({
    isViewingHistory: false,
    viewingHistoryFile: null,
    isHistoryPanelOpen: false,
    activeMarket: 'all',
    activeSignal: null,
  }),
}));
