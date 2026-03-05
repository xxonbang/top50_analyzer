function Pulse({ className }: { className?: string }) {
  return <div className={`animate-pulse bg-slate-200 rounded ${className ?? ''}`} />;
}

export function AnalysisSkeleton() {
  return (
    <div className="space-y-4">
      {/* ResultsMeta skeleton */}
      <div className="grid grid-cols-2 gap-2 md:gap-3">
        {[0, 1].map(i => (
          <div key={i} className="bg-bg-secondary border border-border rounded-xl px-3 md:px-4 py-2.5 md:py-3 flex items-center gap-2 md:gap-3">
            <Pulse className="w-8 h-8 md:w-10 md:h-10 rounded-lg flex-shrink-0" />
            <div className="flex-1 space-y-2">
              <Pulse className="h-3 w-16" />
              <Pulse className="h-4 w-24" />
            </div>
          </div>
        ))}
      </div>

      {/* SignalSummary skeleton */}
      <div className="grid grid-cols-5 gap-2 md:gap-3.5">
        {[0, 1, 2, 3, 4].map(i => (
          <div key={i} className="bg-bg-secondary border border-border rounded-xl md:rounded-2xl py-3 px-1 md:py-5 md:px-4 flex flex-col items-center gap-2">
            <Pulse className="w-7 h-7 md:w-10 md:h-10 rounded-lg" />
            <Pulse className="h-6 w-8 md:h-9 md:w-12" />
            <Pulse className="h-3 w-10 md:w-14" />
          </div>
        ))}
      </div>

      {/* Stock cards skeleton */}
      <div className="space-y-2.5">
        {[0, 1, 2, 3].map(i => (
          <div key={i} className="bg-bg-secondary border border-border rounded-xl p-3 md:p-4">
            <div className="flex justify-between items-start mb-3">
              <div className="space-y-2 flex-1">
                <Pulse className="h-5 w-32" />
                <Pulse className="h-3 w-20" />
              </div>
              <Pulse className="h-6 w-16 rounded-2xl" />
            </div>
            <Pulse className="h-12 w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}
