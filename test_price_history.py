#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공통 PriceHistory 클래스 테스트 스크립트
"""

from utils.price_history import PriceHistory
from datetime import datetime, timedelta
import pandas as pd

def test_price_history():
    """PriceHistory 클래스 기능 테스트"""
    
    print("=" * 60)
    print("PriceHistory 클래스 테스트")
    print("=" * 60)
    
    # 1. 기본 초기화 테스트
    print("\n1. 기본 초기화 테스트")
    ph = PriceHistory(max_length=10)
    print(f"초기 상태: {ph}")
    print(f"비어있음: {ph.isEmpty()}")
    print(f"길이: {ph.getLength()}")
    
    # 2. 가격 데이터 추가 테스트
    print("\n2. 가격 데이터 추가 테스트")
    test_prices = [100.0, 101.5, 99.8, 102.3, 98.7]
    
    for i, price in enumerate(test_prices):
        timestamp = datetime.now() + timedelta(minutes=i)
        ph.addPrice(price, timestamp)
        print(f"가격 추가: ${price:.1f} -> 길이: {ph.getLength()}")
    
    print(f"현재 상태: {ph}")
    print(f"최신 가격: ${ph.getLatestPrice():.1f}")
    print(f"최신 시간: {ph.getLatestTimestamp().strftime('%H:%M:%S')}")
    
    # 3. 데이터 조회 테스트
    print("\n3. 데이터 조회 테스트")
    print(f"모든 가격: {ph.getPrices()}")
    print(f"최근 3개: {ph.getRecentPrices(3)}")
    print(f"범위 조회 [1:4]: {ph.getPriceRange(1, 4)}")
    
    # 4. DataFrame 변환 테스트
    print("\n4. DataFrame 변환 테스트")
    df = ph.getDataframe()
    print("DataFrame 내용:")
    print(df.to_string(index=False))
    
    # 5. 최소 데이터 확인 테스트
    print("\n5. 최소 데이터 확인 테스트")
    print(f"3개 이상 데이터 있음: {ph.hasMinimumData(3)}")
    print(f"10개 이상 데이터 있음: {ph.hasMinimumData(10)}")
    
    # 6. 최대 길이 제한 테스트
    print("\n6. 최대 길이 제한 테스트")
    print("15개 가격 데이터 추가 (최대 10개로 제한)")
    
    for i in range(15):
        ph.addPrice(100 + i * 0.5)
    
    print(f"최종 길이: {ph.getLength()} (최대 10개로 제한됨)")
    print(f"가격 데이터: {ph.getPrices()}")
    
    # 7. 클리어 테스트
    print("\n7. 클리어 테스트")
    ph.clear()
    print(f"클리어 후: {ph}")
    print(f"비어있음: {ph.isEmpty()}")
    
    # 8. RSI/MACD 전략에서의 사용성 테스트
    print("\n8. 전략에서의 사용성 테스트")
    ph2 = PriceHistory(max_length=50)
    
    # 실제 가격 데이터와 유사한 패턴 생성
    base_price = 100.0
    for i in range(30):
        # 간단한 사인 파형으로 가격 변동 시뮬레이션
        import math
        price_change = math.sin(i * 0.2) * 2 + (i * 0.1)
        price = base_price + price_change
        ph2.addPrice(price)
    
    print(f"시뮬레이션 데이터 생성: {ph2.getLength()}개")
    print(f"가격 범위: ${min(ph2.getPrices()):.2f} ~ ${max(ph2.getPrices()):.2f}")
    print(f"최신 5개 가격: {[f'${p:.2f}' for p in ph2.getRecentPrices(5)]}")
    
    # 기술적 지표 계산에 필요한 최소 데이터 확인
    print(f"RSI(14) 계산 가능: {ph2.hasMinimumData(15)}")  # RSI는 14+1개 필요
    print(f"MACD(12,26,9) 계산 가능: {ph2.hasMinimumData(35)}")  # MACD는 26+9개 필요
    
    print("\n" + "=" * 60)
    print("PriceHistory 테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    test_price_history()