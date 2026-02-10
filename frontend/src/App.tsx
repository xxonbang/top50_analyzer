import { useEffect, useState, lazy, Suspense } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { Navigation, Toast, ScrollToTop } from '@/components/common';
import { AnalysisTabs, Footer } from '@/components/layout';
import { HistoryPanel } from '@/components/history';
import { VisionAnalysis, APIAnalysis } from '@/pages';
import { LoadingSpinner } from '@/components/common';

// CombinedAnalysis는 lazy loading - 처음 접근 시에만 로드
const CombinedAnalysis = lazy(() => import('@/pages/CombinedAnalysis').then(m => ({ default: m.CombinedAnalysis })));
// SimulationPage는 lazy loading
const SimulationPage = lazy(() => import('@/pages/SimulationPage').then(m => ({ default: m.SimulationPage })));

import { useUIStore } from '@/store/uiStore';
import { fetchLatestData, fetchKISData, fetchKISAnalysis, fetchHistoryIndex } from '@/services/api';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 2,
      staleTime: 1000 * 60 * 5, // 5분간 데이터를 fresh로 유지
    },
  },
});

// 앱 로드 시 모든 데이터를 미리 prefetch하는 훅
function usePrefetchAllData() {
  const client = useQueryClient();

  useEffect(() => {
    // 백그라운드에서 모든 데이터 prefetch (병렬 실행)
    Promise.allSettled([
      client.prefetchQuery({
        queryKey: ['vision', 'latest'],
        queryFn: fetchLatestData,
      }),
      client.prefetchQuery({
        queryKey: ['kis-data'],
        queryFn: fetchKISData,
      }),
      client.prefetchQuery({
        queryKey: ['kis-analysis'],
        queryFn: fetchKISAnalysis,
      }),
      client.prefetchQuery({
        queryKey: ['history', 'index'],
        queryFn: fetchHistoryIndex,
      }),
    ]);
  }, [client]);
}

function MainContent() {
  const { activeTab } = useUIStore();

  // 지연 마운트: 탭을 한 번이라도 방문했는지 추적
  // 방문한 탭만 렌더링하고, 이후에는 CSS로 숨김 처리
  const [mountedTabs, setMountedTabs] = useState<Set<string>>(() => new Set(['vision']));

  useEffect(() => {
    if (!mountedTabs.has(activeTab)) {
      setMountedTabs(prev => new Set([...prev, activeTab]));
    }
  }, [activeTab, mountedTabs]);

  return (
    <>
      <AnalysisTabs />

      {/* Vision AI - 항상 마운트 */}
      <div style={{ display: activeTab === 'vision' ? 'block' : 'none' }}>
        <VisionAnalysis />
      </div>

      {/* API Analysis - 방문 시에만 마운트 */}
      {mountedTabs.has('api') && (
        <div style={{ display: activeTab === 'api' ? 'block' : 'none' }}>
          <APIAnalysis />
        </div>
      )}

      {/* Combined Analysis - 방문 시에만 마운트 (lazy loading) */}
      {mountedTabs.has('combined') && (
        <div style={{ display: activeTab === 'combined' ? 'block' : 'none' }}>
          <Suspense fallback={<LoadingSpinner message="분석 종합 로딩 중..." />}>
            <CombinedAnalysis />
          </Suspense>
        </div>
      )}
    </>
  );
}

function AppContent() {
  // 앱 로드 시 모든 데이터 미리 로드
  usePrefetchAllData();
  const { currentPage } = useUIStore();

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary">
      <Navigation />
      {currentPage === 'home' && <HistoryPanel />}
      <Toast />

      <main className="max-w-[1200px] mx-auto px-4 md:px-6 pt-20 md:pt-24 pb-10">
        {currentPage === 'home' ? (
          <MainContent />
        ) : (
          <Suspense fallback={<LoadingSpinner message="모의투자 페이지 로딩 중..." />}>
            <SimulationPage />
          </Suspense>
        )}
      </main>

      <Footer />
      <ScrollToTop />
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}
