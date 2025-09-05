import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from kis_price import KisPrice
from utils.logger_util import LoggerUtil
from utils.price_history import PriceHistory


class RSIStrategy:
    """RSI 기반 매매 전략 클래스"""
    
    def __init__(self, 
                 ticker: str = "TQQQ",
                 market: str = "NAS", 
                 rsi_period: int = 14,
                 rsi_oversold: float = 30.0,
                 rsi_overbought: float = 70.0,
                 buy_rate: float = 0.05,
                 sell_rate: float = 0.05):
        
        # 로거 초기화
        self.logger = LoggerUtil().get_logger()
        
        self.ticker = ticker
        self.market = market
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.buy_rate = buy_rate
        self.sell_rate = sell_rate
        
        # 가격 히스토리
        self.price_history = PriceHistory(max_length=200)
        
        # KIS 가격 조회 객체
        self.kis_price = KisPrice()
    
    def loadHistoricalData(self, days: int = 30):
        """과거 데이터 로드 (장 시작 전 호출)"""
        try:
            # 일봉 데이터 조회 (RSI 계산은 반드시 일봉으로만)
            chart_data = self.kis_price.getDailyPrice(
                market=self.market,
                ticker=self.ticker,
                base_date=""  # 최근 데이터
            )
            
            if not chart_data:
                raise Exception(f"{self.market}:{self.ticker} 일봉 데이터 조회 실패 - RSI 계산을 위해서는 일봉 데이터가 필수입니다")
            
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
            
            # RSI 계산을 위한 최소 데이터 확인
            if self.price_history.getLength() < self.rsi_period + 1:
                raise Exception(f"{self.market}:{self.ticker} 일봉 데이터 부족 (현재: {self.price_history.getLength()}개, 필요: {self.rsi_period + 1}개) - RSI 계산을 위해서는 충분한 일봉 데이터가 필요합니다")
            
            self.logger.info(f"{self.market}:{self.ticker} 총 {self.price_history.getLength()}개의 일봉 데이터 로드 완료")
            return True
            
        except Exception as e:
            self.logger.error(f"일봉 데이터 로드 실패: {e}")
            raise e
    
    
    def updatePrice(self, price: float):
        """실시간 가격 업데이트"""
        self.price_history.addPrice(price)
    
    def getCurrentRsi(self):
        """현재 RSI 값 계산"""
        prices = self.price_history.getPrices()
        
        if len(prices) < self.rsi_period + 1:
            return None
        
        try:
            # 판다스 Series로 변환
            price_series = pd.Series(prices)
            
            # RSI 계산
            rsi_indicator = RSIIndicator(close=price_series, window=self.rsi_period)
            rsi_values = rsi_indicator.rsi()
            
            # 최신 RSI 값 반환
            return rsi_values.iloc[-1]
        
        except Exception as e:
            self.logger.error(f"RSI 계산 중 오류 발생: {e}")
            return None
    
    def getBuySignal(self):
        """순수 RSI 기반 매수 신호 판단"""
        rsi = self.getCurrentRsi()
        if rsi is None:
            return False
        
        return rsi <= self.rsi_oversold
    
    def getSellSignal(self):
        """순수 RSI 기반 매도 신호 판단"""
        rsi = self.getCurrentRsi()
        if rsi is None:
            return False
        
        return rsi >= self.rsi_overbought
    
    def getStrategyStatus(self):
        """전략 현재 상태 반환"""
        rsi = self.getCurrentRsi()
        prices = self.price_history.getPrices()
        current_price = prices[-1] if prices else None
        
        return {
            "ticker": self.ticker,
            "current_price": current_price,
            "current_rsi": rsi,
            "data_length": self.price_history.getLength(),
            "buy_signal": self.getBuySignal(),
            "sell_signal": self.getSellSignal(),
            "rsi_oversold": self.rsi_oversold,
            "rsi_overbought": self.rsi_overbought
        }