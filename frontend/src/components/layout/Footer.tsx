export function Footer() {
  return (
    <footer className="border-t border-border py-5 md:py-7 px-4 md:px-6 text-center text-text-muted text-xs md:text-sm bg-bg-secondary">
      <p className="leading-relaxed">
        <span className="hidden sm:inline">AI Vision Stock Signal Analyzer (AVSSA) | </span>
        <span className="sm:hidden">AVSSA | </span>
        Powered by Gemini 2.5 Flash Vision API
      </p>
      <p className="mt-1.5 text-[0.65rem] md:text-xs">
        본 서비스는 투자 참고용이며, 투자 결정에 대한 책임은 투자자 본인에게 있습니다.
      </p>
    </footer>
  );
}
