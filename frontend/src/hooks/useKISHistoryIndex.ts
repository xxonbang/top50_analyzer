import { useQuery } from '@tanstack/react-query';
import { fetchKISHistoryIndex } from '@/services/api';

export function useKISHistoryIndex() {
  return useQuery({
    queryKey: ['kis-history', 'index'],
    queryFn: fetchKISHistoryIndex,
    staleTime: 1000 * 60 * 5, // 5 minutes
    retry: 1,
  });
}
