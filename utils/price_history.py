import pandas as pd
from datetime import datetime
from typing import List, Optional

class PriceHistory:
    """가격 데이터 히스토리 관리 클래스
    
    기술적 지표 계산을 위한 가격 데이터를 관리합니다.
    RSI, MACD 등 다양한 전략에서 공통으로 사용할 수 있습니다.
    """
    
    def __init__(self, max_length: int = 100):
        """PriceHistory 초기화
        
        Args:
            max_length: 최대 저장할 데이터 개수 (기본 100개)
        """
        self.max_length = max_length
        self.prices = []
        self.timestamps = []
    
    def addPrice(self, price: float, timestamp: datetime = None):
        """새로운 가격 데이터 추가
        
        Args:
            price: 가격 데이터
            timestamp: 시간 정보 (None시 현재시간 사용)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        self.prices.append(price)
        self.timestamps.append(timestamp)
        
        # 최대 길이 유지 (FIFO 방식)
        if len(self.prices) > self.max_length:
            self.prices.pop(0)
            self.timestamps.pop(0)
    
    def getPrices(self):
        """가격 리스트 반환
        
        Returns:
            가격 데이터 리스트 (복사본)
        """
        return self.prices.copy()
    
    def getTimestamps(self):
        """타임스탬프 리스트 반환
        
        Returns:
            타임스탬프 리스트 (복사본)
        """
        return self.timestamps.copy()
    
    def getDataframe(self):
        """판다스 DataFrame으로 반환
        
        Returns:
            timestamp와 close 컬럼을 가진 DataFrame
        """
        return pd.DataFrame({
            'timestamp': self.timestamps,
            'close': self.prices
        })
    
    def getLength(self):
        """현재 저장된 데이터 길이
        
        Returns:
            저장된 데이터 개수
        """
        return len(self.prices)
    
    def getLatestPrice(self):
        """최신 가격 반환
        
        Returns:
            최신 가격 (데이터가 없으면 None)
        """
        return self.prices[-1] if self.prices else None
    
    def getLatestTimestamp(self):
        """최신 타임스탬프 반환
        
        Returns:
            최신 타임스탬프 (데이터가 없으면 None)
        """
        return self.timestamps[-1] if self.timestamps else None
    
    def clear(self):
        """모든 데이터 삭제"""
        self.prices.clear()
        self.timestamps.clear()
    
    def isEmpty(self):
        """데이터가 비어있는지 확인
        
        Returns:
            True if 데이터가 없음, False otherwise
        """
        return len(self.prices) == 0
    
    def hasMinimumData(self, min_count: int):
        """최소 필요 데이터 개수 확인
        
        Args:
            min_count: 최소 필요한 데이터 개수
            
        Returns:
            True if 최소 데이터 개수를 만족, False otherwise
        """
        return len(self.prices) >= min_count
    
    def getPriceRange(self, start_idx: int = 0, end_idx: int = None):
        """특정 범위의 가격 데이터 반환
        
        Args:
            start_idx: 시작 인덱스 (기본 0)
            end_idx: 종료 인덱스 (None시 마지막까지)
            
        Returns:
            지정된 범위의 가격 데이터
        """
        if end_idx is None:
            end_idx = len(self.prices)
        
        return self.prices[start_idx:end_idx]
    
    def getRecentPrices(self, count: int):
        """최근 N개의 가격 데이터 반환
        
        Args:
            count: 반환할 데이터 개수
            
        Returns:
            최근 count개의 가격 데이터
        """
        if count >= len(self.prices):
            return self.prices.copy()
        
        return self.prices[-count:].copy()
    
    def __str__(self):
        """문자열 표현"""
        if self.isEmpty():
            return "PriceHistory(empty)"
        
        latest = self.getLatestPrice()
        return f"PriceHistory(length={self.getLength()}, latest={latest:.2f})"
    
    def __repr__(self):
        """공식 문자열 표현"""
        return f"PriceHistory(max_length={self.max_length}, current_length={self.getLength()})"