import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from kis_price import KisPrice
from utils.logger_util import LoggerUtil


class PriceHistory:
    """가격 데이터 히스토리 관리 클래스"""
    
    def __init__(self, max_length: int = 100):
        self.max_length = max_length
        self.prices = []
        self.timestamps = []
    
    def add_price(self, price: float, timestamp: datetime = None):
        """새로운 가격 데이터 추가"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.prices.append(price)
        self.timestamps.append(timestamp)
        
        # 최대 길이 유지
        if len(self.prices) > self.max_length:
            self.prices.pop(0)
            self.timestamps.pop(0)
    
    def get_prices(self):
        """가격 리스트 반환"""
        return self.prices.copy()
    
    def get_dataframe(self):
        """판다스 DataFrame으로 반환"""
        return pd.DataFrame({
            'timestamp': self.timestamps,
            'close': self.prices
        })
    
    def get_length(self):
        """현재 저장된 데이터 길이"""
        return len(self.prices)


class RSICalculator:
    """RSI 계산 클래스"""
    
    def __init__(self, period: int = 14):
        self.period = period
    
    def calculate_rsi(self, prices):
        """RSI 계산
        Args:
            prices: 가격 리스트 (최소 period+1 개 필요)
        Returns:
            RSI 값 (0-100) 또는 None (데이터 부족시)
        """
        if len(prices) < self.period + 1:
            return None
        
        try:
            # 판다스 Series로 변환
            price_series = pd.Series(prices)
            
            # RSI 계산
            rsi_indicator = RSIIndicator(close=price_series, window=self.period)
            rsi_values = rsi_indicator.rsi()
            
            # 최신 RSI 값 반환
            return rsi_values.iloc[-1]
        
        except Exception as e:
            self.logger.error(f"RSI 계산 중 오류 발생: {e}")
            return None


class RSIStrategy:
    """RSI 기반 매매 전략 클래스"""
    
    def __init__(self, 
                 symbol: str = "TQQQ",
                 market: str = "NAS", 
                 rsi_period: int = 14,
                 rsi_oversold: float = 30.0,
                 rsi_overbought: float = 70.0,
                 buy_percentage: float = 0.05,
                 sell_percentage: float = 0.05,
                 trading_bot=None):
        
        # 로거 초기화
        self.logger = LoggerUtil().get_logger()
        
        self.symbol = symbol
        self.market = market
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.buy_percentage = buy_percentage
        self.sell_percentage = sell_percentage
        
        # 가격 히스토리 및 RSI 계산기
        self.price_history = PriceHistory(max_length=200)
        self.rsi_calculator = RSICalculator(period=rsi_period)
        
        # 마지막 매수/매도 시간 추적 (5분 쿨다운)
        self.last_buy_time = None
        self.last_sell_time = None
        self.cooldown_minutes = 5
        
        # TradingBot 참조 (쿨다운 체크용)
        self.trading_bot = trading_bot
        
        # KIS 가격 조회 객체
        self.kis_price = KisPrice()
    
    def load_historical_data(self, days: int = 30):
        """과거 데이터 로드 (장 시작 전 호출)"""
        try:
            self.logger.info(f"실제 일봉 데이터 로딩 중...")
            
            # 일봉 데이터 조회 (더 안정적인 RSI 계산을 위해)
            chart_data = self.kis_price.getDailyPrice(
                market=self.market,
                symbol=self.symbol,
                base_date=""  # 최근 데이터
            )
            
            if not chart_data:
                self.logger.warning("일봉 데이터 조회 실패, 분봉 데이터로 시도...")
                return self._load_minute_data()
            
            # 일봉 데이터 처리 (시간순으로 정렬)
            for data in reversed(chart_data):  # 최신 데이터가 먼저 오므로 역순으로 처리
                try:
                    # 다양한 종가 필드명 시도
                    price = None
                    for field in ['clos', 'close', 'last', 'c']:
                        if field in data and data[field]:
                            price = float(data[field])
                            break
                    
                    if price and price > 0:
                        self.price_history.add_price(price)
                except (ValueError, KeyError):
                    continue
            
            self.logger.info(f"총 {self.price_history.get_length()}개의 일봉 데이터 로드 완료")
            
            # 데이터가 부족하면 분봉으로 보완
            if self.price_history.get_length() < 15:
                self.logger.warning("일봉 데이터 부족, 분봉으로 보완...")
                return self._load_minute_data()
            
            return True
            
        except Exception as e:
            self.logger.error(f"데이터 로드 중 오류 발생: {e}")
            raise e
    
    def _load_minute_data(self):
        """분봉 데이터 로드 (일봉 실패시 대체)"""
        try:
            self.logger.info("분봉 데이터로 RSI 계산...")
            
            chart_data = self.kis_price.getMinuteChartPrice(
                market=self.market,
                symbol=self.symbol,
                time_frame="5",  # 5분봉으로 노이즈 줄이기
                include_prev_day="1"
            )
            
            if not chart_data:
                return self._load_dummy_data()
            
            # 5분봉 데이터 처리
            for data in reversed(chart_data):
                try:
                    price = None
                    for field in ['last', 'clos', 'close', 'c']:
                        if field in data and data[field]:
                            price = float(data[field])
                            break
                    
                    if price and price > 0:
                        self.price_history.add_price(price)
                except (ValueError, KeyError):
                    continue
            
            self.logger.info(f"총 {self.price_history.get_length()}개의 분봉 데이터 로드 완료")
            return self.price_history.get_length() >= 15
            
        except Exception as e:
            self.logger.error(f"분봉 데이터 로드 실패: {e}")
            raise e
    
    def update_price(self, price: float):
        """실시간 가격 업데이트"""
        self.price_history.add_price(price)
    
    def get_current_rsi(self):
        """현재 RSI 값 계산"""
        prices = self.price_history.get_prices()
        return self.rsi_calculator.calculate_rsi(prices)
    
    def should_buy(self):
        """매수 신호 판단"""
        # 실제 주문 기록 기반 쿨다운 체크
        if self.trading_bot:
            last_buy_time = self.trading_bot.get_last_buy_order_time()
            if last_buy_time:
                from utils.datetime_util import DateTimeUtil
                time_diff = DateTimeUtil.get_time_diff_minutes(last_buy_time)
                if time_diff < self.trading_bot.cooldown_minutes:
                    return False
        
        rsi = self.get_current_rsi()
        if rsi is None:
            return False
        
        return rsi <= self.rsi_oversold
    
    def should_sell(self):
        """매도 신호 판단"""
        # 실제 주문 기록 기반 쿨다운 체크 (매도는 매수 기준으로 체크)
        if self.trading_bot:
            last_buy_time = self.trading_bot.get_last_buy_order_time()
            if last_buy_time:
                from utils.datetime_util import DateTimeUtil
                time_diff = DateTimeUtil.get_time_diff_minutes(last_buy_time)
                if time_diff < self.trading_bot.cooldown_minutes:
                    return False
        
        rsi = self.get_current_rsi()
        if rsi is None:
            return False
        
        return rsi >= self.rsi_overbought
    
    def _is_in_cooldown(self, last_time):
        """쿨다운 시간 체크"""
        if last_time is None:
            return False
        
        return datetime.now() - last_time < timedelta(minutes=self.cooldown_minutes)
    
    def execute_buy(self):
        """매수 실행 기록"""
        self.last_buy_time = datetime.now()
        return True
    
    def execute_sell(self):
        """매도 실행 기록"""
        self.last_sell_time = datetime.now()
        return True
    
    def get_strategy_status(self):
        """전략 현재 상태 반환"""
        rsi = self.get_current_rsi()
        prices = self.price_history.get_prices()
        current_price = prices[-1] if prices else None
        
        return {
            "symbol": self.symbol,
            "current_price": current_price,
            "current_rsi": rsi,
            "data_length": self.price_history.get_length(),
            "last_buy_time": self.last_buy_time,
            "last_sell_time": self.last_sell_time,
            "buy_signal": self.should_buy(),
            "sell_signal": self.should_sell(),
            "rsi_oversold": self.rsi_oversold,
            "rsi_overbought": self.rsi_overbought
        }