# KIS-US-AUTO-TRADING
한국투자증권 API를 활용한 해외주식 자동매매 시스템

## 기능 설명
1. 해외주식 실시간 체결 정보 조회
2. 해외주식 모의투자 주문 기능
3. 계좌 잔고 조회 기능
4. 주문 취소/정정 기능
5. 시세 조회 기능

## 환경 설정
1. `.env.sample` 파일을 복사하여 `.env`를 생성하세요. (예: `cp .env.sample .env`)
2. `.env` 파일을 열고 필수 환경변수 정보를 입력하세요.

## 파일 구성
- `kis_base.py`: 기본 API 클래스 (공통 인증 및 요청 처리)
- `kis_order.py`: 주문 관련 API 클래스
- `kis_account.py`: 계좌/잔고 관련 API 클래스
- `kis_price.py`: 시세 관련 API 클래스
- `kis_trading.py`: 통합 API 클래스
- `main.py`: 메인 실행 파일
