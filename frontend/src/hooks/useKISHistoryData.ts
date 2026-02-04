import { useQuery } from '@tanstack/react-query';
import { fetchKISHistoryData } from '@/services/api';

export function useKISHistoryData(filename: string | null) {
  return useQuery({
    queryKey: ['kis-history', filename],
    queryFn: () => fetchKISHistoryData(filename!),
    enabled: !!filename,
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
}
