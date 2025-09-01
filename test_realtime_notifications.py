import asyncio
import os
import sys
from dotenv import load_dotenv
from kis_websocket import KisWebSocket
from utils.logger_util import LoggerUtil


class RealtimeNotificationTester:
    """실시간 체결통보 테스트 클래스"""
    
    def __init__(self):
        self.logger = LoggerUtil().get_logger()
        self.received_notifications = []
        self.test_duration = 30  # 30초 테스트
        
    async def execution_notification_handler(self, execution_info: dict):
        """체결통보 핸들러"""
        try:
            self.logger.info("=== 체결통보 수신 ===")
            self.logger.info(f"종목코드: {execution_info.get('ticker', 'N/A')}")
            self.logger.info(f"매수/매도: {'매수' if execution_info.get('buy_sell_gb') == '02' else '매도' if execution_info.get('buy_sell_gb') == '01' else execution_info.get('buy_sell_gb', 'N/A')}")
            self.logger.info(f"체결수량: {execution_info.get('execution_qty', 'N/A')}")
            self.logger.info(f"체결가격: {execution_info.get('execution_price', 'N/A')}")
            self.logger.info(f"체결시간: {execution_info.get('execution_time', 'N/A')}")
            self.logger.info(f"계좌번호: {execution_info.get('account_no', 'N/A')}")
            self.logger.info(f"주문번호: {execution_info.get('order_no', 'N/A')}")
            self.logger.info(f"체결여부: {execution_info.get('execution_yn', 'N/A')}")
            self.logger.info("==================")
            
            # 수신된 알림 저장
            self.received_notifications.append(execution_info)
            
        except Exception as e:
            self.logger.error(f"체결통보 처리 중 오류: {e}")
    
    async def test_websocket_connection(self):
        """WebSocket 연결 테스트"""
        try:
            self.logger.info("WebSocket 연결 테스트 시작")
            
            # KisWebSocket 인스턴스 생성
            ws_manager = KisWebSocket()
            
            # 체결통보 콜백 설정
            ws_manager.set_execution_callback(self.execution_notification_handler)
            
            # 환경 정보 출력
            is_virtual = os.getenv("IS_VIRTUAL", "true").lower() == "true"
            env_type = "모의투자" if is_virtual else "실투자"
            self.logger.info(f"테스트 환경: {env_type}")
            self.logger.info(f"WebSocket URL: {ws_manager.ws_url}")
            self.logger.info(f"계좌번호: {ws_manager.account_no}")
            
            # WebSocket 연결
            connection_task = asyncio.create_task(ws_manager.connect())
            
            # 테스트 시간 대기
            self.logger.info(f"{self.test_duration}초 동안 실시간 데이터 수신 대기 중...")
            await asyncio.sleep(self.test_duration)
            
            # 연결 해제
            await ws_manager.disconnect()
            connection_task.cancel()
            
            # 테스트 결과 출력
            self.print_test_results()
            
        except Exception as e:
            self.logger.error(f"WebSocket 테스트 중 오류: {e}")
            return False
            
        return True
    
    def print_test_results(self):
        """테스트 결과 출력"""
        self.logger.info("\n=== 테스트 결과 ===")
        self.logger.info(f"수신된 체결통보 개수: {len(self.received_notifications)}")
        
        if self.received_notifications:
            self.logger.info("수신된 체결통보 목록:")
            for i, notification in enumerate(self.received_notifications, 1):
                self.logger.info(f"{i}. 종목: {notification.get('ticker', 'N/A')}, "
                               f"수량: {notification.get('execution_qty', 'N/A')}, "
                               f"가격: {notification.get('execution_price', 'N/A')}")
        else:
            self.logger.info("수신된 체결통보가 없습니다.")
            self.logger.info("- 테스트 기간 중 체결된 거래가 없거나")
            self.logger.info("- WebSocket 연결에 문제가 있을 수 있습니다.")
        
        self.logger.info("================")
    
    async def test_manual_execution(self):
        """수동 체결 테스트 (사용자 입력 대기)"""
        try:
            self.logger.info("수동 체결 테스트 모드")
            self.logger.info("이 모드에서는 사용자가 직접 주문을 실행하여 체결통보를 확인할 수 있습니다.")
            self.logger.info("다른 프로그램이나 HTS에서 해외주식 주문을 실행해주세요.")
            self.logger.info("종료하려면 Ctrl+C를 눌러주세요.")
            
            ws_manager = KisWebSocket()
            ws_manager.set_execution_callback(self.execution_notification_handler)
            
            # 무한 대기 (Ctrl+C로 종료)
            await ws_manager.connect()
            
        except KeyboardInterrupt:
            self.logger.info("사용자에 의해 테스트가 중단되었습니다.")
        except Exception as e:
            self.logger.error(f"수동 테스트 중 오류: {e}")


def check_environment():
    """환경변수 체크"""
    required_vars = [
        'APP_KEY', 'APP_SECRET', 'ACCOUNT_NO', 'IS_VIRTUAL',
        'REST_URL_BASE', 'WS_URL_BASE'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"누락된 환경변수: {', '.join(missing_vars)}")
        return False
    
    # HTS_ID 체크 및 안내
    hts_id = os.getenv("HTS_ID")
    if not hts_id:
        print("권장사항: HTS_ID 환경변수를 설정하면 더 정확한 체결통보를 받을 수 있습니다.")
        print("예시: HTS_ID=YOUR_HTS_ID")
        print("현재는 기본값 'CLAUDE_BOT'을 사용합니다.")
    else:
        print(f"HTS_ID 설정됨: {hts_id}")
    
    return True


async def main():
    """메인 함수"""
    # 환경변수 로드
    load_dotenv()
    
    logger = LoggerUtil().get_logger()
    
    # 환경변수 체크
    if not check_environment():
        logger.error("환경변수가 올바르게 설정되지 않았습니다.")
        sys.exit(1)
    
    logger.info("해외주식 실시간 체결통보 테스트 시작")
    
    # 테스터 생성
    tester = RealtimeNotificationTester()
    
    # 테스트 모드 선택
    print("\n테스트 모드를 선택하세요:")
    print("1. 자동 테스트 (30초 대기)")
    print("2. 수동 테스트 (직접 주문 실행)")
    
    try:
        choice = input("선택 (1 또는 2): ").strip()
        
        if choice == "1":
            success = await tester.test_websocket_connection()
            if success:
                logger.info("자동 테스트 완료")
            else:
                logger.error("자동 테스트 실패")
        elif choice == "2":
            await tester.test_manual_execution()
        else:
            logger.error("잘못된 선택입니다.")
            
    except KeyboardInterrupt:
        logger.info("테스트가 중단되었습니다.")
    except Exception as e:
        logger.error(f"테스트 실행 중 오류: {e}")


if __name__ == "__main__":
    asyncio.run(main())