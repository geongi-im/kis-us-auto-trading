import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from kis_price import KisPrice
from utils.logger_util import LoggerUtil
from utils.price_history import PriceHistory


class MACDStrategy:
    """MACD 기반 매매 전략 클래스"""
    
    def __init__(self, 
                 ticker: str = "TQQQ",
                 market: str = "NAS", 
                 fast_period: int = 12,
                 slow_period: int = 26,
                 signal_period: int = 9,
                 minute_timeframe: str = "5",
                 buy_rate: float = 0.05,
                 sell_rate: float = 0.05):
        
        # 로거 초기화
        self.logger = LoggerUtil().get_logger()
        
        self.ticker = ticker
        self.market = market
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.minute_timeframe = minute_timeframe
        self.buy_rate = buy_rate
        self.sell_rate = sell_rate
        
        # KIS 가격 조회 객체
        self.kis_price = KisPrice()
    
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
    
    def isGoldenCross(self, prices):
        """MACD 골든크로스 상태 판단 (현재 상태만)
        Args:
            prices: 가격 리스트
        Returns:
            bool: 현재 골든크로스 상태이면 True
        """
        macd_data = self.calculateMacd(prices)
        if not macd_data or macd_data['macd'] is None or macd_data['signal'] is None:
            return False
            
        # MACD가 Signal보다 위에 있으면 골든크로스 상태
        return macd_data['macd'] > macd_data['signal']
    
    def hasRecentGoldenCross(self, lookback_periods=3):
        """최근 N봉 내 MACD 골든크로스 발생 여부 체크 (실시간 분봉 데이터 조회)
        Args:
            lookback_periods: 확인할 봉의 수 (기본값: 3)
        Returns:
            bool: 최근 N봉 내 골든크로스 발생했으면 True
        """
        try:
            # 충분한 분봉 데이터 조회 (MACD 계산 + 골든크로스 확인용)
            required_periods = self.slow_period + self.signal_period + lookback_periods + 5
            
            chart_data = self.kis_price.getMinuteChartPrice(
                market=self.market,
                ticker=self.ticker,
                time_frame=self.minute_timeframe,
                include_prev_day="1"
            )
            
            if not chart_data or len(chart_data) < required_periods:
                self.logger.warning(f"{self.ticker} 분봉 데이터 부족: {len(chart_data) if chart_data else 0}개")
                return False
            
            # 가격 데이터 추출 (시간순 정렬)
            prices = []
            for data in reversed(chart_data):
                try:
                    price = None
                    for field in ['last', 'clos', 'close', 'c']:
                        if field in data and data[field]:
                            price = float(data[field])
                            break
                    if price and price > 0:
                        prices.append(price)
                except (ValueError, KeyError):
                    continue
            
            if len(prices) < required_periods:
                return False
            
            # 판다스 Series로 변환
            price_series = pd.Series(prices)
            
            # MACD 계산
            exp1 = price_series.ewm(span=self.fast_period).mean()
            exp2 = price_series.ewm(span=self.slow_period).mean()
            macd_line = exp1 - exp2
            signal_line = macd_line.ewm(span=self.signal_period).mean()
            
            # 최근 N봉 동안 골든크로스 발생 여부 체크
            for i in range(1, lookback_periods + 1):
                if len(macd_line) < i + 1 or len(signal_line) < i + 1:
                    continue
                    
                # 현재봉: MACD > Signal, 이전봉: MACD <= Signal 이면 골든크로스 발생
                current_macd = macd_line.iloc[-i]
                current_signal = signal_line.iloc[-i]
                prev_macd = macd_line.iloc[-i-1] 
                prev_signal = signal_line.iloc[-i-1]
                
                if (current_macd > current_signal and 
                    prev_macd <= prev_signal):
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"최근 골든크로스 체크 중 오류: {e}")
            return False
    
    def isDeadCross(self, prices):
        """MACD 데드크로스 상태 판단 (현재 상태만)
        Args:
            prices: 가격 리스트
        Returns:
            bool: 현재 데드크로스 상태이면 True
        """
        macd_data = self.calculateMacd(prices)
        if not macd_data or macd_data['macd'] is None or macd_data['signal'] is None:
            return False
            
        # MACD가 Signal보다 아래에 있으면 데드크로스 상태
        return macd_data['macd'] < macd_data['signal']
    
    def loadHistoricalData(self, days: int = 30):
        """MACD는 실시간 분봉 조회 방식이므로 초기 데이터 로드 불필요"""
        self.logger.info(f"{self.ticker} MACD 전략: 실시간 분봉 계산 방식으로 초기 데이터 로드 생략")
        return True
    
    def updatePrice(self, price: float):
        """MACD는 실시간 분봉 조회 방식이므로 가격 업데이트 불필요"""
        pass
    
    def getCurrentMacd(self):
        """현재 MACD 값 계산 (실시간 분봉 데이터 조회)"""
        try:
            # 충분한 분봉 데이터 조회
            required_periods = self.slow_period + self.signal_period + 5
            
            chart_data = self.kis_price.getMinuteChartPrice(
                market=self.market,
                ticker=self.ticker,
                time_frame=self.minute_timeframe,
                include_prev_day="1"
            )
            
            if not chart_data or len(chart_data) < required_periods:
                return None
            
            # 가격 데이터 추출 (시간순 정렬)
            prices = []
            for data in reversed(chart_data):
                try:
                    price = None
                    for field in ['last', 'clos', 'close', 'c']:
                        if field in data and data[field]:
                            price = float(data[field])
                            break
                    if price and price > 0:
                        prices.append(price)
                except (ValueError, KeyError):
                    continue
            
            return self.calculateMacd(prices)
            
        except Exception as e:
            self.logger.error(f"현재 MACD 계산 중 오류: {e}")
            return None
    
    def getBuySignal(self):
        """MACD 기반 매수 신호 판단 (골든크로스) - 사용 안함"""
        return False
    
    def getSellSignal(self):
        """MACD 기반 매도 신호 판단 (데드크로스) - 사용 안함"""
        return False
    
    def getStrategyStatus(self):
        """전략 현재 상태 반환"""
        macd_data = self.getCurrentMacd()
        has_recent_golden_cross = self.hasRecentGoldenCross(3)
        
        return {
            "ticker": self.ticker,
            "current_macd": macd_data.get('macd') if macd_data else None,
            "current_signal": macd_data.get('signal') if macd_data else None,
            "current_histogram": macd_data.get('histogram') if macd_data else None,
            "recent_golden_cross": has_recent_golden_cross,
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "signal_period": self.signal_period,
            "minute_timeframe": self.minute_timeframe
        }