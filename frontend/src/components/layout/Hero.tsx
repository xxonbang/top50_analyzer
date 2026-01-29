import { Badge } from '@/components/common';

export function Hero() {
  return (
    <section className="text-center py-6 md:py-12 px-2 md:px-0">
      <h1 className="text-xl md:text-4xl font-bold mb-2 md:mb-3 text-text-primary">
        AI Vision{' '}
        <span className="bg-gradient-to-br from-accent-primary to-accent-secondary bg-clip-text text-transparent">
          Stock Signal
        </span>{' '}
        Analyzer
      </h1>
      <p className="text-sm md:text-base text-text-secondary max-w-xl mx-auto mb-4 md:mb-5 px-2 md:px-0">
        Gemini 2.5 Flash Vision API를 활용하여 국내 주식 거래량 상위 120개 종목을 자동으로 분석합니다.
      </p>
      <div className="flex justify-center gap-1.5 md:gap-2 flex-wrap">
        <Badge className="text-[0.65rem] md:text-xs px-2 md:px-3 py-1 md:py-1.5">🤖 Gemini 2.5</Badge>
        <Badge className="text-[0.65rem] md:text-xs px-2 md:px-3 py-1 md:py-1.5">📸 Playwright</Badge>
        <Badge className="text-[0.65rem] md:text-xs px-2 md:px-3 py-1 md:py-1.5">🇰🇷 KOSPI + KOSDAQ</Badge>
        <Badge className="text-[0.65rem] md:text-xs px-2 md:px-3 py-1 md:py-1.5">⚡ 배치 분석</Badge>
      </div>
    </section>
  );
}
