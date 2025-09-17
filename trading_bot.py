import asyncio
import os
import pytz
import traceback
from datetime import datetime, time
from kis_order import KisOrder
from kis_account import KisAccount
from kis_base import KisBase
from kis_websocket import KisWebSocket
from rsi_strategy import RSIStrategy
from macd_strategy import MACDStrategy
from utils.telegram_util import TelegramUtil
from utils.logger_util import LoggerUtil
from utils.datetime_util import DateTimeUtil
import holidays


class TradingBot:
    """한국투자증권 해외 주식 자동매매 봇"""
    
    def __init__(self, trading_tickers):
        
        # 로거 초기화
        self.logger = LoggerUtil().get_logger()
        
        # 거래 종목 설정 (ticker: market 형태)
        self.trading_tickers = trading_tickers
        self.logger.info(f"거래 종목 초기화: {list(trading_tickers.keys())}")
        
        # 환경변수에서 체크 간격 및 대기시간 가져오기 (main에서 이미 체크했으므로 반드시 존재)
        self.check_interval_minutes = int(os.getenv("CHECK_INTERVAL_MINUTES"))
        self.buy_delay_minutes = int(os.getenv("BUY_DELAY_MIN"))
        self.sell_delay_minutes = int(os.getenv("SELL_DELAY_MIN"))

        stop_loss_rate = os.getenv("STOP_LOSS_RATE")
        self.stop_loss_rate = float(stop_loss_rate) if stop_loss_rate is not None else None
        if self.stop_loss_rate is not None:
            self.logger.info(f"손절매 기준 수익률 설정: {self.stop_loss_rate:.2f}%")
        
        # KIS API 객체들
        self.kis_order = KisOrder()
        self.kis_account = KisAccount()
        self.kis_base = KisBase()
        
        # WebSocket 객체 (체결통보용)
        self.kis_websocket = KisWebSocket()
        self.websocket_task = None
        
        # 매수/매도 거래 비중 가져오기
        buy_rate = float(os.getenv("BUY_RATE"))
        sell_rate = float(os.getenv("SELL_RATE"))
        self.buy_rate = buy_rate
        self.sell_rate = sell_rate

        # 기술적 지표 설정 정보 출력
        rsi_oversold = int(os.getenv("RSI_OVERSOLD"))
        rsi_overbought = int(os.getenv("RSI_OVERBOUGHT"))
        self.rsi_interval = os.getenv("RSI_INTERVAL")
        self.macd_interval = os.getenv("MACD_INTERVAL")
        
        # 각 종목별 RSI 및 MACD 전략 생성
        self.rsi_strategies = {}
        self.macd_strategies = {}
        for ticker, market in trading_tickers.items():
            parse_market = self.kis_base.changeMarketCode(market)
            self.rsi_strategies[ticker] = RSIStrategy(
                ticker=ticker, 
                market=parse_market, 
                rsi_oversold=rsi_oversold, 
                rsi_overbought=rsi_overbought,
                buy_rate=buy_rate,
                sell_rate=sell_rate
            )
            self.macd_strategies[ticker] = MACDStrategy(
                ticker=ticker,
                market=parse_market,
                buy_rate=buy_rate,
                sell_rate=sell_rate
            )
        
        # 텔레그램 유틸
        self.telegram = TelegramUtil()
        
        # 봇 상태
        self.is_running = False
        self.total_trades = 0
        self.start_time = None
        
        # 주문 추적 시스템
        self.active_orders = {}  # {order_no: {ticker, order_type, total_qty, executed_qty, remaining_qty, price, market}}
        
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
    
    def isMarketHours(self):
        """현재 시간이 미국 장시간인지 확인 (미국 현지시간 기준)"""
        us_now = DateTimeUtil.get_us_now().time()
        
        # 미국 시간 기준으로 장시간 체크
        if self.market_start_time <= self.market_end_time:
            # 같은 날 (예: 09:30 ~ 16:00)
            return self.market_start_time <= us_now <= self.market_end_time
        else:
            # 자정을 넘나드는 경우 (예: 23:00 ~ 04:00)  
            return us_now >= self.market_start_time or us_now <= self.market_end_time
    
    def shouldShutdown(self):
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
    
    def isUSMarketHoliday(self):
        """미국 주식 시장 휴장일인지 확인 (미국 현지시간 기준)"""
        us_now = DateTimeUtil.get_us_now()
        us_date = us_now.date()
        
        # 미국 주식시장 휴장일 체크
        us_holidays = holidays.US()
        
        # NYSE/NASDAQ 휴장일인지 확인
        if us_date in us_holidays:
            holiday_name = us_holidays[us_date]
            self.logger.info(f"오늘은 미국 주식시장 휴장일입니다: {holiday_name}")
            return True, holiday_name
        
        return False, None
    
    def getCashBalance(self, market):
        """현재 매수가능현금 조회"""
        try:
            # getBalance로 매수가능한 외화금액 조회
            balance_info = self.kis_account.getBalance(market=market)
            summary = balance_info.get('summary', {})
            
            # 매수가능현금 (USD)
            # frcr_pchs_amt1: 외화매수가능금액1 (실제 매수 가능한 현금)
            cash_balance = float(summary.get('frcr_pchs_amt1', '0'))
            
            self.logger.debug(f"매수가능현금: ${cash_balance:.2f}")
            return cash_balance
            
        except Exception as e:
            self.logger.error(f"매수가능현금 조회 중 오류 발생: {e}")
            return 0.0
    
    def getStockBalance(self, ticker, market):
        """현재 주식 보유량 조회"""
        try:
            balance_info = self.kis_account.getBalance(market=market)
            stocks = balance_info.get('stocks', [])
            
            for stock in stocks:
                if stock.get('ovrs_pdno') == ticker:
                    return {
                        'quantity': int(stock.get('ord_psbl_qty', '0')),  # 주문가능수량
                        'avg_price': float(stock.get('pchs_avg_pric', '0')),  # 매입평균가
                        'current_price': float(stock.get('now_pric2', '0')),  # 현재가
                        'profit_loss': float(stock.get('frcr_evlu_pfls_amt', '0'))  # 평가손익금액
                    }
            
            return {'quantity': 0, 'avg_price': 0, 'current_price': 0, 'profit_loss': 0}
            
        except Exception as e:
            self.logger.error(f"주식 잔고 조회 중 오류 발생: {e}")
            return {'quantity': 0, 'avg_price': 0, 'current_price': 0, 'profit_loss': 0}
    def getPurchaseAmount(self, ticker, market, price="0"):
        """특정 종목 기준 매수 가능 금액 조회"""
        try:
            # getOverseasPurchaseAmount로 매수가능한 외화금액 조회
            parse_market = self.kis_base.changeMarketCode(market, length=4)
            balance_info = self.kis_account.getOverseasPurchaseAmount(market=parse_market, price=price, ticker=ticker)
            
            # 매수가능현금 (USD)
            cash_balance = float(balance_info.get('ord_psbl_frcr_amt', '0'))
            
            self.logger.debug(f"{ticker} 매수가능현금: ${cash_balance:.2f}")
            return cash_balance
            
        except Exception as e:
            self.logger.error(f"{ticker} 매수가능현금 조회 중 오류 발생: {e}")
            return 0.0
    
    def calculateBuyQuantity(self, ticker, cash_balance, current_price):
        """매수 수량 계산 (현금의 5%)"""
        rsi_strategy = self.rsi_strategies[ticker]
        buy_amount = cash_balance * rsi_strategy.buy_rate
        quantity = int(buy_amount / current_price)
        return max(1, quantity)  # 최소 1주
    
    def calculateSellQuantity(self, ticker, stock_balance):
        """매도 수량 계산 (보유량의 5%)"""
        rsi_strategy = self.rsi_strategies[ticker]
        total_quantity = stock_balance['quantity']
        sell_quantity = int(total_quantity * rsi_strategy.sell_rate)
        return max(1, min(sell_quantity, total_quantity))  # 최소 1주, 최대 보유량
    
    def getLastBuyOrderTime(self, ticker):
        """가장 마지막 매수 주문 시간 조회 (한국시간)"""
        try:
            # 한국시간 기준 오늘과 내일 날짜
            start_date = DateTimeUtil.get_kr_date_str(offset=-1)  # 오늘
            end_date = DateTimeUtil.get_kr_date_str(offset=1)    # 내일
            
            # 주문내역 조회 (한국시간 기준)
            order_history = self.kis_account.getOverseasOrderHistory(
                ticker=ticker, 
                start_date=start_date, 
                end_date=end_date, 
                order_div="02",  # 매수만
                fetch_all=True
            )
            
            if not order_history:
                return None
            
            # 매수 주문만 필터링
            buy_orders = [order for order in order_history if order.get('sll_buy_dvsn_cd') == '02']
            if not buy_orders:
                return None
            
            # ord_dt(주문일자) 기준 1차 내림차순, 동일일자 내에서는 odno 기준 2차 내림차순
            buy_orders.sort(key=lambda x: (x.get('ord_dt', ''), x.get('odno', '')), reverse=True)
            
            # 가장 최신 매수 주문의 order_time만 반환 (한국시간 기준)
            latest_order = buy_orders[0]
            order_time = latest_order.get('ord_tmd', '')  # HHMMSS (한국시간 기준)
            
            if order_time:
                return order_time
                
        except Exception as e:
            self.logger.error(f"{ticker} 마지막 매수 주문 시간 조회 중 오류: {e}")
            
        return None
    
    def getLastSellOrderTime(self, ticker):
        """가장 마지막 매도 주문 시간 조회 (한국시간)"""
        try:
            # 한국시간 기준 오늘과 내일 날짜
            start_date = DateTimeUtil.get_kr_date_str(offset=-1)  # 오늘
            end_date = DateTimeUtil.get_kr_date_str(offset=1)    # 내일
            
            # 주문내역 조회 (한국시간 기준)
            order_history = self.kis_account.getOverseasOrderHistory(
                ticker=ticker, 
                start_date=start_date, 
                end_date=end_date, 
                order_div="01",  # 매도만
                fetch_all=True
            )
            
            if not order_history:
                return None
            
            # 매도 주문만 필터링
            sell_orders = [order for order in order_history if order.get('sll_buy_dvsn_cd') == '01']
            if not sell_orders:
                return None
            
            # ord_dt(주문일자) 기준 1차 내림차순, 동일일자 내에서는 odno 기준 2차 내림차순
            sell_orders.sort(key=lambda x: (x.get('ord_dt', ''), x.get('odno', '')), reverse=True)
            
            # 가장 최신 매도 주문의 order_time만 반환 (한국시간 기준)
            latest_order = sell_orders[0]
            order_time = latest_order.get('ord_tmd', '')  # HHMMSS (한국시간 기준)
            
            if order_time:
                return order_time
                
        except Exception as e:
            self.logger.error(f"{ticker} 마지막 매도 주문 시간 조회 중 오류: {e}")
            
        return None
    
    def shouldBuy(self, ticker, market, current_price):
        """매수 신호 종합 판단 (RSI + 대기시간 + 계좌 조건)"""
        rsi_strategy = self.rsi_strategies[ticker]
        
        # RSI 신호 확인
        if not rsi_strategy.getBuySignal():
            return False
        
        # 매수 대기시간 체크 (한국시간 기준)
        last_buy_time_str = self.getLastBuyOrderTime(ticker)
        if last_buy_time_str:
            # 오늘 날짜로 datetime 객체 생성 (한국시간)
            today_kr = DateTimeUtil.get_kr_date_str()  # YYYYMMDD
            last_buy_datetime = DateTimeUtil.parse_kr_datetime(today_kr, last_buy_time_str)
            
            time_diff = DateTimeUtil.get_time_diff_minutes_kr(last_buy_datetime)
            if time_diff < self.buy_delay_minutes:
                remaining_minutes = self.buy_delay_minutes - time_diff
                self.logger.info(f"{ticker} 매수 대기 중: {remaining_minutes:.1f}분 후 가능")
                return False
        
        # 계좌 잔고 확인
        cash_balance = self.getPurchaseAmount(ticker, market, current_price)
        if cash_balance < current_price:
            self.logger.debug(f"{ticker} 매수 불가: 현금 부족 (${cash_balance:.2f})")
            return False
        
        return True
    
    def shouldSell(self, ticker, market):
        """매도 신호 종합 판단 (RSI + MACD 골든크로스 + 대기시간 + 보유 주식 조건)"""
        rsi_strategy = self.rsi_strategies[ticker]
        macd_strategy = self.macd_strategies[ticker]
        
        # RSI 신호 확인
        if not rsi_strategy.getSellSignal():
            return False
        
        # MACD 최근 N봉 골든크로스 신호 확인
        if not macd_strategy.hasRecentGoldenCross(5):
            return False
        
        # 매도 대기시간 체크 (한국시간 기준)
        last_sell_time_str = self.getLastSellOrderTime(ticker)
        if last_sell_time_str:
            # 오늘 날짜로 datetime 객체 생성 (한국시간)
            today_kr = DateTimeUtil.get_kr_date_str()  # YYYYMMDD
            last_sell_datetime = DateTimeUtil.parse_kr_datetime(today_kr, last_sell_time_str)
            
            time_diff = DateTimeUtil.get_time_diff_minutes_kr(last_sell_datetime)
            if time_diff < self.sell_delay_minutes:
                remaining_minutes = self.sell_delay_minutes - time_diff
                self.logger.info(f"{ticker} 매도 대기 중: {remaining_minutes:.1f}분 후 가능")
                return False
        
        # 보유 주식 확인
        stock_balance = self.getStockBalance(ticker, market)
        if stock_balance['quantity'] == 0:
            self.logger.debug(f"{ticker} 매도 불가: 보유 주식 없음")
            return False
        
        return True

    def executeBuyOrder(self, ticker, market, current_price):
        """매수 주문 실행"""
        try:
            # 미체결 주문 확인
            if self.hasUnfilledOrders(ticker, market):
                self.logger.info(f"{ticker} 미체결 주문이 있어 새로운 매수 주문을 취소합니다")
                return False
                
            rsi_strategy = self.rsi_strategies[ticker]
            cash_balance = self.getPurchaseAmount(ticker, market, current_price)
            quantity = self.calculateBuyQuantity(ticker, cash_balance, current_price)
            parse_market = self.kis_base.changeMarketCode(market, length=4)
            
            # 매수 주문 실행
            result = self.kis_order.buyOrder(
                ticker=ticker,
                quantity=quantity,
                price=current_price,
                market=parse_market,
                ord_dvsn="00"  # 지정가 주문
            )
            
            if result:
                self.total_trades += 1
                
                # 주문번호 추출 및 추적 시스템에 추가
                order_no = str(int(result.get('ODNO', '')))
                if order_no:
                    self.addOrderToTracker(order_no, ticker, '매수', quantity, current_price, market)
                
                # 텔레그램 알림
                rsi = rsi_strategy.getCurrentRsi()
                message = f"""<b>🟥 [매수] 주문완료</b>
종목코드: {ticker}
주문번호: {order_no}
RSI: {rsi:.1f}
수량: {quantity}주 (${quantity * current_price:.2f})
현재가: ${current_price:.2f}
현금잔고: ${cash_balance:.2f}
시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                
                self.telegram.sendMessage(message)
                self.logger.info(f"{ticker} 매수 주문 성공: {quantity}주 @ ${current_price:.2f}, 주문번호: {order_no}")
                return True
            
        except Exception as e:
            error_msg = f"{ticker} 매수 주문 실행 중 오류: {e}"
            self.logger.error(error_msg)
            self.telegram.sendMessage(f"[오류] {ticker} 매수 오류: {error_msg}")
            
        return False
    
    def executeSellOrder(self, ticker, market, current_price):
        """매도 주문 실행"""
        try:
            # 미체결 주문 확인
            if self.hasUnfilledOrders(ticker, market):
                self.logger.info(f"{ticker} 미체결 주문이 있어 새로운 매도 주문을 취소합니다")
                return False
                
            rsi_strategy = self.rsi_strategies[ticker]
            macd_strategy = self.macd_strategies[ticker]
            stock_balance = self.getStockBalance(ticker, market)
            if stock_balance['quantity'] == 0:
                self.logger.warning(f"{ticker} 매도 불가: 보유 주식 없음")
                return False
            
            quantity = self.calculateSellQuantity(ticker, stock_balance)
            parse_market = self.kis_base.changeMarketCode(market, length=4)
            
            # 매도 주문 실행
            result = self.kis_order.sellOrder(
                ticker=ticker,
                quantity=quantity,
                price=current_price,
                market=parse_market,
                ord_dvsn="00"  # 지정가 주문
            )
            
            if result:
                self.total_trades += 1
                
                # 주문번호 추출 및 추적 시스템에 추가
                order_no = str(int(result.get('ODNO', '')))
                if order_no:
                    self.addOrderToTracker(order_no, ticker, '매도', quantity, current_price, market)
                
                # 텔레그램 알림
                rsi = rsi_strategy.getCurrentRsi()
                macd_data = macd_strategy.getCurrentMacd()
                profit_loss = stock_balance['profit_loss']
                
                macd_info = ""
                if macd_data:
                    macd_info = f"\nMACD: {macd_data['macd']:.4f}\nSignal: {macd_data['signal']:.4f}"
                
                message = f"""<b>🟦 [매도] 주문완료</b>
