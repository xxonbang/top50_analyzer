import { create } from 'zustand';
import type { SimulationCategory } from '@/services/types';

export type SimulationMode = 'close' | 'high';
export type InvestmentMode = 'per_share' | 'equal_amount';

// 제외 키 형식: "date:category:code"
function stockKey(date: string, category: SimulationCategory, code: string) {
  return `${date}:${category}:${code}`;
}

interface SimulationStore {
  // 시뮬레이션 모드 (종가 매도 vs 최고가 매도)
  simulationMode: SimulationMode;

  // 투자 방식 (1주씩 vs 동일 금액)
  investmentMode: InvestmentMode;

  // 카테고리 토글
  activeCategories: Set<SimulationCategory>;

  // 개별 종목 제외 ("date:category:code" 형태)
  excludedStocks: Set<string>;

  // 선택된 날짜들
  selectedDates: Set<string>;

  // 상세보기 활성 날짜
  activeDetailDate: string | null;

  // 분석 시간대 오버라이드 (날짜별 선택된 시간, 예: { "2026-02-11": "2020" })
  analysisTimeOverrides: Record<string, string>;

  // Actions
  setSimulationMode: (mode: SimulationMode) => void;
  setInvestmentMode: (mode: InvestmentMode) => void;

  toggleCategory: (category: SimulationCategory) => void;
  setCategories: (categories: SimulationCategory[]) => void;

  toggleStock: (date: string, category: SimulationCategory, code: string) => void;
  excludeAllStocks: (date: string, category: SimulationCategory, codes: string[]) => void;
  includeAllStocks: (date: string, category: SimulationCategory, codes: string[]) => void;
  isStockExcluded: (date: string, category: SimulationCategory, code: string) => boolean;

  toggleDate: (date: string) => void;
  selectAllDates: (dates: string[]) => void;
  deselectAllDates: () => void;

  setActiveDetailDate: (date: string | null) => void;

  setAnalysisTime: (date: string, time: string | null) => void;

  resetAll: (allDates: string[]) => void;
}

export const useSimulationStore = create<SimulationStore>((set, get) => ({
  simulationMode: 'close' as SimulationMode,
  investmentMode: 'equal_amount' as InvestmentMode,
  activeCategories: new Set<SimulationCategory>(['vision', 'kis', 'combined']),
  excludedStocks: new Set<string>(),
  selectedDates: new Set<string>(),
  activeDetailDate: null,
  analysisTimeOverrides: {},

  setSimulationMode: (mode) => set({ simulationMode: mode }),
  setInvestmentMode: (mode) => set({ investmentMode: mode }),

  toggleCategory: (category) =>
    set((state) => {
      const next = new Set(state.activeCategories);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return { activeCategories: next };
    }),

  setCategories: (categories) =>
    set({ activeCategories: new Set(categories) }),

  toggleStock: (date, category, code) =>
    set((state) => {
      const key = stockKey(date, category, code);
      const next = new Set(state.excludedStocks);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return { excludedStocks: next };
    }),

  excludeAllStocks: (date, category, codes) =>
    set((state) => {
      const next = new Set(state.excludedStocks);
      codes.forEach((code) => next.add(stockKey(date, category, code)));
      return { excludedStocks: next };
    }),

  includeAllStocks: (date, category, codes) =>
    set((state) => {
      const next = new Set(state.excludedStocks);
      codes.forEach((code) => next.delete(stockKey(date, category, code)));
      return { excludedStocks: next };
    }),

  isStockExcluded: (date, category, code) =>
    get().excludedStocks.has(stockKey(date, category, code)),

  toggleDate: (date) =>
    set((state) => {
      const next = new Set(state.selectedDates);
      if (next.has(date)) {
        next.delete(date);
      } else {
        next.add(date);
      }
      const activeDetail = next.has(date) ? date : (next.size > 0 ? [...next].sort().reverse()[0] : null);
      return { selectedDates: next, activeDetailDate: activeDetail };
    }),

  selectAllDates: (dates) =>
    set({
      selectedDates: new Set(dates),
      activeDetailDate: dates.length > 0 ? [...dates].sort().reverse()[0] : null,
    }),

  deselectAllDates: () =>
    set({ selectedDates: new Set(), activeDetailDate: null }),

  setActiveDetailDate: (date) =>
    set({ activeDetailDate: date }),

  resetAll: (allDates) =>
    set({
      simulationMode: 'close' as SimulationMode,
      investmentMode: 'equal_amount' as InvestmentMode,
      activeCategories: new Set<SimulationCategory>(['vision', 'kis', 'combined']),
      excludedStocks: new Set<string>(),
      selectedDates: new Set(allDates),
      activeDetailDate: allDates.length > 0 ? [...allDates].sort().reverse()[0] : null,
      analysisTimeOverrides: {},
    }),

  setAnalysisTime: (date, time) =>
    set((state) => {
      const next = { ...state.analysisTimeOverrides };
      if (time === null) {
        delete next[date];
      } else {
        next[date] = time;
      }
      return { analysisTimeOverrides: next };
    }),
}));

export { stockKey };
