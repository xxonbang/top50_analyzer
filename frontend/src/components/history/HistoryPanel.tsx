import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchCombinedHistoryIndex } from '@/services/api';
import { useUIStore } from '@/store/uiStore';
import { LoadingSpinner } from '@/components/common';
import { cn } from '@/lib/utils';

// 시그널별 색상
const signalColors: Record<string, string> = {
  '적극매수': 'bg-signal-strong-buy',
  '매수': 'bg-signal-buy',
  '중립': 'bg-signal-neutral',
  '매도': 'bg-signal-sell',
  '적극매도': 'bg-signal-strong-sell',
};

interface HistoryItemData {
  date: string;
  time?: string;
  filename: string;
  total_stocks: number;
  signals: Record<string, number>;
}

function HistoryItem({
  item,
  isToday,
  isActive,
  onClick,
}: {
  item: HistoryItemData;
  isToday: boolean;
  isActive: boolean;
  onClick: () => void;
}) {
  const displayTime = item.time ? `${item.time.slice(0, 2)}:${item.time.slice(2)}` : '';

  return (
    <div
      onClick={onClick}
      className={cn(
        'p-3 md:p-4 rounded-xl mb-2 cursor-pointer transition-all border',
        isActive
          ? 'bg-gradient-to-r from-indigo-50 to-purple-50 border-indigo-300 shadow-md'
          : 'bg-bg-primary border-border hover:border-indigo-200 hover:shadow-sm'
      )}
    >
      <div className="flex justify-between items-center mb-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm md:text-base text-text-primary">
            {item.date}
          </span>
          {displayTime && (
            <span className="text-xs md:text-sm text-text-muted">
              {displayTime}
            </span>
          )}
          {isToday && (
            <span className="px-1.5 py-0.5 bg-indigo-100 text-indigo-700 text-[0.6rem] md:text-xs rounded font-medium">
              오늘
            </span>
          )}
        </div>
        <span className="text-xs md:text-sm text-text-muted">
          {item.total_stocks}종목
        </span>
      </div>

      {/* 시그널 바 */}
      <div className="flex gap-0.5 h-1.5 md:h-2 rounded-full overflow-hidden bg-gray-100">
        {(() => {
          const signalSum = Object.values(item.signals || {}).reduce((a, b) => a + b, 0);
          return Object.entries(item.signals || {}).map(([signal, count]) => {
            if (count === 0) return null;
            const width = signalSum > 0 ? (count / signalSum) * 100 : 0;
            return (
              <div
                key={signal}
                className={cn('h-full', signalColors[signal] || 'bg-gray-300')}
                style={{ width: `${width}%` }}
                title={`${signal}: ${count}`}
              />
            );
          });
        })()}
      </div>
    </div>
  );
}

export function HistoryPanel() {
  const {
    isHistoryPanelOpen,
    closeHistoryPanel,
    viewingHistoryDateTime,
    setViewingHistory,
    isViewingHistory,
  } = useUIStore();

  // Combined 히스토리 인덱스 (통합 히스토리로 사용)
  const { data: historyIndex, isLoading, error } = useQuery({
    queryKey: ['combined-history', 'index'],
    queryFn: fetchCombinedHistoryIndex,
  });

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

  const handleItemClick = (item: HistoryItemData) => {
    // dateTime 형식으로 저장: "2026-02-04_0700"
    const dateTime = item.time ? `${item.date}_${item.time}` : item.date;
    setViewingHistory(dateTime);
    closeHistoryPanel();
  };

  // 현재 보고 있는 히스토리의 dateTime 계산
  const getItemDateTime = (item: HistoryItemData) => {
    return item.time ? `${item.date}_${item.time}` : item.date;
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
        <div className="px-4 md:px-5 py-2.5 md:py-3 bg-indigo-50/50 text-[0.65rem] md:text-xs text-indigo-700 border-b border-indigo-100">
          <div className="flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 16v-4M12 8h.01"/>
            </svg>
            <span>
              히스토리 선택 시 <strong>모든 탭</strong>이 해당 시점의 데이터로 동기화됩니다.
            </span>
          </div>
        </div>

        {historyIndex && (
          <div className="px-4 md:px-5 py-2.5 md:py-3 bg-bg-primary/50 text-[0.65rem] md:text-xs text-text-muted border-b border-border">
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

          {!isLoading && !error && (!historyIndex || historyIndex.history.length === 0) && (
            <div className="text-center py-10 text-text-muted">
              <div className="text-4xl mb-3">📭</div>
              <p>아직 저장된 분석 기록이 없습니다.</p>
              <p className="text-[0.65rem] mt-2">
                workflow 실행 후 히스토리가 생성됩니다.
              </p>
            </div>
          )}

          {historyIndex && historyIndex.history.map((item) => (
            <HistoryItem
              key={item.filename}
              item={item}
              isToday={item.date === today}
              isActive={
                isViewingHistory
                  ? viewingHistoryDateTime === getItemDateTime(item)
                  : item.date === today
              }
              onClick={() => handleItemClick(item)}
            />
          ))}
        </div>
      </div>
    </>
  );
}