종목코드: {ticker}
주문번호: {order_no}
RSI: {rsi:.1f}{macd_info}
수량: {quantity}주 (${quantity * current_price:,.2f})
현재가: ${current_price:.2f}
평가손익: ${profit_loss:.2f}
남은수량: {stock_balance['quantity'] - quantity}주
시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                
                self.telegram.sendMessage(message)
                self.logger.info(f"{ticker} 매도 주문 성공: {quantity}주 @ ${current_price:.2f}, 주문번호: {order_no}")
                return True
            
        except Exception as e:
            error_msg = f"{ticker} 매도 주문 실행 중 오류: {e}"
            self.logger.error(error_msg)
            self.telegram.sendMessage(f"[오류] {ticker} 매도 오류: {error_msg}")

        return False

    def checkStopLoss(self, ticker, market, present_balance_stocks):
        """현재잔고 평가수익률을 기반으로 손절 조건을 점검"""
        stock_balance = self.getStockBalance(ticker, market)
        quantity = stock_balance.get('quantity', 0)
        if quantity is None or quantity <= 0:
            return False

        ticker_code = str(ticker).strip().upper()
        balance_stock = None
        for stock in present_balance_stocks or []:
            if not isinstance(stock, dict):
                continue
            code = stock.get('ovrs_pdno') or stock.get('pdno')
            if code and str(code).strip().upper() == ticker_code:
                balance_stock = stock
                break

        if balance_stock is None:
            self.logger.debug(f"{ticker} 현재잔고 데이터가 없어 손절 확인을 건너뜁니다.")
            return False

        raw_rate = balance_stock.get('evlu_pfls_rt1')
        if raw_rate is None:
            self.logger.debug(f"{ticker} 평가수익률(evlu_pfls_rt1) 데이터가 없습니다.")
            return False

        try:
            if isinstance(raw_rate, str):
                cleaned = raw_rate.replace(',', '').replace('%', '').strip()
                profit_rate = float(cleaned) if cleaned else None
            else:
                profit_rate = float(raw_rate)
        except (ValueError, TypeError):
            profit_rate = None

        if profit_rate is None:
            self.logger.debug(f"{ticker} 평가수익률(evlu_pfls_rt1) 값을 해석할 수 없습니다.")
            return False

        if self.stop_loss_rate is None:
            return False

        if profit_rate < self.stop_loss_rate:
            self.logger.info(
                f"{ticker} 손절 조건 충족: 평가수익률 {profit_rate:.2f}% < 기준 {self.stop_loss_rate:.2f}%"
            )
            return self.executeStopLossSell(
                ticker=ticker,
                market=market,
                quantity=int(quantity),
                profit_rate=profit_rate,
                stock_balance=stock_balance
            )

        return False

    def executeStopLossSell(self, ticker, market, quantity, profit_rate, stock_balance):
        """손절 조건 충족 시 시장가 매도 주문 실행"""
        if quantity <= 0:
            return False

        try:
            parse_market = self.kis_base.changeMarketCode(market, length=4)
            result = self.kis_order.sellOrder(
                ticker=ticker,
                quantity=quantity,
                price=0,
                market=parse_market,
                ord_dvsn="01"  # 시장가 주문
            )

            if result:
                self.total_trades += 1

                order_no_raw = result.get('ODNO', '')
                order_no = str(order_no_raw).strip()
                if order_no:
                    try:
                        order_no = str(int(order_no))
                    except (ValueError, TypeError):
                        pass
                    self.addOrderToTracker(order_no, ticker, '매도', quantity, 0.0, market)

                profit_loss = stock_balance.get('profit_loss', 0.0)
                avg_price = stock_balance.get('avg_price', 0.0)
                message = (
                    f"""<b>🟧 [손절] 시장가 매도</b>
종목코드: {ticker}
주문번호: {order_no or '미확인'}
수량: {quantity}주
평균단가: ${avg_price:.2f}
평가손익: ${profit_loss:,.2f}
평가수익률: {profit_rate:.2f}%
손절기준: {self.stop_loss_rate:.2f}%
시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                )

                self.telegram.sendMessage(message)
                self.logger.info(
                    f"{ticker} 손절 시장가 매도 주문 제출: {quantity}주, 평가수익률 {profit_rate:.2f}%"
                )
                return True

        except Exception as e:
            error_msg = f"{ticker} 손절 매도 주문 실행 중 오류: {e}"
            self.logger.error(error_msg)
            self.telegram.sendMessage(f"[오류] {ticker} 손절 주문 오류: {error_msg}")

        return False

    def processTradingSignal(self):
        """모든 종목에 대한 매매 신호 처리"""
        present_balance_stocks = None

        for ticker, market in self.trading_tickers.items():
            try:
                rsi_strategy = self.rsi_strategies[ticker]
                macd_strategy = self.macd_strategies[ticker]

                if self.stop_loss_rate is not None:
                    if present_balance_stocks is None:
                        try:
                            balance_data = self.kis_account.getOverseasPresentBalance()
                            stocks = balance_data.get('stocks', [])
                            if isinstance(stocks, list):
                                present_balance_stocks = stocks
                            else:
                                present_balance_stocks = []
                        except Exception as balance_error:
                            self.logger.error(f"현재잔고 조회 중 오류: {balance_error}")
                            present_balance_stocks = []

                    try:
                        if self.checkStopLoss(ticker, market, present_balance_stocks):
                            continue
                    except Exception as stop_loss_error:
                        self.logger.error(f"{ticker} 손절 점검 중 오류: {stop_loss_error}")

                # 현재가 조회
                parse_market = self.kis_base.changeMarketCode(market)
                price_info = rsi_strategy.kis_price.getPrice(parse_market, ticker)
                current_price = float(price_info.get('last', 0))
                
                if current_price <= 0:
                    self.logger.warning(f"{ticker} 유효한 가격 정보를 가져올 수 없습니다.")
                    continue

                # 최신 RSI를 미리 계산해 신호 판단에서 재사용
                rsi_strategy.getCurrentRsi(force_refresh=True)

                self.logger.info(f"{ticker} 현재가: ${current_price:.2f} RSI: {rsi_strategy.getCurrentRsi():.1f}")

                # 매수 신호 확인
                if self.shouldBuy(ticker, market, current_price):
                    self.logger.info(f"{ticker} 매수 신호 감지!")
                    self.executeBuyOrder(ticker, market, current_price)
                
                # 매도 신호 확인
                elif self.shouldSell(ticker, market):
                    self.logger.info(f"{ticker} 매도 신호 감지!")
                    self.executeSellOrder(ticker, market, current_price)
                    
            except Exception as e:
                self.logger.error(f"{ticker} 매매 신호 처리 중 오류: {e}")
                continue
    
    async def startTrading(self):
        """매매 봇 시작"""
        self.is_running = True
        self.start_time = DateTimeUtil.get_us_now()
        
        ticker_names = list(self.trading_tickers.keys())
        self.logger.info(f"RSI 다중 종목 자동매매 봇 시작: {', '.join(ticker_names)}")
        self.logger.info(f"체크 간격: {self.check_interval_minutes}분")
        self.logger.info(f"장시간: {self.market_start_time} - {self.market_end_time}")
        
        # 미국 주식시장 휴장일 체크
        is_holiday, holiday_name = self.isUSMarketHoliday()
        if is_holiday:
            holiday_msg = f"[휴장] 오늘은 미국 주식시장 휴장일입니다.\n휴일: {holiday_name}"
            self.logger.info(holiday_msg)
            self.telegram.sendMessage(holiday_msg)
            return
        
        # RSI 데이터 연결 상태 확인 (선택적)
        for ticker in self.trading_tickers.keys():
            rsi_strategy = self.rsi_strategies[ticker]
            
            # 데이터 연결 상태 확인 (실패해도 계속 진행)
            if not rsi_strategy.validateDataConnection():
                self.logger.warning(f"{ticker} RSI 데이터 연결 경고 - 계속 진행합니다.")
    
        # 시작 시점 미체결 주문 동기화 -> active_orders 초기화
        try:
            self.syncActiveOrders()
        except Exception as e:
            self.logger.error(f"미체결 주문 동기화 오류: {e}")

         # 장 시작시 봇 정보와 보유 종목 현황을 통합하여 한 번에 전송
        self.sendPortfolioStatus()
        
        # WebSocket 체결통보 연결 시작
        try:
            self.kis_websocket.set_execution_callback(self.handle_execution_notification)
            self.websocket_task = asyncio.create_task(self.kis_websocket.connect())
            await asyncio.sleep(2)  # 연결 안정화 대기
        except Exception as e:
            self.logger.error(f"WebSocket 연결 실패: {e}")
            return
        
        try:
            while self.is_running:
                # 자동 종료 시간 체크
                if self.shouldShutdown():
                    self.logger.info("자동 종료 시간에 도달했습니다. 프로그램을 종료합니다.")
                    break
                
                # 장시간 체크
                if not self.isMarketHours():
                    self.logger.info("장시간이 아닙니다. 대기 중...")
                    await asyncio.sleep(60)  # 1분 대기
                    continue
                
                try:
                    # 모든 종목에 대한 매매 신호 처리
                    self.processTradingSignal()
                
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
            await self.stopTrading()
    
    async def stopTrading(self):
        """매매 봇 종료"""
        self.is_running = False
        
        # WebSocket 연결 정리
        try:
            if self.kis_websocket and self.kis_websocket.is_connected:
                await self.kis_websocket.disconnect()
                self.logger.info("WebSocket 연결 해제 완료")
                
            if self.websocket_task and not self.websocket_task.done():
                self.websocket_task.cancel()
                try:
                    await self.websocket_task
                except asyncio.CancelledError:
                    self.logger.info("WebSocket 태스크 취소 완료")
        except Exception as e:
            self.logger.error(f"WebSocket 정리 중 오류: {e}")
        
        if self.start_time:
            runtime = DateTimeUtil.get_us_now() - self.start_time
            self.logger.info(f"봇 운영시간: {str(runtime).split('.')[0]}")
            self.logger.info(f"총 거래횟수: {self.total_trades}")
        
        self.logger.info("다중 종목 매매 봇이 종료되었습니다.")
    
    def sendPortfolioStatus(self):
        """장 시작시 봇 정보와 보유 종목 현황을 텔레그램으로 전송"""
        try:            
            # 미국 시장 보유 종목 조회
            balance_result = self.kis_account.getBalance(market="NASD")
            
            stocks = balance_result.get('stocks', [])
            summary = balance_result.get('summary', {})
            
            # 장 시작 알림 메시지 생성 및 전송
            message = self._createStartupMessage(stocks, summary)
            self.telegram.sendMessage(message)
            self.logger.info(f"장 시작 알림 및 보유 종목 현황 텔레그램 전송 완료: {len(stocks)}개 종목")
            
        except Exception as e:
            error_msg = f"장 시작 알림 및 보유 종목 현황 조회 중 오류: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.telegram.sendMessage(f"❌ <b>오류 발생</b>\n{error_msg}")
    
    def _createStartupMessage(self, stocks, summary):
        """장 시작시 전송할 통합 메시지 생성"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"📊 <b>장 시작 알림</b>\n"
        message += f"🕘 {current_time}\n\n"
        
        # 봇 정보 추가
        env_type = "모의투자" if os.getenv('IS_VIRTUAL', 'true').lower() == 'true' else "실투자"
        account_no = os.getenv('ACCOUNT_NO', 'N/A')
        ticker_names = list(self.rsi_strategies.keys())
        
        message += f"🤖 <b>봇 정보</b>\n"
        message += f"계좌번호: {account_no} ({env_type})\n"
        message += f"탐지 종목: {', '.join(ticker_names)}\n"
        message += f"탐지 간격: {self.check_interval_minutes}분\n"
        message += f"매수 대기시간: {self.buy_delay_minutes}분\n"
        message += f"매도 대기시간: {self.sell_delay_minutes}분\n"
        message += f"매수 비율: {(self.buy_rate*100):.2f}%\n"
        message += f"매도 비율: {(self.sell_rate*100):.2f}%\n"
        message += f"RSI 인터벌: {self.rsi_interval}\n"
        message += f"MACD 인터벌: {self.macd_interval}\n"
        message += f"매수 신호(RSI 과매도): {list(self.rsi_strategies.values())[0].rsi_oversold} 이하\n"
        message += f"매도 신호(RSI 과매수): {list(self.rsi_strategies.values())[0].rsi_overbought} 이상 + MACD 골든크로스\n\n"

        if not stocks:
            message += "현재 보유 종목이 없습니다."
            return message
        
        # 계좌 요약 정보 (summary가 있는 경우만)
        if summary:
            cash_balance = summary.get('frcr_buy_amt_smtl1', '0')  # 외화매수금액합계
            total_eval_amt = summary.get('tot_evlu_pfls_amt', '0')  # 총평가손익금액
            total_eval_rate = summary.get('tot_pftrt', '0')  # 총수익률
            
            message += f"💰 <b>계좌 요약</b>\n"
            message += f"매입금액: {float(cash_balance):,.0f}원\n"
            if total_eval_amt != '0':
                message += f"평가손익: {float(total_eval_amt):,.0f}원\n"
            if total_eval_rate != '0':
                message += f"수익률: {float(total_eval_rate):+.2f}%\n"
            message += "\n"
        
        # 보유 종목별 상세 정보
        message += f"📈 <b>보유 종목 ({len(stocks)}개)</b>\n"
        
        for i, stock in enumerate(stocks, 1):
            ticker = stock.get('ovrs_pdno', '')           # 종목코드
            name = stock.get('ovrs_item_name', '')        # 종목명
            qty = stock.get('ord_psbl_qty', '0')          # 주문가능수량
            avg_price = stock.get('pchs_avg_pric', '0')   # 매입평균가격
            current_price = stock.get('now_pric2', '0')         # 현재가
            eval_amt = stock.get('ovrs_stck_evlu_amt', '0')      # 해외주식평가금액
            profit_loss = stock.get('frcr_evlu_pfls_amt', '0')  # 외화평가손익금액
            profit_rate = stock.get('evlu_pfls_rt', '0')     # 평가손익율
            
            # 손익에 따른 이모지
            if float(profit_loss) < 0:
                profit_emoji = "🔵"
            elif float(profit_loss) > 0:
                profit_emoji = "🔴"
            else:
                profit_emoji = "⚫"
            
            message += f"{profit_emoji} <b>{ticker}</b> ({name[:15]}{'...' if len(name) > 15 else ''})\n"
            message += f"보유: {int(float(qty)):,}주\n"
            message += f"매입가: ${float(avg_price):.2f}\n"
            message += f"현재가: ${float(current_price):.2f}\n"
            message += f"평가손익: ${float(profit_loss):,.2f}\n"
            message += f"수익률: {float(profit_rate):+.2f}%\n"
            
            if i < len(stocks):  # 마지막 종목이 아니면 개행 추가
                message += "\n"
        
        return message
    
    def addOrderToTracker(self, order_no, ticker, order_type, total_qty, price, market):
        """주문 추적 시스템에 새 주문 추가"""
        self.active_orders[order_no] = {
            'ticker': ticker,
            'order_type': order_type,
            'total_qty': total_qty,
            'executed_qty': 0,
            'remaining_qty': total_qty,
            'price': price,
            'market': market
        }
        self.logger.info(f"주문 추적 추가: {order_no} - {ticker} {order_type} {total_qty}주")
    
    def updateOrderExecution(self, order_no, executed_qty):
        """주문 체결량 업데이트"""
        if order_no in self.active_orders:
            order = self.active_orders[order_no]
            order['executed_qty'] += executed_qty
            order['remaining_qty'] = order['total_qty'] - order['executed_qty']
            
            self.logger.info(f"체결량 업데이트: {order_no} - 체결: {executed_qty}주, 누적: {order['executed_qty']}주, 미체결: {order['remaining_qty']}주")
            
            # 모든 주문이 체결되면 추적에서 제거
            if order['remaining_qty'] <= 0:
                self.logger.info(f"주문 완전 체결: {order_no} - {order['ticker']} 추적 종료")
                del self.active_orders[order_no]
                return True  # 완전 체결
                
        return False  # 미완결 또는 주문번호 없음
    
    def getOrderExecutionInfo(self, order_no):
        """주문 체결 정보 조회"""
        return self.active_orders.get(order_no, None)
    
    def clearCompletedOrders(self, ticker=None):
        """완료된 주문들 정리 (특정 종목 또는 전체)"""
        to_remove = []
        for order_no, order in self.active_orders.items():
            if ticker is None or order['ticker'] == ticker:
                if order['remaining_qty'] <= 0:
                    to_remove.append(order_no)
        
        for order_no in to_remove:
            del self.active_orders[order_no]
            
        if to_remove:
            self.logger.info(f"완료된 주문 정리: {len(to_remove)}개 주문 제거")
   
    def hasUnfilledOrders(self, ticker, market="NASD"):
        """특정 종목의 미체결 주문 존재 여부를 주문체결내역 API로 확인

        주의: 모의계좌는 API 제약으로 settle_div가 강제(전체)될 수 있습니다.
        """
        try:
            parse_market = self.kis_base.changeMarketCode(market, length=4)
            # 미체결만 조회 (실계좌에서는 정확히 필터됨). 페이징은 내부에서 처리(fetch_all=True).
            orders = self.kis_account.getOverseasOrderHistory(
                ticker=ticker,
                settle_div="02",  # 02: 미체결
                market=parse_market,
                fetch_all=True
            )

            # 모의계좌에서는 settle_div 필터가 적용되지 않으므로
            # 응답 데이터에서 nccs_qty(미체결수량) 기준으로 재필터링
            unfilled = []
            if isinstance(orders, list):
                for o in orders:
                    qty_str = str(o.get('nccs_qty', '0')).replace(',', '').strip()
                    try:
                        qty = int(float(qty_str)) if qty_str else 0
                    except Exception:
                        qty = 0
                    if qty > 0:
                        unfilled.append(o)

            count = len(unfilled)
            if count > 0:
                self.logger.info(f"미체결 주문 발견: {ticker} - {count}건")
                # 상세 로그는 과도한 출력 방지를 위해 상위 3건만 표시
                for order in unfilled[:3]:
                    self.logger.info(f"  주문번호: {order.get('odno', '')}, 미체결수량: {order.get('nccs_qty', '0')}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"미체결 주문 조회 오류: {e}")
            return False

    def syncActiveOrders(self):
        """계좌의 미체결 주문을 조회해 active_orders를 초기화"""
        synced = 0
        for ticker, market in self.trading_tickers.items():
            try:
                parse_market = self.kis_base.changeMarketCode(market, length=4)
                orders = self.kis_account.getOverseasOrderHistory(
                    ticker=ticker,
                    settle_div="02",  # 미체결
                    market=parse_market,
                    fetch_all=True
                )

                # nccs_qty(미체결수량) 기준 필터링 (모의계좌 호환)
                unfilled = []
                if isinstance(orders, list):
                    for o in orders:
                        qty_str = str(o.get('nccs_qty', '0')).replace(',', '').strip()
                        try:
                            qty = int(float(qty_str)) if qty_str else 0
                        except Exception:
                            qty = 0
                        if qty > 0:
                            unfilled.append(o)

                for o in unfilled:
                    order_no = str(o.get('odno', '')).strip()
                    if not order_no:
                        continue
                    if order_no in self.active_orders:
                        continue

                    # 주문 종류 매핑
                    bs = o.get('sll_buy_dvsn_cd', '')
                    order_type = '매수' if bs == '02' else ('매도' if bs == '01' else f"주문({bs})")

                    # 수량 계산
                    rem_qty_str = str(o.get('nccs_qty', '0')).replace(',', '').strip()
                    try:
                        remaining_qty = int(float(rem_qty_str)) if rem_qty_str else 0
                    except Exception:
                        remaining_qty = 0

                    total_qty = None
                    for key in ['tot_ord_qty', 'ord_qty']:
                        if key in o:
                            try:
                                total_qty = int(str(o.get(key, '0')).replace(',', '').strip())
                                break
                            except Exception:
                                total_qty = None
                    if not total_qty or total_qty < remaining_qty:
                        total_qty = remaining_qty

                    executed_qty = max(total_qty - remaining_qty, 0)

                    # 가격(가능한 경우만)
                    price = 0.0
                    for pkey in ['ovrs_ord_unpr', 'ord_unpr']:
                        if pkey in o:
                            try:
                                price = float(str(o.get(pkey, '0')).replace(',', '').strip())
                                break
                            except Exception:
                                price = 0.0

                    # 추적 테이블에 반영
                    self.active_orders[order_no] = {
                        'ticker': ticker,
                        'order_type': order_type,
                        'total_qty': total_qty,
                        'executed_qty': executed_qty,
                        'remaining_qty': remaining_qty,
                        'price': price,
                        'market': market
                    }
                    synced += 1
            except Exception as e:
                self.logger.error(f"{ticker} 미체결 동기화 오류: {e}")

        if synced:
            self.logger.info(f"시작 시 미체결 주문 {synced}건 동기화 완료")

    async def handle_execution_notification(self, execution_info):
        """체결통보 처리 함수"""
        try:
            self.logger.info("🎉 === 실시간 체결통보 수신 ===")
            
            # 체결통보 데이터 파싱
            ticker = execution_info.get('ticker', 'N/A')
            buy_sell_gb = execution_info.get('buy_sell_gb', '')
            execution_qty = execution_info.get('execution_qty', '0')
            execution_price = execution_info.get('execution_price', '0')
            execution_time = execution_info.get('execution_time', 'N/A')
            order_no = execution_info.get('order_no', 'N/A')
            execution_yn = execution_info.get('execution_yn', 'N/A')
            account_no = execution_info.get('account_no', 'N/A')
            stock_name = execution_info.get('stock_name', 'N/A')
            
            # 매수/매도 구분
            trade_type = ""
            if buy_sell_gb == '02':  # 매수
                trade_type = "매수"
            elif buy_sell_gb == '01':  # 매도
                trade_type = "매도"
            else:
                trade_type = f"주문({buy_sell_gb})"
            
            # 체결 금액 계산
            try:
                qty = int(execution_qty)
                price = float(int(execution_price)/10000)
                total_amount = qty * price
            except:
                qty = 0
                price = 0
                total_amount = 0
                        
            # 로거 출력
            self.logger.info(f"종목: {ticker} ({stock_name})")
            self.logger.info(f"{trade_type}: {execution_qty}주 @ ${execution_price}")
            self.logger.info(f"체결금액: ${total_amount:.2f}")
            self.logger.info(f"체결시간: {execution_time}")
            self.logger.info(f"주문번호: {order_no}")
            self.logger.info(f"체결여부: {execution_yn}")
            self.logger.info("===============================")
            
            # 체결 완료인 경우에만 로그 기록
            if execution_yn == '2':  # 체결 완료
                # 주문 추적 정보 먼저 조회 (삭제되기 전에)
                order_info = self.getOrderExecutionInfo(order_no)
                
                # 주문 추적 정보 업데이트
                is_fully_executed = self.updateOrderExecution(order_no, qty)
                
                # 체결 로그 기록
                if order_info:
                    executed_qty = order_info['executed_qty'] + qty  # 현재 체결량 포함
                    total_order_qty = order_info['total_qty']
                    remaining_qty = total_order_qty - executed_qty
                    execution_rate = (executed_qty / total_order_qty) * 100
                    
                    self.logger.info(f"📊 {ticker} {trade_type} 체결: {qty}주 (${total_amount:,.2f}) | "
                                   f"누적: {executed_qty}/{total_order_qty}주 ({execution_rate:.1f}%) | "
                                   f"미체결: {remaining_qty}주")
                    
                    # 전량 체결 완료시에만 텔레그램 메시지 전송
                    if is_fully_executed:
                        flag_type = "📕" if trade_type == "매수" else "📘"
                        telegram_message = f"""<b>{flag_type} [{trade_type}] 전량 체결완료</b>
종목코드: {ticker}
주문번호: {order_no}
총 체결량: {total_order_qty}주 (${total_order_qty * price:,.2f})
현재가: ${price:.2f}
시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                        
                        # 텔레그램 전송
                        self.telegram.sendMessage(telegram_message)
                        self.logger.info(f"🎊 {ticker} {trade_type} 주문 전량 체결 완료: {total_order_qty}주")
                    
                else:
                    # 추적 정보가 없는 경우 기본 로그
                    self.logger.info(f"📊 {ticker} {trade_type} 체결: {qty}주 (${total_amount:,.2f})")
            
            elif execution_yn == '1':  # 접수
                self.logger.info(f"{ticker} 주문 접수됨 - 체결 대기 중")
            else:
                self.logger.info(f"{ticker} 기타 상태: {execution_yn}")
                
        except Exception as e:
            error_msg = f"체결통보 처리 중 오류: {e}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            try:
                self.telegram.sendMessage(f"❌ <b>체결통보 처리 오류</b>\n{error_msg}")
            except:
                pass  # 텔레그램 전송 실패시에도 계속 진행

    def getBotStatus(self):
        """봇 현재 상태 반환"""
        rsi_strategies_status = {}
        macd_strategies_status = {}
        
        for ticker, rsi_strategy in self.rsi_strategies.items():
            rsi_strategies_status[ticker] = rsi_strategy.getStrategyStatus()
            
        for ticker, macd_strategy in self.macd_strategies.items():
            macd_strategies_status[ticker] = macd_strategy.getStrategyStatus()
        
        return {
            "is_running": self.is_running,
            "start_time": self.start_time,
            "total_trades": self.total_trades,
            "is_market_hours": self.isMarketHours(),
            "trading_tickers": self.trading_tickers,
            "rsi_strategies": rsi_strategies_status,
            "macd_strategies": macd_strategies_status
        }
