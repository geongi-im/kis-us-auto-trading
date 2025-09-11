import os
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
        
        # 환경변수에서 시간 간격 설정 로드
        self.interval = os.getenv("MACD_INTERVAL")
        
        # KIS 가격 조회 객체
        self.kis_price = KisPrice()
    
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
                time_frame=self.interval,
                include_prev_day="1"
            )
            
            if not chart_data or len(chart_data) < required_periods:
                self.logger.warning(f"{self.ticker} 분봉 데이터 부족: {len(chart_data) if chart_data else 0}개")
                return False
            
            # 가격 데이터 추출 (시간순 정렬)
            prices = []
            for data in reversed(chart_data):
                try:
                    price = float(data['last']) if 'last' in data and data['last'] else None
                    if price and price > 0:
                        prices.append(price)
                except (ValueError, KeyError):
                    continue
            
            if len(prices) < required_periods:
                return False
            
            # 판다스 Series로 변환
            price_series = pd.Series(prices)
            
            # ta 라이브러리를 사용한 MACD 계산
            macd_line = ta.trend.MACD(close=price_series, 
                                      window_fast=self.fast_period, 
                                      window_slow=self.slow_period, 
                                      window_sign=self.signal_period).macd()
            
            signal_line = ta.trend.MACD(close=price_series, 
                                       window_fast=self.fast_period, 
                                       window_slow=self.slow_period, 
                                       window_sign=self.signal_period).macd_signal()
            
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
    
    def getCurrentMacd(self):
        """현재 MACD 값 계산 (실시간 분봉 데이터 조회)"""
        try:
            # 충분한 분봉 데이터 조회
            required_periods = self.slow_period + self.signal_period + 5
            
            chart_data = self.kis_price.getMinuteChartPrice(
                market=self.market,
                ticker=self.ticker,
                time_frame=self.interval,
                include_prev_day="1"
            )
            
            if not chart_data or len(chart_data) < required_periods:
                return None
            
            # 가격 데이터 추출 (시간순 정렬)
            prices = []
            for data in reversed(chart_data):
                try:
                    price = float(data['last']) if 'last' in data and data['last'] else None
                    if price and price > 0:
                        prices.append(price)
                except (ValueError, KeyError):
                    continue
            
            # ta 라이브러리를 사용한 MACD 계산
            price_series = pd.Series(prices)
            
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
            self.logger.error(f"현재 MACD 계산 중 오류: {e}")
            return None
    
    def _getChartData(self, required_periods):
        """설정된 간격에 따라 차트 데이터 조회"""
        if self.interval == "day":
            return self.kis_price.getDailyPrice(
                market=self.market,
                ticker=self.ticker,
                base_date=""
            )
        else:
            return self.kis_price.getMinuteChartPrice(
                market=self.market,
                ticker=self.ticker,
                time_frame=self.interval,
                include_prev_day="1"
            )
    
    def _extractPrices(self, chart_data):
        """차트 데이터에서 가격 추출"""
        prices = []
        price_field = 'clos' if self.interval == "day" else 'last'
        
        for data in reversed(chart_data):
            try:
                price = float(data[price_field]) if price_field in data and data[price_field] else None
                if price and price > 0:
                    prices.append(price)
            except (ValueError, KeyError):
                continue
        
        return prices

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
            "interval": self.interval,
            "data_source": "daily" if self.interval == "day" else f"{self.interval}min"
        }