import asyncio
import os
import pytz
import traceback
from datetime import datetime, time
from typing import Optional, Dict
from kis_order import KisOrder
from kis_account import KisAccount
from rsi_strategy import RSIStrategy
from utils.telegram_util import TelegramUtil
from utils.logger_util import LoggerUtil
from utils.datetime_util import DateTimeUtil


class TradingBot:
    """RSI 기반 자동매매 봇"""
    
    def __init__(self, 
                 symbol: str = "TQQQ",
                 market: str = "NASD"):
        
        # 로거 초기화
        self.logger = LoggerUtil().get_logger()
        
        self.symbol = symbol
        self.market = market
        
        # 환경변수에서 체크 간격 및 쿨다운 시간 가져오기 (main에서 이미 체크했으므로 반드시 존재)
        self.check_interval_minutes = int(os.getenv("CHECK_INTERVAL_MINUTES"))
        self.cooldown_minutes = int(os.getenv("COOLDOWN_MINUTES"))
        
        # KIS API 객체들
        self.kis_order = KisOrder()
        self.kis_account = KisAccount()
        
        # 환경변수에서 RSI 설정 가져오기
        rsi_oversold = int(os.getenv("RSI_OVERSOLD"))
        rsi_overbought = int(os.getenv("RSI_OVERBOUGHT"))
        
        # RSI 전략
        self.strategy = RSIStrategy(symbol=symbol, market="NAS", rsi_oversold=rsi_oversold, rsi_overbought=rsi_overbought)
        
        # 텔레그램 유틸
        self.telegram = TelegramUtil()
        
        # 봇 상태
        self.is_running = False
        self.total_trades = 0
        self.start_time = None
        
        # 환경변수에서 시간 설정 가져오기
        market_start = os.getenv("MARKET_START_TIME")
        market_end = os.getenv("MARKET_END_TIME") 
        auto_shutdown = os.getenv("AUTO_SHUTDOWN_TIME")
        
        # 시간 파싱 (HH:MM 형식)
        start_hour, start_min = map(int, market_start.split(":"))
        end_hour, end_min = map(int, market_end.split(":"))
        shutdown_hour, shutdown_min = map(int, auto_shutdown.split(":"))
        
        # 미국 장시간 (미국 현지시간 기준)
        self.market_start_time = time(start_hour, start_min)
        self.market_end_time = time(end_hour, end_min)
        
        # 자동 종료 시간 (미국 현지시간 기준)  
        self.auto_shutdown_time = time(shutdown_hour, shutdown_min)
    
    def is_market_hours(self):
        """현재 시간이 미국 장시간인지 확인 (미국 현지시간 기준)"""
        us_now = DateTimeUtil.get_us_now().time()
        
        # 미국 시간 기준으로 장시간 체크
        if self.market_start_time <= self.market_end_time:
            # 같은 날 (예: 09:30 ~ 16:00)
            return self.market_start_time <= us_now <= self.market_end_time
        else:
            # 자정을 넘나드는 경우 (예: 23:00 ~ 04:00)  
            return us_now >= self.market_start_time or us_now <= self.market_end_time
    
    def should_shutdown(self):
        """자동 종료 시간인지 확인 (미국 현지시간 기준)"""
        us_now = DateTimeUtil.get_us_now()
        us_current_time = us_now.time()
        
        # 미국 시간 기준으로 자동 종료 시간 체크
        if us_current_time >= self.auto_shutdown_time:
            return True
        
        # 추가적으로 시작 시간 기준 최대 실행 시간 체크 (8시간)
        if self.start_time:
            # start_time을 미국 시간으로 변환해서 비교
            if hasattr(self.start_time, 'astimezone'):
                # 이미 timezone aware한 경우
                start_time_us = self.start_time.astimezone(DateTimeUtil.US_TIMEZONE)
            else:
                # naive datetime인 경우 한국시간으로 가정하고 변환
                korea_tz = pytz.timezone('Asia/Seoul')
                start_time_korea = korea_tz.localize(self.start_time)
                start_time_us = start_time_korea.astimezone(DateTimeUtil.US_TIMEZONE)
            
            elapsed_hours = (us_now - start_time_us).total_seconds() / 3600
            return elapsed_hours >= 8
        
        return False
    
    def get_cash_balance(self):
        """현재 매수가능현금 조회"""
        try:
            # getBalance로 매수가능한 외화금액 조회
            balance_info = self.kis_account.getBalance(market=self.market)
            summary = balance_info.get('summary', {})
            
            # 매수가능현금 (USD)
            # frcr_pchs_amt1: 외화매수가능금액1 (실제 매수 가능한 현금)
            cash_balance = float(summary.get('frcr_pchs_amt1', '0'))
            
            self.logger.debug(f"매수가능현금: ${cash_balance:.2f}")
            return cash_balance
            
        except Exception as e:
            self.logger.error(f"매수가능현금 조회 중 오류 발생: {e}")
            return 0.0
    
    def get_stock_balance(self):
        """현재 주식 보유량 조회"""
        try:
            balance_info = self.kis_account.getBalance(market=self.market)
            stocks = balance_info.get('stocks', [])
            
            for stock in stocks:
                if stock.get('pdno') == self.symbol:
                    return {
                        'quantity': int(stock.get('ord_psbl_qty', '0')),  # 주문가능수량
                        'avg_price': float(stock.get('pchs_avg_pric', '0')),  # 매입평균가
                        'current_price': float(stock.get('now_pric2', '0')),  # 현재가
                        'profit_loss': float(stock.get('evlu_pfls_amt', '0'))  # 평가손익금액
                    }
            
            return {'quantity': 0, 'avg_price': 0, 'current_price': 0, 'profit_loss': 0}
            
        except Exception as e:
            self.logger.error(f"주식 잔고 조회 중 오류 발생: {e}")
            return {'quantity': 0, 'avg_price': 0, 'current_price': 0, 'profit_loss': 0}
        
    def getPurchaseAmount(self, price="0", symbol=""):
        """특정 종목 기준 매수 가능 금액 조회"""
        try:
            # getOverseasPurchaseAmount로 매수가능한 외화금액 조회
            balance_info = self.kis_account.getOverseasPurchaseAmount(market=self.market, price=price, symbol=symbol)
            
            # 매수가능현금 (USD)
            cash_balance = float(balance_info.get('ord_psbl_frcr_amt', '0'))
            
            self.logger.debug(f"매수가능현금: ${cash_balance:.2f}")
            return cash_balance
            
        except Exception as e:
            self.logger.error(f"매수가능현금 조회 중 오류 발생: {e}")
            return 0.0
    
    def calculate_buy_quantity(self, cash_balance: float, current_price: float):
        """매수 수량 계산 (현금의 5%)"""
        buy_amount = cash_balance * self.strategy.buy_percentage
        quantity = int(buy_amount / current_price)
        return max(1, quantity)  # 최소 1주
    
    def calculate_sell_quantity(self, stock_balance):
        """매도 수량 계산 (보유량의 5%)"""
        total_quantity = stock_balance['quantity']
        sell_quantity = int(total_quantity * self.strategy.sell_percentage)
        return max(1, min(sell_quantity, total_quantity))  # 최소 1주, 최대 보유량
    
    def get_last_buy_order_time(self):
        """가장 마지막 매수 주문 시간 조회 (미국 현지시간)"""
        try:
            today_str = DateTimeUtil.get_us_date_str()
            
            # 오늘 날짜의 주문내역 조회
            order_history = self.kis_account.getOverseasOrderHistory(
                symbol=self.symbol, 
                start_date=today_str, 
                end_date=today_str, 
                order_div="02",  # 매수만
                fetch_all=True
            )
            
            if not order_history:
                return None
            
            # 매수 주문만 필터링하고 시간순 정렬 (최신순)
            buy_orders = [order for order in order_history if order.get('sll_buy_dvsn_cd') == '02']
            if not buy_orders:
                return None
            
            # 가장 최신 매수 주문의 시간 반환 (미국 현지시간)
            latest_order = buy_orders[0]  # 이미 정렬되어 있음 (DS: 최신순)
            order_date = latest_order.get('ord_dt', '')  # YYYYMMDD
            order_time = latest_order.get('ord_tmd', '')  # HHMMSS
            
            if order_date and order_time:
                return DateTimeUtil.parse_us_datetime(order_date, order_time)
                
        except Exception as e:
            self.logger.error(f"마지막 매수 주문 시간 조회 중 오류: {e}")
            
        return None

    def execute_buy_order(self, current_price: float):
        """매수 주문 실행 (쿨다운 시간 체크 포함)"""
        try:
            # 쿨다운 시간 체크
            last_buy_time = self.get_last_buy_order_time()
            if last_buy_time:
                time_diff = DateTimeUtil.get_time_diff_minutes(last_buy_time)
                
                if time_diff < self.cooldown_minutes:
                    remaining_minutes = self.cooldown_minutes - time_diff
                    self.logger.info(f"매수 쿨다운 중: {remaining_minutes:.1f}분 후 가능")
                    return False
            cash_balance = self.getPurchaseAmount(price=current_price, symbol=self.symbol)
            if cash_balance < current_price:
                self.logger.warning(f"매수 불가: 현금 부족 (${cash_balance:.2f})")
                return False
            
            quantity = self.calculate_buy_quantity(cash_balance, current_price)
            
            # 매수 주문 실행
            result = self.kis_order.buyOrder(
                symbol=self.symbol,
                quantity=quantity,
                price=current_price,
                market=self.market,
                ord_dvsn="00"  # 지정가 주문
            )
            
            if result:
                self.strategy.execute_buy()
                self.total_trades += 1
                
                # 텔레그램 알림
                rsi = self.strategy.get_current_rsi()
                message = f"""[매수] {self.symbol} 주문 완료
RSI: {rsi:.1f}
매수량: {quantity}주 (${quantity * current_price:.2f})
현재가: ${current_price:.2f}
현금잔고: ${cash_balance:.2f}
시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                
                self.telegram.sendMessage(message)
                self.logger.info(f"매수 주문 성공: {quantity}주 @ ${current_price:.2f}")
                return True
            
        except Exception as e:
            error_msg = f"매수 주문 실행 중 오류: {e}"
            self.logger.error(error_msg)
            self.telegram.sendMessage(f"[오류] 매수 오류: {error_msg}")
            
        return False
    
    def execute_sell_order(self, current_price: float):
        """매도 주문 실행"""
        try:
            stock_balance = self.get_stock_balance()
            if stock_balance['quantity'] == 0:
                self.logger.warning("매도 불가: 보유 주식 없음")
                return False
            
            quantity = self.calculate_sell_quantity(stock_balance)
            
            # 매도 주문 실행
            result = self.kis_order.sellOrder(
                symbol=self.symbol,
                quantity=quantity,
                price=current_price,
                market=self.market,
                ord_dvsn="00"  # 지정가 주문
            )
            
            if result:
                self.strategy.execute_sell()
                self.total_trades += 1
                
                # 텔레그램 알림
                rsi = self.strategy.get_current_rsi()
                profit_loss = stock_balance['profit_loss']
                message = f"""[매도] {self.symbol} 주문 완료
