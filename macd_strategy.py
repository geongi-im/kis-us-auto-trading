import pandas as pd
import numpy as np
import ta
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
    
    def addPrice(self, price: float, timestamp: datetime = None):
        """새로운 가격 데이터 추가"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.prices.append(price)
        self.timestamps.append(timestamp)
        
        # 최대 길이 유지
        if len(self.prices) > self.max_length:
            self.prices.pop(0)
            self.timestamps.pop(0)
    
    def getPrices(self):
        """가격 리스트 반환"""
        return self.prices.copy()
    
    def getDataframe(self):
        """판다스 DataFrame으로 반환"""
        return pd.DataFrame({
            'timestamp': self.timestamps,
            'close': self.prices
        })
    
    def getLength(self):
        """현재 저장된 데이터 길이"""
        return len(self.prices)


class MACDCalculator:
    """MACD 계산 클래스"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def calculateMacd(self, prices):
        """MACD 계산
        Args:
            prices: 가격 리스트 (최소 slow_period + signal_period 개 필요)
        Returns:
            dict: {'macd': float, 'signal': float, 'histogram': float} 또는 None
        """
        min_required = self.slow_period + self.signal_period
        if len(prices) < min_required:
            return None
        
        try:
            # 판다스 Series로 변환
            price_series = pd.Series(prices)
            
            # ta 라이브러리를 사용한 MACD 계산
            macd_line = ta.trend.MACD(close=price_series, 
                                      window_fast=self.fast_period, 
                                      window_slow=self.slow_period, 
                                      window_sign=self.signal_period).macd()
            
            macd_signal = ta.trend.MACD(close=price_series, 
                                       window_fast=self.fast_period, 
                                       window_slow=self.slow_period, 
                                       window_sign=self.signal_period).macd_signal()
            
            macd_histogram = ta.trend.MACD(close=price_series, 
                                          window_fast=self.fast_period, 
                                          window_slow=self.slow_period, 
                                          window_sign=self.signal_period).macd_diff()
            
            # 최신 값들 반환
            return {
                'macd': macd_line.iloc[-1] if not pd.isna(macd_line.iloc[-1]) else None,
                'signal': macd_signal.iloc[-1] if not pd.isna(macd_signal.iloc[-1]) else None,
                'histogram': macd_histogram.iloc[-1] if not pd.isna(macd_histogram.iloc[-1]) else None
            }
        
        except Exception as e:
            return None
    
    def detectCrosses(self, prices):
        """MACD 골든크로스/데드크로스 검출
        Args:
            prices: 가격 리스트
        Returns:
            dict: {'golden_cross': bool, 'death_cross': bool, 'current_macd': dict}
        """
        min_required = self.slow_period + self.signal_period + 1  # 교차점 검출을 위해 +1
        if len(prices) < min_required:
            return {
                'golden_cross': False,
                'death_cross': False,
                'current_macd': None
            }
        
        try:
            price_series = pd.Series(prices)
            
            # MACD 계산
            macd_line = ta.trend.MACD(close=price_series, 
                                      window_fast=self.fast_period, 
                                      window_slow=self.slow_period, 
                                      window_sign=self.signal_period).macd()
            
            macd_signal = ta.trend.MACD(close=price_series, 
                                       window_fast=self.fast_period, 
                                       window_slow=self.slow_period, 
                                       window_sign=self.signal_period).macd_signal()
            
            # 최근 2개 값으로 교차점 검출
            if len(macd_line) < 2 or pd.isna(macd_line.iloc[-2]) or pd.isna(macd_line.iloc[-1]):
                return {
                    'golden_cross': False,
                    'death_cross': False,
                    'current_macd': self.calculateMacd(prices)
                }
            
            prev_macd = macd_line.iloc[-2]
            curr_macd = macd_line.iloc[-1]
            prev_signal = macd_signal.iloc[-2]
            curr_signal = macd_signal.iloc[-1]
            
            # 골든크로스: MACD가 Signal을 아래에서 위로 돌파
            golden_cross = (prev_macd <= prev_signal) and (curr_macd > curr_signal)
            
            # 데드크로스: MACD가 Signal을 위에서 아래로 돌파
            death_cross = (prev_macd >= prev_signal) and (curr_macd < curr_signal)
            
            return {
                'golden_cross': golden_cross,
                'death_cross': death_cross,
                'current_macd': self.calculateMacd(prices)
            }
            
        except Exception as e:
            return {
                'golden_cross': False,
                'death_cross': False,
                'current_macd': None
            }


