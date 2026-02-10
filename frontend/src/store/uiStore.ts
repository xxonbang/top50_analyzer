import { create } from 'zustand';
import type { SignalType, MarketType, AnalysisTab } from '@/services/types';

export type PageType = 'home' | 'simulation';

interface ToastState {
  isVisible: boolean;
  message: string;
}

interface UIStore {
  // 현재 페이지
  currentPage: PageType;

  // 현재 활성 탭
  activeTab: AnalysisTab;

  // 필터 상태
  activeMarket: MarketType;
  activeSignal: SignalType | null;

  // 히스토리 (통합 - workflow 회차 기준 동기화)
  isHistoryPanelOpen: boolean;
  isViewingHistory: boolean;
  viewingHistoryDateTime: string | null;  // "2026-02-04_0700" 형식 (날짜_시간)

  // Compact 보기
  isCompactView: boolean;

  // Toast
  toast: ToastState;

  // Actions
  setCurrentPage: (page: PageType) => void;
  setActiveTab: (tab: AnalysisTab) => void;
  setMarketFilter: (market: MarketType) => void;
  setSignalFilter: (signal: SignalType | null) => void;
  toggleSignalFilter: (signal: SignalType) => void;
  clearSignalFilter: () => void;
  openHistoryPanel: () => void;
  closeHistoryPanel: () => void;
  setViewingHistory: (dateTime: string | null) => void;
  resetToLatest: () => void;
  showToast: (message: string, duration?: number) => void;
  hideToast: () => void;
  toggleCompactView: () => void;
}

export const useUIStore = create<UIStore>((set, get) => ({
  currentPage: 'home',
  activeTab: 'vision',
  activeMarket: 'all',
  activeSignal: null,
  isHistoryPanelOpen: false,
  isViewingHistory: false,
  viewingHistoryDateTime: null,
  isCompactView: false,
  toast: { isVisible: false, message: '' },

  setCurrentPage: (page) => set({ currentPage: page }),

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

  openHistoryPanel: () => set({ isHistoryPanelOpen: true }),

  closeHistoryPanel: () => set({ isHistoryPanelOpen: false }),

  // dateTime: "2026-02-04_0700" 형식
  setViewingHistory: (dateTime) => set({
    isViewingHistory: dateTime !== null,
    viewingHistoryDateTime: dateTime,
  }),

  resetToLatest: () => {
    set({
      isViewingHistory: false,
      viewingHistoryDateTime: null,
      isHistoryPanelOpen: false,
      activeMarket: 'all',
      activeSignal: null,
    });
    get().showToast('가장 최신의 데이터를 표시합니다', 2000);
  },

  showToast: (message, duration = 2000) => {
    set({ toast: { isVisible: true, message } });
    setTimeout(() => {
      // message는 유지하고 isVisible만 false로 (애니메이션 중 쪼그라듦 방지)
      set((state) => ({ toast: { ...state.toast, isVisible: false } }));
    }, duration);
  },

  hideToast: () => set((state) => ({ toast: { ...state.toast, isVisible: false } })),

  toggleCompactView: () => set((state) => ({ isCompactView: !state.isCompactView })),
}));
