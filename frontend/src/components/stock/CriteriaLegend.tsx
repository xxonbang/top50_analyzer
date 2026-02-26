import { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface CriteriaLegendProps {
  isAdmin: boolean;
  hasCriteriaData: boolean;
}

const LEGEND_ITEMS = [
  { dotColor: 'bg-red-500', label: '전고점 돌파', desc: '6개월(120영업일) 고가를 현재가가 돌파한 종목' },
  { icon: '👑', label: '52주 신고가', desc: '52주 신고가를 현재가가 돌파한 종목 (더 강력한 매수 신호)' },
  { dotColor: 'bg-blue-500', label: '외국인/기관 수급', desc: '외국인과 기관이 동시에 순매수 중인 종목' },
  { dotColor: 'bg-violet-500', label: '프로그램 매매', desc: '프로그램 순매수량이 양수인 종목' },
  { dotColor: 'bg-orange-500', label: '끼 보유', desc: '상한가(29%↑) 이력 또는 거래대금 1,000억 이상 + 시초가 대비 종가 10%↑ 이력이 있는 종목' },
  { dotColor: 'bg-yellow-400', label: '저항선 돌파', desc: '심리적 저항선(호가 단위 경계, 라운드 넘버)을 전일종가 기준으로 현재가가 돌파한 종목' },
  { dotColor: 'bg-teal-500', label: '정배열', desc: '현재가 > MA5 > MA10 > MA20 > MA60 > MA120 이동평균선 정배열 상태인 종목' },
  { dotColor: 'bg-fuchsia-500', label: '거래대금 TOP30', desc: 'KOSPI+KOSDAQ 합산 거래대금 상위 30위 이내 종목' },
  { dotColor: 'bg-lime-500', label: '시가총액 적정', desc: '시가총액 3,000억 ~ 10조원 범위 내 종목' },
  { dotColor: 'bg-yellow-400/30 ring-1 ring-yellow-400', label: '전체 충족', desc: '위 8개 기준을 모두 충족한 종목' },
];

export function CriteriaLegend({ isAdmin, hasCriteriaData }: CriteriaLegendProps) {
  const [activeIndex, setActiveIndex] = useState<number | 'help' | null>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeIndex === null) return;
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setActiveIndex(null);
      }
    };
    document.addEventListener('click', handleClick, true);
    return () => document.removeEventListener('click', handleClick, true);
  }, [activeIndex]);

  useEffect(() => {
    if (activeIndex === null || !popupRef.current) return;
    const popup = popupRef.current;
    popup.style.left = '';
    popup.style.right = '';
    const rect = popup.getBoundingClientRect();
    if (rect.right > window.innerWidth - 8) {
      popup.style.left = 'auto';
      popup.style.right = '0';
    }
  }, [activeIndex]);

  if (!isAdmin || !hasCriteriaData) return null;

  return (
    <div ref={containerRef} className="bg-bg-primary/40 rounded-lg p-2 sm:p-3 mb-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="relative text-[10px] sm:text-xs font-semibold text-text-secondary mr-1">
          선정 기준
          <button
            onClick={() => setActiveIndex(activeIndex === 'help' ? null : 'help')}
            className="inline-flex items-center justify-center w-3 h-3 sm:w-3.5 sm:h-3.5 rounded-full bg-text-muted/20 text-text-muted text-[8px] sm:text-[9px] font-bold leading-none ml-0.5 cursor-pointer active:opacity-60 sm:hover:opacity-70 transition-opacity"
          >?</button>
          {activeIndex === 'help' && (
            <div className="absolute top-full left-0 mt-1.5 z-50 w-44 bg-white border border-border rounded-lg shadow-lg p-2">
              <p className="text-[10px] text-text-secondary leading-relaxed">각 기준 이름을 클릭하면 상세 설명을 확인할 수 있습니다.</p>
            </div>
          )}
        </span>
        {LEGEND_ITEMS.map((item, i) => (
          <span key={item.label} className="relative inline-flex items-center gap-1">
            <button
              onClick={() => setActiveIndex(activeIndex === i ? null : i)}
              className="inline-flex items-center gap-1 cursor-pointer active:opacity-60 sm:hover:opacity-70 transition-opacity"
            >
              {'icon' in item
                ? <span className="text-[10px] sm:text-xs leading-none">{item.icon}</span>
                : <span className={cn('inline-block w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full', item.dotColor)} />
              }
              <span className="text-[10px] sm:text-xs text-text-muted">{item.label}</span>
            </button>
            {activeIndex === i && (
              <div
                ref={popupRef}
                className="absolute top-full left-1/2 -translate-x-1/2 mt-1.5 z-50 w-56 bg-white border border-border rounded-lg shadow-lg p-2.5"
              >
                <div className="flex items-center gap-1.5 mb-1">
                  {'icon' in item
                    ? <span className="text-xs leading-none flex-shrink-0">{item.icon}</span>
                    : <span className={cn('inline-block w-2 h-2 rounded-full flex-shrink-0', item.dotColor)} />
                  }
                  <span className="text-[11px] font-semibold text-text-primary">{item.label}</span>
                </div>
                <p className="text-[10px] text-text-secondary leading-relaxed">{item.desc}</p>
              </div>
            )}
          </span>
        ))}
      </div>
    </div>
  );
}
