# KIS-US-AUTO-TRADING

한국투자증권 OpenAPI를 활용한 미국 주식 자동매매 시스템

## 프로젝트 개요

이 프로젝트는 한국투자증권의 OpenAPI를 사용하여 미국 주식 시장에서 자동으로 매매를 수행하는 트레이딩 봇입니다. RSI 및 MACD 기술적 지표를 기반으로 매수/매도 신호를 감지하고, WebSocket을 통한 실시간 체결 통보를 받아 자동으로 거래를 실행합니다.

## 주요 기능

- **다중 종목 자동매매**: 여러 미국 주식 종목을 동시에 모니터링하고 자동 거래
- **기술적 지표 기반 전략**
  - RSI(Relative Strength Index) 기반 과매도/과매수 감지
  - MACD(Moving Average Convergence Divergence) 골든크로스 확인
- **실시간 체결 통보**: WebSocket을 통한 실시간 주문 체결 알림
- **손절매 기능**: 설정된 손실률에 도달하면 자동으로 시장가 매도
- **텔레그램 알림**: 매매 신호, 체결 내역, 오류 발생 시 텔레그램으로 실시간 알림
- **주문 추적 시스템**: 미체결 주문 관리 및 체결량 추적
- **장시간 관리**: 미국 시장 개장/폐장 시간 자동 감지 및 휴장일 체크
- **모의투자/실전투자 지원**: 환경변수로 간편하게 전환 가능

## 기술적 특징

- **비동기 처리**: asyncio를 활용한 효율적인 비동기 WebSocket 통신
- **토큰 자동 관리**: OAuth2 토큰 자동 발급 및 갱신
- **API 호출 제한 관리**: 적절한 딜레이를 통한 API 호출 빈도 제한 준수
- **에러 핸들링**: 포괄적인 예외 처리 및 로깅
- **타임존 관리**: 한국 시간과 미국 시간 자동 변환 처리

## 시스템 아키텍처

### 핵심 모듈

```
kis-us-auto-trading/
├── main.py                    # 메인 실행 파일
├── trading_bot.py             # 트레이딩 봇 핵심 로직
├── kis_base.py                # KIS API 기본 클래스 (인증, 공통 요청)
├── kis_order.py               # 주문 관련 API
├── kis_account.py             # 계좌/잔고 관련 API
├── kis_price.py               # 시세 조회 API
├── kis_websocket.py           # WebSocket 실시간 통신
├── rsi_strategy.py            # RSI 전략 구현
├── macd_strategy.py           # MACD 전략 구현
└── utils/                     # 유틸리티 모듈
    ├── token_manager.py       # 토큰 관리
    ├── telegram_util.py       # 텔레그램 알림
    ├── logger_util.py         # 로깅 유틸리티
    └── datetime_util.py       # 날짜/시간 유틸리티
```

## 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd kis-us-auto-trading
```

### 2. 파이썬 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 설정

`.env.sample` 파일을 복사하여 `.env` 파일을 생성하고 필요한 정보를 입력하세요.

```bash
cp .env.sample .env
```

## 환경 변수 설정

`.env` 파일에 다음 항목들을 설정해야 합니다:

### KIS API 인증 정보
```bash
# 실전/모의 구분
IS_VIRTUAL=true                    # true: 모의투자, false: 실전투자

# 한국투자증권 API 정보
HTS_ID=your_hts_id                 # HTS ID
APP_KEY=your_app_key               # 앱 키
APP_SECRET=your_app_secret         # 앱 시크릿
ACCOUNT_NO=your_account_no         # 계좌번호 (8자리+2자리)
```

### 텔레그램 설정
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_CHAT_TEST_ID=your_test_chat_id
```

### 거래 설정
```bash
# 거래 종목 (시장:티커 형식, 쉼표로 구분)
TRADING_TICKERS=NASDAQ:TQQQ,NYSE:O,AMEX:XLF

# 장 운영 시간 (미국 현지 시간 기준)
MARKET_START_TIME=09:30
MARKET_END_TIME=16:00
AUTO_SHUTDOWN_TIME=16:30

# 매매 간격 설정
CHECK_INTERVAL_MINUTES=1           # 매매 신호 체크 간격 (분)
BUY_DELAY_MIN=5                    # 매수 후 다음 매수까지 대기 시간 (분)
SELL_DELAY_MIN=5                   # 매도 후 다음 매도까지 대기 시간 (분)

# 거래 비율 설정
BUY_RATE=0.30                      # 매수 시 사용 가능 현금의 30%
SELL_RATE=0.30                     # 매도 시 보유 수량의 30%
```

### RSI 설정
```bash
RSI_OVERSOLD=50                    # RSI 과매도 기준값 (이하일 때 매수 신호)
RSI_OVERBOUGHT=60                  # RSI 과매수 기준값 (이상일 때 매도 신호)
RSI_INTERVAL=day                   # RSI 계산 인터벌 (day, 1, 3, 5, 15, 30, 60)
```

### MACD 설정
```bash
MACD_INTERVAL=1                    # MACD 계산 인터벌 (day, 1, 3, 5, 15, 30, 60)
```

### 손절매 설정
```bash
STOP_LOSS_RATE=-5                  # 손절매 기준 수익률 (%)
```

## 실행 방법

```bash
python main.py
```

