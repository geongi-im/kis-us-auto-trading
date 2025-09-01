import asyncio
import os
from dotenv import load_dotenv
from kis_websocket import KisWebSocket
from kis_order import KisOrder
from kis_price import KisPrice
from utils.logger_util import LoggerUtil


class OrderExecutionTester:
    """실제 주문 실행과 함께 체결통보 테스트"""
    
    def __init__(self):
        self.logger = LoggerUtil().get_logger()
        self.kis_order = KisOrder()
        self.kis_price = KisPrice()
        self.received_notifications = []
        
    async def execution_notification_handler(self, execution_info: dict):
        """체결통보 핸들러"""
        try:
            self.logger.info("🎉 === 실시간 체결통보 수신 ===")
            self.logger.info(f"📈 종목코드: {execution_info.get('ticker', 'N/A')}")
            self.logger.info(f"💰 매수/매도: {'🟢 매수' if execution_info.get('buy_sell_gb') == '02' else '🔴 매도' if execution_info.get('buy_sell_gb') == '01' else execution_info.get('buy_sell_gb', 'N/A')}")
            self.logger.info(f"📊 체결수량: {execution_info.get('execution_qty', 'N/A')} 주")
            self.logger.info(f"💵 체결가격: ${execution_info.get('execution_price', 'N/A')}")
            self.logger.info(f"⏰ 체결시간: {execution_info.get('execution_time', 'N/A')}")
            self.logger.info(f"🔢 주문번호: {execution_info.get('order_no', 'N/A')}")
            self.logger.info(f"✅ 체결여부: {execution_info.get('execution_yn', 'N/A')}")
            self.logger.info(f"📋 계좌번호: {execution_info.get('account_no', 'N/A')}")
            self.logger.info("===============================")
            
            # 수신된 알림 저장
            self.received_notifications.append(execution_info)
            
        except Exception as e:
            self.logger.error(f"체결통보 처리 중 오류: {e}")
    
    async def execute_test_order(self, ticker: str = "AAPL", market: str = "NAS"):
        """테스트용 소량 주문 실행"""
        try:
            self.logger.info(f"🚀 {ticker} 테스트 주문 실행 준비")
            
            # 현재가 조회
            price_info = self.kis_price.getPrice(market, ticker)
            current_price = float(price_info.get('last', 0))
            
            if current_price <= 0:
                self.logger.error(f"❌ {ticker} 현재가 조회 실패")
                return False
                
            self.logger.info(f"📊 {ticker} 현재가: ${current_price:.2f}")
            
            # 매수 주문 (1주, 현재가 대비 약간 높은 가격)
            order_price = round(current_price * 1.01, 2)  # 현재가의 101%
            quantity = 1
            
            self.logger.info(f"📝 매수 주문 실행: {quantity}주 @ ${order_price:.2f}")
            
            result = self.kis_order.buyOrder(
                ticker=ticker,
                quantity=quantity, 
                price=order_price,
                market=market,
                ord_dvsn="00"  # 지정가
            )
            
            if result:
                self.logger.info("✅ 매수 주문 전송 성공!")
                return True
            else:
                self.logger.error("❌ 매수 주문 전송 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"테스트 주문 실행 중 오류: {e}")
            return False
    
    async def test_with_real_order(self):
        """실제 주문과 함께 체결통보 테스트"""
        try:
            self.logger.info("🎯 실제 주문 실행 + 실시간 체결통보 테스트 시작")
            
            # WebSocket 연결
            ws_manager = KisWebSocket()
            ws_manager.set_execution_callback(self.execution_notification_handler)
            
            # 환경 정보 출력
            is_virtual = os.getenv("IS_VIRTUAL", "true").lower() == "true"
            env_type = "🧪 모의투자" if is_virtual else "💰 실투자"
            self.logger.info(f"환경: {env_type}")
            
            # WebSocket 연결 시작 (백그라운드)
            connection_task = asyncio.create_task(ws_manager.connect())
            
            # 연결 안정화 대기
            await asyncio.sleep(3)
            
            if ws_manager.is_connected:
                self.logger.info("🔗 WebSocket 연결 완료, 테스트 주문 실행")
                
                # 테스트 주문 실행
                order_success = await self.execute_test_order()
                
                if order_success:
                    self.logger.info("⏳ 60초 동안 체결통보 대기 중...")
                    await asyncio.sleep(60)  # 60초 대기
                else:
                    self.logger.warning("⚠️ 주문 실행 실패, 30초 대기 후 종료")
                    await asyncio.sleep(30)
                    
            else:
                self.logger.error("❌ WebSocket 연결 실패")
            
            # 연결 해제
            await ws_manager.disconnect()
            connection_task.cancel()
            
            # 결과 출력
            self.print_test_results()
            
        except Exception as e:
            self.logger.error(f"테스트 실행 중 오류: {e}")
    
    def print_test_results(self):
        """테스트 결과 출력"""
        self.logger.info("\n📊 === 테스트 결과 ===")
        self.logger.info(f"수신된 체결통보: {len(self.received_notifications)}건")
        
        if self.received_notifications:
            self.logger.info("🎉 체결통보 수신 성공!")
            for i, notification in enumerate(self.received_notifications, 1):
                self.logger.info(f"  {i}. {notification.get('ticker')} "
                                f"{notification.get('execution_qty')}주 @ "
                                f"${notification.get('execution_price')}")
        else:
            self.logger.info("ℹ️ 수신된 체결통보 없음")
            self.logger.info("  - 주문이 아직 체결되지 않았거나")
            self.logger.info("  - 주문 가격이 시장가와 차이가 클 수 있습니다")
        
        self.logger.info("========================")


async def main():
    """메인 함수"""
    # 환경변수 로드
    load_dotenv()
    
    logger = LoggerUtil().get_logger()
    
    # 환경변수 체크
    required_vars = ['APP_KEY', 'APP_SECRET', 'ACCOUNT_NO', 'IS_VIRTUAL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"누락된 환경변수: {', '.join(missing_vars)}")
        return
    
    # 주의사항 안내
    is_virtual = os.getenv("IS_VIRTUAL", "true").lower() == "true"
    if not is_virtual:
        logger.warning("⚠️  실투자 환경입니다!")
        response = input("실제 돈으로 테스트 주문을 실행하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            logger.info("테스트를 중단합니다.")
            return
    else:
        logger.info("🧪 모의투자 환경에서 안전하게 테스트합니다.")
    
    # 테스터 생성 및 실행
    tester = OrderExecutionTester()
    await tester.test_with_real_order()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")