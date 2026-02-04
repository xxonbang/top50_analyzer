import { useState } from 'react';

interface HistoryButtonProps {
  onClick: () => void;
  label?: string;
  count?: number;
}

export function HistoryButton({ onClick, label = "분석 히스토리", count }: HistoryButtonProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`
        group relative flex items-center gap-2 px-3 md:px-4 py-2 md:py-2.5
        bg-white/80 backdrop-blur-sm
        border border-slate-200/80 hover:border-indigo-300
        rounded-xl shadow-sm hover:shadow-md
        transition-all duration-300 ease-out
        hover:bg-gradient-to-r hover:from-indigo-50/80 hover:to-purple-50/80
        active:scale-[0.98]
      `}
    >
      {/* 아이콘 */}
      <div className={`
        flex items-center justify-center w-7 h-7 md:w-8 md:h-8
        rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600
        shadow-sm group-hover:shadow-indigo-200
        transition-all duration-300
        ${isHovered ? 'scale-110 rotate-3' : ''}
      `}>
        <svg
          className="w-4 h-4 md:w-4.5 md:h-4.5 text-white"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
      </div>

      {/* 텍스트 */}
      <div className="flex flex-col items-start">
        <span className="text-xs md:text-sm font-semibold text-slate-700 group-hover:text-indigo-700 transition-colors whitespace-nowrap">
          {label}
        </span>
        {count !== undefined && (
          <span className="text-[0.6rem] md:text-[0.65rem] text-slate-400 group-hover:text-indigo-400 transition-colors">
            {count}개 기록
          </span>
        )}
      </div>

      {/* 화살표 */}
      <svg
        className={`
          w-4 h-4 text-slate-400 group-hover:text-indigo-500
          transition-all duration-300
          ${isHovered ? 'translate-x-0.5' : ''}
        `}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polyline points="9 18 15 12 9 6"/>
      </svg>

      {/* Hover 시 글로우 효과 */}
      <div className={`
        absolute inset-0 rounded-xl
        bg-gradient-to-r from-indigo-400/0 via-purple-400/0 to-indigo-400/0
        group-hover:from-indigo-400/5 group-hover:via-purple-400/10 group-hover:to-indigo-400/5
        transition-all duration-500 pointer-events-none
      `}/>
    </button>
  );
}
