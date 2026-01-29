import { useEffect } from 'react';
import { useHistoryIndex } from '@/hooks/useHistoryIndex';
import { useUIStore } from '@/store/uiStore';
import { LoadingSpinner } from '@/components/common';
import { HistoryItem } from './HistoryItem';
import { cn } from '@/lib/utils';

export function HistoryPanel() {
  const {
    isHistoryPanelOpen,
    closeHistoryPanel,
    viewingHistoryFile,
    setViewingHistory,
    isViewingHistory,
  } = useUIStore();

  const { data: historyIndex, isLoading, error } = useHistoryIndex();

  const today = new Date().toISOString().split('T')[0];

  useEffect(() => {
    if (isHistoryPanelOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isHistoryPanelOpen]);

  const handleItemClick = (filename: string) => {
    setViewingHistory(filename);
    closeHistoryPanel();
  };

  return (
    <>
      {/* Overlay */}
      <div
        className={cn(
          'fixed inset-0 bg-black/40 z-[200] transition-opacity',
          isHistoryPanelOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        )}
        onClick={closeHistoryPanel}
      />

      {/* Panel */}
      <div
        className={cn(
          'fixed top-0 bottom-0 w-[320px] md:w-[380px] max-w-[85vw] bg-bg-secondary z-[201] shadow-lg transition-all duration-300 flex flex-col',
          isHistoryPanelOpen ? 'right-0' : '-right-[400px]'
        )}
      >
        {/* Header */}
        <div className="p-4 md:p-5 border-b border-border flex justify-between items-center">
          <h3 className="text-base md:text-lg font-bold flex items-center gap-2">
            <span>📅</span>
            분석 히스토리
          </h3>
          <button
            onClick={closeHistoryPanel}
            className="w-8 h-8 md:w-9 md:h-9 rounded-lg bg-bg-primary text-text-muted hover:bg-border hover:text-text-primary transition-colors flex items-center justify-center text-lg md:text-xl"
          >
            ✕
          </button>
        </div>

        {/* Info */}
        {historyIndex && (
          <div className="px-4 md:px-5 py-2.5 md:py-3 bg-bg-primary text-[0.65rem] md:text-xs text-text-muted border-b border-border">
            최근 {historyIndex.retention_days}일간 총 {historyIndex.total_records}개 기록
          </div>
        )}

        {/* List */}
        <div className="flex-1 overflow-y-auto p-2.5 md:p-3">
          {isLoading && <LoadingSpinner message="히스토리 로딩 중..." />}

          {error && (
            <div className="text-center py-10 text-text-muted">
              <div className="text-4xl mb-3">📭</div>
              <p>히스토리를 불러올 수 없습니다.</p>
            </div>
          )}

          {historyIndex && historyIndex.history.length === 0 && (
            <div className="text-center py-10 text-text-muted">
              <div className="text-4xl mb-3">📭</div>
              <p>아직 저장된 분석 기록이 없습니다.</p>
            </div>
          )}

          {historyIndex && historyIndex.history.map((item) => (
            <HistoryItem
              key={item.filename}
              item={item}
              isToday={item.date === today}
              isActive={
                isViewingHistory
                  ? viewingHistoryFile === item.filename
                  : item.date === today
              }
              onClick={() => handleItemClick(item.filename)}
            />
          ))}
        </div>
      </div>
    </>
  );
}
