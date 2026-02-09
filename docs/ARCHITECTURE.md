# System Architecture: SignalPulse - AI Stock Signal Analyzer

## 1. Overview
이 시스템은 네이버 증권의 실시간 시장 데이터를 브라우저 자동화(Playwright)를 통해 시각적으로 수집하고, Gemini 2.5 Flash의 대규모 컨텍스트 및 Vision 기능을 활용하여 국내 주식 상위 100개 종목에 대한 투자 시그널을 도출하는 자동화 파이프라인이다.

## 2. Tech Stack
- Language: Python 3.10+
- Automation: Playwright (Headless Browser)
- AI Engine: Google Gemini 2.5 Flash (Vision API)
- Environment: GitHub Actions (Scheduler) or Local Desktop
- Output: Markdown Report / JSON Data

## 3. System Workflow (Logic Chain)

### Phase 1: Market Data Scraping (List Up)
- Target API (신버전 stock.naver.com):
  - 코스피: https://stock.naver.com/api/domestic/market/stock/default?tradeType=KRX&marketType=KOSPI&orderType=amountTop&startIdx=0&pageSize=50
  - 코스닥: https://stock.naver.com/api/domestic/market/stock/default?tradeType=KRX&marketType=KOSDAQ&orderType=amountTop&startIdx=0&pageSize=50
- Action:
  - API 호출로 코스피 상위 50개 종목의 종목명(itemname) 및 6자리 코드(itemcode) 추출
  - API 호출로 코스닥 상위 50개 종목의 종목명(itemname) 및 6자리 코드(itemcode) 추출
- Output: 총 100개의 종목 코드 리스트

### Phase 2: Visual Evidence Collection (Screenshot)
- Target URL Pattern: https://stock.naver.com/domestic/stock/{symbol_code}
- Action:
  - 각 종목 페이지 접속 후 페이지 로딩 대기
  - Screenshot Area: 전체 화면(full screen) 캡처
  - Optimization: Gemini 전송 최적화를 위해 이미지 크기를 조정하고 ./captures/{yyyy-mm-dd}/{code}.png 경로에 저장
  - Performance: 100개 종목 순회 시 타임아웃 방지를 위한 비동기 처리(asyncio) 적용

### Phase 3: AI Vision Batch Processing (Analysis)
- AI Model: Gemini 2.5 Flash
- Action:
  - 저장된 이미지를 API 호출에 포함
  - Input: 이미지 + Structured Prompt
  - Analysis Scope: 시가/종가, 이동평균선(MA), 차트 패턴, 거래량 변화율, 전일, 고가, 저가, 거래대금, 시총, 외인소진율, PER, EPS, PBR, BPS, 배당수익률, 투자자별 매매동향 등

### Phase 4: Signal Derivation & Reporting
- Output Schema:
  - 종목명(코드): [시그널]
  - 분석 근거: 2~3줄 요약 설명
- Signal Categories: [적극매수, 매수, 중립, 매도, 적극매도]

## 4. Module Structure

```
/top50_analyzer
├── main.py                 # 실행 메인 로직 및 오케스트레이션
├── modules/
│   ├── scraper.py          # Playwright 기반 리스트 수집 및 스크린샷 캡처
│   ├── ai_engine.py        # Gemini API 연동 및 프롬프트 관리
│   └── utils.py            # 이미지 처리 및 파일 저장 관련 유틸리티
├── config/
│   └── settings.py         # API Key, 환경 설정
├── captures/               # 생성된 스크린샷 저장 폴더
├── output/                 # 분석 결과 저장 폴더
├── requirements.txt        # Python 의존성
└── .env                    # GEMINI_API_KEY 저장
```

## 5. AI Prompt Engineering (Gemini)

### System Prompt:
"너는 20년 경력의 대한민국 주식 시장 전문 퀀트 애널리스트다. 제공된 이미지는 네이버 증권의 종목별 주가 상세 정보 화면이다."

### User Instructions:
- 각 이미지에서 시가/종가, 이동평균선(MA), 차트 패턴, 거래량 변화율 등 모든 지표를 정확히 추출하라
- 기술적 분석 관점에서 [적극매수, 매수, 중립, 매도, 적극매도] 중 하나의 시그널을 결정하라
- 분석 근거는 반드시 이미지에서 확인되는 지표를 바탕으로 2~3문장으로 간결하게 설명하라
- 최종 결과는 한국어로 작성하며, JSON 형식을 유지하라

## 6. Technical Considerations

- **Playwright Stealth**: 봇 탐지 방지를 위해 User-Agent를 최신 Chrome 버전으로 설정
- **Rate Limiting**: Gemini API 호출 시 Request too large 에러 발생 시 분할 전송
- **Wait Strategies**: 페이지 이동 후 차트 컴포넌트가 완전히 렌더링될 때까지 대기
- **Image Compression**: 토큰 절약을 위해 캡처 후 이미지 해상도를 적절히 리사이징
