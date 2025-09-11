import os
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from kis_price import KisPrice
from utils.logger_util import LoggerUtil


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
        
        # 환경변수에서 시간 간격 설정 로드
        self.interval = os.getenv("RSI_INTERVAL")
        self.logger.info(f"{ticker} RSI 시간 간격: {self.interval}")
        
        # KIS 가격 조회 객체
        self.kis_price = KisPrice()
    
    def validateDataConnection(self):
        """데이터 연결 상태 확인 (선택적 호출)"""
        try:
            # 간단한 데이터 연결 테스트
            chart_data = self.kis_price.getDailyPrice(
                market=self.market,
                ticker=self.ticker,
                base_date=""  # 최근 데이터
            )
            
            if not chart_data:
                self.logger.warning(f"{self.market}:{self.ticker} 일봉 데이터 조회 실패 - API 연결 상태를 확인하세요")
                return False
            
            if len(chart_data) < self.rsi_period + 1:
                self.logger.warning(f"{self.market}:{self.ticker} 일봉 데이터 부족 (현재: {len(chart_data)}개, 필요: {self.rsi_period + 1}개)")
                return False
                
            self.logger.info(f"{self.market}:{self.ticker} 일봉 데이터 연결 확인 완료: {len(chart_data)}개 데이터")
            return True
            
        except Exception as e:
            self.logger.error(f"데이터 연결 확인 실패: {e}")
            return False
    
    def getCurrentRsi(self):
        """환경변수 기반 RSI 값 계산"""
        if self.interval == "day":
            return self._getRsiFromDaily()
        else:
            return self._getRsiFromMinute(self.interval)
    
    def _getRsiFromDaily(self):
        """일봉 데이터로 RSI 계산"""
        try:
            required_periods = self.rsi_period + 5
            
            chart_data = self.kis_price.getDailyPrice(
                market=self.market,
                ticker=self.ticker,
                base_date=""
            )
            
            if not chart_data or len(chart_data) < required_periods:
                self.logger.warning(f"{self.ticker} 일봉 데이터 부족: {len(chart_data) if chart_data else 0}개")
                return None
            
            # 가격 데이터 추출
            prices = []
            for data in reversed(chart_data):
                try:
                    price = float(data['clos']) if 'clos' in data and data['clos'] else None
                    if price and price > 0:
                        prices.append(price)
                except (ValueError, KeyError):
                    continue
            
            if len(prices) < required_periods:
                return None
            
            return self._calculateRsi(prices)
            
        except Exception as e:
            self.logger.error(f"일봉 RSI 계산 중 오류: {e}")
            return None
    
    def _getRsiFromMinute(self, minute_frame):
        """분봉 데이터로 RSI 계산"""
        try:
            required_periods = self.rsi_period + 5
            
            chart_data = self.kis_price.getMinuteChartPrice(
                market=self.market,
                ticker=self.ticker,
                time_frame=minute_frame,
                include_prev_day="1"
            )
            
            if not chart_data or len(chart_data) < required_periods:
                self.logger.warning(f"{self.ticker} {minute_frame}분봉 데이터 부족: {len(chart_data) if chart_data else 0}개")
                return None
            
            # 가격 데이터 추출
            prices = []
            for data in reversed(chart_data):
                try:
                    price = float(data['last']) if 'last' in data and data['last'] else None
                    if price and price > 0:
                        prices.append(price)
                except (ValueError, KeyError):
                    continue
            
            if len(prices) < required_periods:
                return None
            
            return self._calculateRsi(prices)
            
        except Exception as e:
            self.logger.error(f"{minute_frame}분봉 RSI 계산 중 오류: {e}")
            return None
    
    def _calculateRsi(self, prices):
        """가격 리스트로 RSI 계산"""
        try:
            price_series = pd.Series(prices)
            rsi_indicator = RSIIndicator(close=price_series, window=self.rsi_period)
            rsi_values = rsi_indicator.rsi()
            return rsi_values.iloc[-1]
        except Exception as e:
            self.logger.error(f"RSI 계산 오류: {e}")
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
    
    def getCurrentPrice(self):
        """현재 가격 조회 (설정된 간격에 따라)"""
        try:
            if self.interval == "day":
                chart_data = self.kis_price.getDailyPrice(
                    market=self.market,
                    ticker=self.ticker,
                    base_date=""
                )
                if chart_data:
                    latest_data = chart_data[0]
                    return float(latest_data['clos']) if 'clos' in latest_data and latest_data['clos'] else None
            else:
                chart_data = self.kis_price.getMinuteChartPrice(
                    market=self.market,
                    ticker=self.ticker,
                    time_frame=self.interval,
                    include_prev_day="1"
                )
                if chart_data:
                    latest_data = chart_data[0]
                    return float(latest_data['last']) if 'last' in latest_data and latest_data['last'] else None
            
            return None
            
        except Exception as e:
            self.logger.error(f"현재 가격 조회 오류: {e}")
            return None
    
    def getStrategyStatus(self):
        """전략 현재 상태 반환"""
        rsi = self.getCurrentRsi()
        current_price = self.getCurrentPrice()
        
        return {
            "ticker": self.ticker,
            "current_price": current_price,
            "current_rsi": rsi,
            "interval": self.interval,
            "data_source": "daily" if self.interval == "day" else f"{self.interval}min",
            "buy_signal": self.getBuySignal(),
            "sell_signal": self.getSellSignal(),
            "rsi_oversold": self.rsi_oversold,
            "rsi_overbought": self.rsi_overbought,
            "rsi_period": self.rsi_period
        }