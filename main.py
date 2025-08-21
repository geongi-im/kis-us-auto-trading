import asyncio
import os
import sys
import traceback
from dotenv import load_dotenv
from trading_bot import TradingBot
from utils.logger_util import LoggerUtil

# 환경변수 로드
load_dotenv()

# 필수 환경변수 체크 함수
def checkEnvVariables():
    """필수 환경변수 체크"""
    required_vars = ['APP_KEY', 'APP_SECRET', 'ACCOUNT_NO', 'IS_VIRTUAL', 
                     'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'MARKET_START_TIME', 
                     'MARKET_END_TIME', 'AUTO_SHUTDOWN_TIME', 'RSI_OVERSOLD', 'RSI_OVERBOUGHT']
    missing_vars = [var for var in required_vars if os.getenv(var) is None]
    
    if missing_vars:
        raise Exception(f"다음 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
    
    # IS_VIRTUAL 값이 올바른지 확인
    is_virtual = os.getenv("IS_VIRTUAL").lower()
    if is_virtual not in ["true", "false"]:
        raise Exception("IS_VIRTUAL 환경변수는 'true' 또는 'false'로 설정해야 합니다.")
    
    # API URL 상수 정의
    REAL_REST_URL = "https://openapi.koreainvestment.com:9443"
    REAL_WS_URL = "ws://ops.koreainvestment.com:21000"
    VIRTUAL_REST_URL = "https://openapivts.koreainvestment.com:29443"
    VIRTUAL_WS_URL = "ws://ops.koreainvestment.com:31000"
    
    # 환경변수 설정
    os.environ['REST_URL_BASE'] = VIRTUAL_REST_URL if is_virtual == "true" else REAL_REST_URL
    os.environ['WS_URL_BASE'] = VIRTUAL_WS_URL if is_virtual == "true" else REAL_WS_URL

async def main_async():
    """비동기 메인 함수"""
    # 로거 초기화
    logger = LoggerUtil().get_logger()
    
    # 환경변수 체크
    checkEnvVariables()
    logger.info("환경변수 체크 완료")
    
    # 현재 환경 정보 출력
    is_virtual = True if os.getenv("IS_VIRTUAL").lower() == "true" else False
    env_type = "모의투자" if is_virtual else "실전투자"
    logger.info(f"현재 환경: {env_type}")
    logger.info(f"REST API URL: {os.getenv('REST_URL_BASE')}")
    
    # RSI 자동매매 봇 시작
    logger.info("RSI 기반 자동매매 봇을 시작합니다...")
    
    # 매매 봇 생성 및 시작 (테스트용 1분 간격)
    trading_bot = TradingBot(
        symbol="TQQQ",
        market="NASD",
        check_interval_minutes=1
    )
    
    await trading_bot.start_trading()

def main():
    """메인 함수"""
    logger = LoggerUtil().get_logger()
    
    try:
        # 이벤트 루프 생성 및 비동기 함수 실행
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("\n프로그램이 사용자에 의해 종료되었습니다.")
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류 발생: {e}")
        logger.error(traceback.format_exc())
        sys.exit(-1)

if __name__ == "__main__":
    main()