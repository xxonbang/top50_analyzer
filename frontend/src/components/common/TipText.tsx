import { useState } from 'react';

interface TipTextProps {
  children: React.ReactNode;
  id?: string;
}

export function TipText({ children, id }: TipTextProps) {
  const storageKey = id ? `tip_dismissed_${id}` : null;
  const [dismissed, setDismissed] = useState(() =>
    storageKey ? localStorage.getItem(storageKey) === '1' : false
  );

  if (dismissed) return null;

  const handleDismiss = () => {
    if (storageKey) localStorage.setItem(storageKey, '1');
    setDismissed(true);
  };

  return (
    <div className="text-[0.7rem] md:text-[0.8125rem] text-text-secondary flex items-start gap-2 md:gap-3 px-3 md:px-4 py-2.5 md:py-3 bg-slate-50 border border-slate-200 rounded-lg leading-relaxed mb-3 md:mb-4">
      <svg className="w-3.5 h-3.5 md:w-4 md:h-4 flex-shrink-0 text-slate-500 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"/>
      </svg>
      <span className="flex-1">{children}</span>
      {storageKey && (
        <button
          onClick={handleDismiss}
          className="flex-shrink-0 text-slate-400 hover:text-slate-600 transition-colors p-0.5"
          aria-label="팁 닫기"
        >
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      )}
    </div>
  );
}
