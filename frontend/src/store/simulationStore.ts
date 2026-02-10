import { create } from 'zustand';
import type { SimulationCategory } from '@/services/types';

// 제외 키 형식: "date:category:code"
function stockKey(date: string, category: SimulationCategory, code: string) {
  return `${date}:${category}:${code}`;
}

interface SimulationStore {
  // 카테고리 토글
  activeCategories: Set<SimulationCategory>;

  // 개별 종목 제외 ("date:category:code" 형태)
  excludedStocks: Set<string>;

  // 선택된 날짜들
  selectedDates: Set<string>;

  // 상세보기 활성 날짜
  activeDetailDate: string | null;

  // Actions
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
}

export const useSimulationStore = create<SimulationStore>((set, get) => ({
  activeCategories: new Set<SimulationCategory>(['vision', 'kis', 'combined']),
  excludedStocks: new Set<string>(),
  selectedDates: new Set<string>(),
  activeDetailDate: null,

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
}));

export { stockKey };