RSI: {rsi:.1f}
매도량: {quantity}주 (${quantity * current_price:.2f})
현재가: ${current_price:.2f}
평가손익: ${profit_loss:.2f}
남은수량: {stock_balance['quantity'] - quantity}주
시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                
                self.telegram.sendMessage(message)
                self.logger.info(f"매도 주문 성공: {quantity}주 @ ${current_price:.2f}")
                return True
            
        except Exception as e:
            error_msg = f"매도 주문 실행 중 오류: {e}"
            self.logger.error(error_msg)
            self.telegram.sendMessage(f"[오류] 매도 오류: {error_msg}")
            
        return False
    
    def process_trading_signal(self, current_price: float):
        """매매 신호 처리"""
        # 현재 RSI 가격 업데이트
        self.strategy.update_price(current_price)
        
        # RSI 계산
        rsi = self.strategy.get_current_rsi()
        if rsi is None:
            self.logger.warning("RSI 계산 불가 (데이터 부족)")
            return
        
        self.logger.info(f"{self.symbol} 현재가: ${current_price:.2f}, RSI: {rsi:.1f}")
        
        # 매수 신호 확인
        if self.strategy.should_buy():
            self.logger.info(f"매수 신호 감지! RSI: {rsi:.1f}")
            self.execute_buy_order(current_price)
        
        # 매도 신호 확인
        elif self.strategy.should_sell():
            self.logger.info(f"매도 신호 감지! RSI: {rsi:.1f}")
            self.execute_sell_order(current_price)
    
    async def start_trading(self):
        """매매 봇 시작"""
        self.is_running = True
        self.start_time = DateTimeUtil.get_us_now()
        
        self.logger.info(f"RSI 자동매매 봇 시작: {self.symbol}")
        self.logger.info(f"체크 간격: {self.check_interval_minutes}분")
        self.logger.info(f"장시간: {self.market_start_time} - {self.market_end_time}")

        # result = self.kis_account.getOverseasOrderHistory(symbol="TQQQ", start_date="20250820", end_date="20250821", fetch_all=True)
        # print(result)

        # 해외주식 매수가능금액 조회
        # purchase_amount = self.kis_account.getOverseasPurchaseAmount(market="NASD", price="90.4200", symbol="TQQQ")
        # print(purchase_amount)
        
        # 과거 데이터 로드 (실제 일봉 데이터 사용)
        if not self.strategy.load_historical_data():
            self.logger.error("과거 데이터 로드 실패. 봇을 종료합니다.")
            return
        
        # 주식 보유량 조회
        # stock_balance = self.get_stock_balance()
        # self.logger.info(f"현재 주식 보유량: {stock_balance['quantity']}주")
        
        # 시작 알림
        start_msg = f"""[시작] RSI 자동매매 봇
종목: {self.symbol}
RSI 임계값: {self.strategy.rsi_oversold} / {self.strategy.rsi_overbought}
매수/매도 비율: {self.strategy.buy_percentage*100}%
체크 간격: {self.check_interval_minutes}분"""
        
        self.telegram.sendMessage(start_msg)
        
        try:
            while self.is_running:
                # 자동 종료 시간 체크
                if self.should_shutdown():
                    self.logger.info("자동 종료 시간에 도달했습니다. 프로그램을 종료합니다.")
                    break
                
                # 장시간 체크
                if not self.is_market_hours():
                    self.logger.info("장시간이 아닙니다. 대기 중...")
                    await asyncio.sleep(60)  # 1분 대기
                    continue
                
                try:
                    # 현재가 조회
                    price_info = self.strategy.kis_price.getPrice("NAS", self.symbol)
                    current_price = float(price_info.get('last', 0))
                    
                    if current_price > 0:
                        self.process_trading_signal(current_price)
                    else:
                        self.logger.warning("유효한 가격 정보를 가져올 수 없습니다.")
                
                except Exception as e:
                    error_msg = f"매매 처리 중 오류: {e}"
                    self.logger.error(error_msg)
                    self.logger.error(traceback.format_exc())
                
                # 다음 체크까지 대기
                await asyncio.sleep(self.check_interval_minutes * 60)
                
        except KeyboardInterrupt:
            self.logger.info("사용자에 의해 봇이 중단되었습니다.")
        except Exception as e:
            error_msg = f"봇 실행 중 치명적 오류: {e}"
            self.logger.error(error_msg)
            self.telegram.sendMessage(f"[긴급] 봇 오류: {error_msg}")
        finally:
            await self.stop_trading()
    
    async def stop_trading(self):
        """매매 봇 종료"""
        self.is_running = False
        
        if self.start_time:
            runtime = DateTimeUtil.get_us_now() - self.start_time
            self.logger.info(f"봇 운영시간: {str(runtime).split('.')[0]}")
            self.logger.info(f"총 거래횟수: {self.total_trades}")
        
        self.logger.info("매매 봇이 종료되었습니다.")
    
    def get_bot_status(self):
        """봇 현재 상태 반환"""
        strategy_status = self.strategy.get_strategy_status()
        
        return {
            "is_running": self.is_running,
            "start_time": self.start_time,
            "total_trades": self.total_trades,
            "is_market_hours": self.is_market_hours(),
            "strategy": strategy_status
        }