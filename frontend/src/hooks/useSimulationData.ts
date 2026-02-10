import { useQuery, useQueries } from '@tanstack/react-query';
import { fetchSimulationIndex, fetchSimulationData } from '@/services/api';

export function useSimulationIndex() {
  return useQuery({
    queryKey: ['simulation', 'index'],
    queryFn: fetchSimulationIndex,
    staleTime: 1000 * 60 * 5,
    retry: 2,
  });
}

export function useSimulationData(filename: string | null) {
  return useQuery({
    queryKey: ['simulation', filename],
    queryFn: () => fetchSimulationData(filename!),
    enabled: !!filename,
    staleTime: 1000 * 60 * 30, // 30분 (과거 데이터는 변하지 않으므로)
    retry: 2,
  });
}

export function useSimulationMultipleDates(filenames: string[]) {
  return useQueries({
    queries: filenames.map((filename) => ({
      queryKey: ['simulation', filename],
      queryFn: () => fetchSimulationData(filename),
      staleTime: 1000 * 60 * 30,
      retry: 2,
      enabled: !!filename,
    })),
  });
}