class MACDStrategy:
    """MACD 기반 매매 전략 클래스"""
    
    def __init__(self, 
                 ticker: str = "TQQQ",
                 market: str = "NAS", 
                 fast_period: int = 12,
                 slow_period: int = 26,
                 signal_period: int = 9,
                 buy_rate: float = 0.05,
                 sell_rate: float = 0.05):
        
        # 로거 초기화
        self.logger = LoggerUtil().get_logger()
        
        self.ticker = ticker
        self.market = market
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.buy_rate = buy_rate
        self.sell_rate = sell_rate
        
        # 가격 히스토리 및 MACD 계산기
        self.price_history = PriceHistory(max_length=200)
        self.macd_calculator = MACDCalculator(
            fast_period=fast_period, 
            slow_period=slow_period, 
            signal_period=signal_period
        )
        
        # KIS 가격 조회 객체
        self.kis_price = KisPrice()
    
    def loadHistoricalData(self, days: int = 30):
        """과거 데이터 로드 (장 시작 전 호출)"""
        try:
            # 일봉 데이터 조회 (더 안정적인 MACD 계산을 위해)
            chart_data = self.kis_price.getDailyPrice(
                market=self.market,
                ticker=self.ticker,
                base_date=""  # 최근 데이터
            )
            
            if not chart_data:
                self.logger.warning(f"{self.market}:{self.ticker} 일봉 데이터 조회 실패, 분봉 데이터로 시도...")
                return self._loadMinuteData()
            
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
                        self.price_history.addPrice(price)
                except (ValueError, KeyError):
                    continue
            
            self.logger.info(f"{self.market}:{self.ticker} 총 {self.price_history.getLength()}개의 일봉 데이터 로드 완료")
            
            # 데이터가 부족하면 분봉으로 보완
            min_required = self.slow_period + self.signal_period + 5  # 여유분 포함
            if self.price_history.getLength() < min_required:
                self.logger.warning(f"{self.market}:{self.ticker} 일봉 데이터 부족 ({self.price_history.getLength()}개), 분봉으로 보완...")
                return self._loadMinuteData()
            
            return True
            
        except Exception as e:
            self.logger.error(f"데이터 로드 중 오류 발생: {e}")
            raise e
    
    def _loadMinuteData(self):
        """분봉 데이터 로드 (일봉 실패시 대체)"""
        try:
            self.logger.info("분봉 데이터로 MACD 계산...")
            
            chart_data = self.kis_price.getMinuteChartPrice(
                market=self.market,
                ticker=self.ticker,
                time_frame="5",  # 5분봉으로 노이즈 줄이기
                include_prev_day="1"
            )
            
            if not chart_data:
                self.logger.error(f"{self.market} {self.ticker} 종목 분봉 데이터 로드 실패")
                return False
            
            # 5분봉 데이터 처리
            for data in reversed(chart_data):
                try:
                    price = None
                    for field in ['last', 'clos', 'close', 'c']:
                        if field in data and data[field]:
                            price = float(data[field])
                            break
                    
                    if price and price > 0:
                        self.price_history.addPrice(price)
                except (ValueError, KeyError):
                    continue
            
            self.logger.info(f"총 {self.price_history.getLength()}개의 분봉 데이터 로드 완료")
            
            min_required = self.slow_period + self.signal_period + 1
            return self.price_history.getLength() >= min_required
            
        except Exception as e:
            self.logger.error(f"분봉 데이터 로드 실패: {e}")
            raise e
    
    def updatePrice(self, price: float):
        """실시간 가격 업데이트"""
        self.price_history.addPrice(price)
    
    def getCurrentMacd(self):
        """현재 MACD 값 계산"""
        prices = self.price_history.getPrices()
        return self.macd_calculator.calculateMacd(prices)
    
    def getBuySignal(self):
        """MACD 기반 매수 신호 판단 (골든크로스)"""
        prices = self.price_history.getPrices()
        crosses = self.macd_calculator.detectCrosses(prices)
        return crosses.get('golden_cross', False)
    
    def getSellSignal(self):
        """MACD 기반 매도 신호 판단 (데드크로스)"""
        prices = self.price_history.getPrices()
        crosses = self.macd_calculator.detectCrosses(prices)
        return crosses.get('death_cross', False)
    
    def getStrategyStatus(self):
        """전략 현재 상태 반환"""
        prices = self.price_history.getPrices()
        current_price = prices[-1] if prices else None
        macd_data = self.getCurrentMacd()
        crosses = self.macd_calculator.detectCrosses(prices)
        
        return {
            "ticker": self.ticker,
            "current_price": current_price,
            "current_macd": macd_data.get('macd') if macd_data else None,
            "current_signal": macd_data.get('signal') if macd_data else None,
            "current_histogram": macd_data.get('histogram') if macd_data else None,
            "data_length": self.price_history.getLength(),
            "buy_signal": crosses.get('golden_cross', False),
            "sell_signal": crosses.get('death_cross', False),
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "signal_period": self.signal_period
        }