import { Logo } from './Logo';
import { useUIStore } from '@/store/uiStore';
import { useAuthStore } from '@/store/authStore';
import { useQuery } from '@tanstack/react-query';
import { fetchCombinedHistoryIndex } from '@/services/api';

export function Navigation() {
  const { currentPage, setCurrentPage, isCompactView, toggleCompactView, openHistoryPanel } = useUIStore();
  const { user, signOut } = useAuthStore();

  // Combined 히스토리 인덱스
  const { data: historyIndex } = useQuery({
    queryKey: ['combined-history', 'index'],
    queryFn: fetchCombinedHistoryIndex,
  });

  return (
    <nav aria-label="메인 네비게이션" className="fixed top-0 left-0 right-0 bg-white/95 backdrop-blur-xl border-b border-border z-50 px-4 md:px-6 pt-[env(safe-area-inset-top)]">
      <div className="max-w-[1200px] mx-auto flex justify-between items-center h-14 md:h-16">
        <Logo />

        {/* 우측 버튼 그룹 */}
        <div className="flex items-center gap-2">
          {/* 모의투자 / 홈으로 토글 - 주요 액션 */}
          <button
            onClick={() => setCurrentPage(currentPage === 'home' ? 'simulation' : 'home')}
            className="flex items-center gap-1.5 px-2.5 md:px-3 py-1.5 md:py-2
              bg-accent-primary/10 text-accent-primary
              border border-accent-primary/30
              rounded-lg text-xs md:text-sm font-semibold
              hover:bg-accent-primary hover:text-white
              transition-all"
          >
            {currentPage === 'home' ? (
              <>
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
                  <polyline points="16 7 22 7 22 13"/>
                </svg>
                <span className="hidden md:inline">모의투자</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
                  <polyline points="9 22 9 12 15 12 15 22"/>
                </svg>
                <span className="hidden md:inline">홈으로</span>
              </>
            )}
          </button>

          {/* 히스토리 버튼 - 보조 액션 */}
          <button
            onClick={openHistoryPanel}
            className="flex items-center gap-1.5 px-2.5 md:px-3 py-1.5 md:py-2
              text-text-muted
              rounded-lg text-xs md:text-sm font-medium
              hover:bg-bg-primary hover:text-text-secondary
              transition-all"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
            <span className="hidden md:inline">히스토리</span>
            {historyIndex?.total_records !== undefined && (
              <span className="flex items-center justify-center min-w-[1.1rem] h-[1.1rem] px-1
                bg-accent-primary/10 text-accent-primary text-[0.65rem] font-semibold
                rounded-full"
              >
                {historyIndex.total_records}
              </span>
            )}
          </button>

          {/* Compact 보기 토글 */}
          <button
            onClick={toggleCompactView}
            className={`
              flex items-center gap-1.5 px-2.5 md:px-3 py-1.5 md:py-2
              rounded-lg text-xs md:text-sm font-medium
              border transition-all
              ${isCompactView
                ? 'bg-accent-primary text-white border-accent-primary'
                : 'bg-bg-secondary text-text-secondary border-border hover:border-accent-primary hover:text-accent-primary'
              }
            `}
            title={isCompactView ? '일반 보기' : 'Compact 보기'}
          >
            {isCompactView ? (
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7"/>
                <rect x="14" y="3" width="7" height="7"/>
                <rect x="3" y="14" width="7" height="7"/>
                <rect x="14" y="14" width="7" height="7"/>
              </svg>
            ) : (
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="8" y1="6" x2="21" y2="6"/>
                <line x1="8" y1="12" x2="21" y2="12"/>
                <line x1="8" y1="18" x2="21" y2="18"/>
                <line x1="3" y1="6" x2="3.01" y2="6"/>
                <line x1="3" y1="12" x2="3.01" y2="12"/>
                <line x1="3" y1="18" x2="3.01" y2="18"/>
              </svg>
            )}
            <span className="hidden md:inline">{isCompactView ? '일반' : 'Compact'}</span>
          </button>

          {/* 로그아웃 - 최소화 */}
          {user && (
            <button
              onClick={signOut}
              className="flex items-center gap-1.5 px-2 md:px-2.5 py-1.5 md:py-2
                text-text-muted/60
                rounded-lg text-xs md:text-sm font-medium
                hover:text-red-500 hover:bg-red-50
                transition-all"
              title={user.email ?? '로그아웃'}
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              <span className="hidden md:inline">LOGOUT</span>
            </button>
          )}
        </div>
      </div>
    </nav>
  );
}
