# KIS-US-AUTO-TRADING
한국투자증권 API를 활용한 해외주식 자동매매 시스템

## 기능 설명
1. 해외주식 실시간 체결 정보 조회
2. 해외주식 모의투자 주문 기능
3. 계좌 잔고 조회 기능
4. 주문 취소/정정 기능
5. 시세 조회 기능

## 환경 설정
1. `.env` 파일을 생성하고 다음 정보를 입력하세요:
```
# API 키 및 시크릿
APP_KEY=your_app_key_here
APP_SECRET=your_app_secret_here

# URL 설정
REST_URL_BASE=https://openapivts.koreainvestment.com:29443 # 모의투자용 REST API URL
WS_URL_BASE=ws://ops.koreainvestment.com:31000 # 모의투자용 웹소켓 URL

# 계좌 설정
ACCOUNT_NO=your_account_number_here # 모의투자 계좌번호(앞 8자리 + 뒷 2자리)
```

## 파일 구성
- `kis_base.py`: 기본 API 클래스 (공통 인증 및 요청 처리)
- `kis_order.py`: 주문 관련 API 클래스
- `kis_account.py`: 계좌/잔고 관련 API 클래스
- `kis_price.py`: 시세 관련 API 클래스
- `kis_trading.py`: 통합 API 클래스
- `main.py`: 메인 실행 파일
