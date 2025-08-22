"""
대기시간 로직 테스트 스크립트
"""

import os
from dotenv import load_dotenv
from trading_bot import TradingBot
from utils.datetime_util import DateTimeUtil
from datetime import datetime, timedelta

# 환경변수 로드
load_dotenv()

def test_delay_logic():
    """대기시간 로직 테스트"""
    print("=== 대기시간 로직 테스트 ===")
    
    # TradingBot 인스턴스 생성 (테스트용 더미 tickers)
    test_tickers = {'TQQQ': 'NASD'}
    bot = TradingBot(test_tickers)
    print(f"설정된 매수 대기시간: {bot.buy_delay_minutes}분")
    print(f"설정된 매도 대기시간: {bot.sell_delay_minutes}분")
    
    # 현재 한국시간
    current_kr_time = datetime.now(DateTimeUtil.KR_TIMEZONE)
    print(f"현재 한국시간: {current_kr_time}")
    
    # 마지막 매수 주문 시간 조회
    test_ticker = 'TQQQ'
    last_buy_time_str = bot.getLastBuyOrderTime(test_ticker)
    print(f"마지막 매수 주문 시간 (HHMMSS): {last_buy_time_str}")
    
    if last_buy_time_str:
        # 오늘 날짜로 datetime 객체 생성 (한국시간)
        today_kr = DateTimeUtil.get_kr_date_str()  # YYYYMMDD
        print(f"오늘 날짜 (YYYYMMDD): {today_kr}")
        
        last_buy_datetime = DateTimeUtil.parse_kr_datetime(today_kr, last_buy_time_str)
        print(f"마지막 매수 datetime (한국시간): {last_buy_datetime}")
        
        # 시간 차이 계산
        time_diff = DateTimeUtil.get_time_diff_minutes_kr(last_buy_datetime)
        print(f"시간 차이: {time_diff:.1f}분")
        
        # 매수 대기시간 체크
        if time_diff < bot.buy_delay_minutes:
            remaining_minutes = bot.buy_delay_minutes - time_diff
            print(f"[X] 매수 대기 중: {remaining_minutes:.1f}분 후 가능")
            return False
        else:
            print(f"[O] 대기시간 완료: 매수 가능")
            return True
    else:
        print("[O] 매수 주문 내역 없음: 매수 가능")
        return True

def test_should_buy_logic():
    """should_buy 함수의 대기시간 로직 테스트"""
    print("\n=== should_buy 함수 대기시간 로직 테스트 ===")
    
    test_tickers = {'TQQQ': 'NASD'}
    bot = TradingBot(test_tickers)
    test_ticker = 'TQQQ'
    test_market = 'NASD'
    
    # 테스트용 현재가 설정
    test_price = 90.0
    print(f"테스트 현재가: ${test_price}")
    
    # RSI 전략 신호 우선 체크 (실제 데이터 로드 필요)
    try:
        print("⚠️ RSI 데이터 로드 생략 - 대기시간 로직만 테스트")
        
        # 마지막 매수 시간 직접 체크
        last_buy_time_str = bot.getLastBuyOrderTime(test_ticker)
        if last_buy_time_str:
            today_kr = DateTimeUtil.get_kr_date_str()
            last_buy_datetime = DateTimeUtil.parse_kr_datetime(today_kr, last_buy_time_str)
            time_diff = DateTimeUtil.get_time_diff_minutes_kr(last_buy_datetime)
            
            print(f"마지막 매수 시간: {last_buy_time_str}")
            print(f"시간 차이: {time_diff:.1f}분")
            print(f"매수 대기시간 설정: {bot.buy_delay_minutes}분")
            
            if time_diff < bot.buy_delay_minutes:
                remaining_minutes = bot.buy_delay_minutes - time_diff
                print(f"[X] 대기 중: {remaining_minutes:.1f}분 후 가능")
            else:
                print(f"[O] 대기시간 완료")
        else:
            print("[O] 매수 주문 내역 없음")
            
        # 실제 shouldBuy 함수 호출 테스트
        print("\n--- shouldBuy 함수 호출 테스트 ---")
        can_buy = bot.shouldBuy(test_ticker, test_market, test_price)
        print(f"shouldBuy 결과: {can_buy}")
        
    except Exception as e:
        print(f"오류 발생: {e}")

def test_time_calculation():
    """시간 계산 로직 검증"""
    print("\n=== 시간 계산 로직 검증 ===")
    
    # 현재 시간
    now_kr = datetime.now(DateTimeUtil.KR_TIMEZONE)
    print(f"현재 한국시간: {now_kr}")
    
    # 5분 전 시간 시뮬레이션
    past_time_5min = now_kr - timedelta(minutes=5)
    past_time_3min = now_kr - timedelta(minutes=3)
    past_time_7min = now_kr - timedelta(minutes=7)
    
    print(f"5분 전: {past_time_5min}")
    print(f"3분 전: {past_time_3min}")  
    print(f"7분 전: {past_time_7min}")
    
    # 시간 차이 계산 테스트
    diff_5min = DateTimeUtil.get_time_diff_minutes_kr(past_time_5min)
    diff_3min = DateTimeUtil.get_time_diff_minutes_kr(past_time_3min)
    diff_7min = DateTimeUtil.get_time_diff_minutes_kr(past_time_7min)
    
    print(f"5분 전 시간차이: {diff_5min:.1f}분")
    print(f"3분 전 시간차이: {diff_3min:.1f}분")
    print(f"7분 전 시간차이: {diff_7min:.1f}분")
    
    # 대기시간 체크 (5분 설정 기준)
    delay_time = 5
    print(f"\n대기시간 설정: {delay_time}분")
    
    tests = [
        (diff_5min, "5분 전"),
        (diff_3min, "3분 전"), 
        (diff_7min, "7분 전")
    ]
    
    for diff, desc in tests:
        if diff < delay_time:
            remaining = delay_time - diff
            print(f"{desc}: [X] 대기 중 ({remaining:.1f}분 후 가능)")
        else:
            print(f"{desc}: [O] 대기시간 완료")

if __name__ == "__main__":
    # 실제 데이터 기반 테스트
    test_delay_logic()
    
    # should_buy 함수 테스트
    test_should_buy_logic()
    
    # 시간 계산 로직 검증
    test_time_calculation()