프로그램이 시작되면:
1. 환경 변수 검증
2. 거래 종목 초기화
3. RSI/MACD 전략 초기화
4. WebSocket 체결 통보 연결
5. 장 시작 알림 및 보유 종목 현황 전송
6. 설정된 간격으로 매매 신호 감지 시작

## 트레이딩 전략

### 매수 신호
다음 조건을 **모두** 만족할 때 매수 주문 실행:
1. **RSI 과매도**: 현재 RSI 값이 설정된 과매도 기준값 이하
2. **매수 대기시간**: 마지막 매수 후 설정된 대기시간 경과
3. **현금 잔고**: 매수 가능한 현금이 충분함
4. **미체결 주문 없음**: 해당 종목의 미체결 주문이 없음

### 매도 신호
다음 조건을 **모두** 만족할 때 매도 주문 실행:
1. **RSI 과매수**: 현재 RSI 값이 설정된 과매수 기준값 이상
2. **MACD 골든크로스**: 최근 5봉 내에 MACD 골든크로스 발생
3. **매도 대기시간**: 마지막 매도 후 설정된 대기시간 경과
4. **보유 주식 있음**: 매도할 주식을 보유하고 있음
5. **미체결 주문 없음**: 해당 종목의 미체결 주문이 없음

### 손절매
- 평가 수익률이 설정된 손절매 기준 이하로 떨어지면 **시장가 매도** 자동 실행
- 손절매는 매매 신호 체크보다 우선 실행됨

## 주요 모듈 설명

### kis_base.py
- KIS OpenAPI의 기본 클래스
- 토큰 관리 및 API 요청 공통 처리
- 모의투자/실전투자 자동 전환
- 토큰 만료 시 자동 재발급

### kis_order.py
- 주문 관련 API 제공
- 매수/매도/정정/취소 주문 실행
- 실전/모의투자 TR ID 자동 매핑

### kis_account.py
- 계좌 정보 조회 API
- 잔고, 미체결 내역, 주문 내역 조회
- 매수 가능 금액 계산

### kis_price.py
- 시세 정보 조회 API
- 현재가, 일봉, 분봉 차트 데이터 제공

### trading_bot.py
- 트레이딩 봇의 핵심 로직
- 매매 신호 감지 및 주문 실행
- 주문 추적 및 체결 통보 처리
- 장시간 관리 및 자동 종료

### rsi_strategy.py
- RSI 지표 계산 및 매매 신호 생성
- 일봉/분봉 데이터 기반 RSI 계산

### macd_strategy.py
- MACD 지표 계산
- 골든크로스/데드크로스 감지

### kis_websocket.py
- WebSocket 기반 실시간 체결 통보
- 자동 재연결 및 PING-PONG 처리

## 텔레그램 알림

봇은 다음 상황에서 텔레그램 메시지를 전송합니다:

- 장 시작 시 봇 정보 및 보유 종목 현황
- 매수 주문 완료
- 매도 주문 완료
- 손절매 실행
- 전량 체결 완료
- 오류 발생 시

## 로깅

- 로그 파일은 `logs/` 디렉토리에 날짜별로 생성됩니다
- 로그 레벨: INFO, DEBUG, ERROR
- 모든 API 요청/응답, 매매 신호, 주문 내역이 기록됩니다

## 주의사항

1. **API 키 보안**: `.env` 파일은 절대 공개 저장소에 업로드하지 마세요
2. **모의투자 테스트**: 실전투자 전에 반드시 모의투자로 충분히 테스트하세요
3. **API 호출 제한**: 한국투자증권 API는 호출 횟수 제한이 있으니 주의하세요
4. **손실 위험**: 자동매매는 손실 위험이 있습니다. 충분한 이해 후 사용하세요
5. **시장 상황**: 급격한 시장 변동 시 예상치 못한 결과가 발생할 수 있습니다
6. **네트워크 안정성**: 안정적인 인터넷 연결이 필요합니다

## 문제 해결

### 토큰 발급 실패
- APP_KEY, APP_SECRET이 올바른지 확인
- 한국투자증권 OpenAPI 서비스 신청 여부 확인

### WebSocket 연결 실패
- 방화벽 설정 확인
- WS_URL_BASE가 올바른지 확인

### 주문 실패
- 계좌번호가 올바른지 확인
- 매수 가능 현금 확인
- 장시간인지 확인

## 개발 환경

- Python 3.8 이상
- 주요 라이브러리:
  - requests: HTTP API 통신
  - websockets: WebSocket 통신
  - pandas, numpy: 데이터 처리
  - ta: 기술적 지표 계산
  - python-dotenv: 환경변수 관리
  - pytz: 타임존 처리
  - holidays: 휴장일 체크

## 라이센스

이 프로젝트는 개인 학습 및 연구 목적으로 제작되었습니다.

## 면책 조항

이 소프트웨어는 교육 및 연구 목적으로만 제공됩니다. 실제 투자에 사용하여 발생하는 손실에 대해 개발자는 책임지지 않습니다. 투자는 본인의 판단과 책임 하에 이루어져야 합니다.

## 참고 자료

- [한국투자증권 OpenAPI 문서](https://apiportal.koreainvestment.com/)
- [WebSocket API 가이드](https://apiportal.koreainvestment.com/apiservice/oauth2)
