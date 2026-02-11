import { useQuery, useQueries } from '@tanstack/react-query';
import { fetchSimulationIndex, fetchSimulationData } from '@/services/api';

/** 오늘 날짜 문자열 (YYYY-MM-DD) */
function getTodayStr(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/** 파일명에 오늘 날짜가 포함되면 2분, 아니면 30분 */
function getStaleTime(filename: string): number {
  const today = getTodayStr();
  return filename.includes(today)
    ? 1000 * 60 * 2   // 2분 (당일 데이터는 가격 갱신 반영)
    : 1000 * 60 * 30;  // 30분 (과거 데이터는 변하지 않으므로)
}

export function useSimulationIndex() {
  return useQuery({
    queryKey: ['simulation', 'index'],
    queryFn: fetchSimulationIndex,
    staleTime: 1000 * 60 * 2, // 2분 (당일 수집 반영)
    retry: 2,
  });
}

export function useSimulationData(filename: string | null) {
  return useQuery({
    queryKey: ['simulation', filename],
    queryFn: () => fetchSimulationData(filename!),
    enabled: !!filename,
    staleTime: filename ? getStaleTime(filename) : 1000 * 60 * 30,
    retry: 2,
  });
}

export function useSimulationMultipleDates(filenames: string[]) {
  return useQueries({
    queries: filenames.map((filename) => ({
      queryKey: ['simulation', filename],
      queryFn: () => fetchSimulationData(filename),
      staleTime: getStaleTime(filename),
      retry: 2,
      enabled: !!filename,
    })),
  });
}
