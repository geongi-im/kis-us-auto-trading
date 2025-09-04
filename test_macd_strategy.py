#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MACD 전략 테스트 스크립트
"""

from macd_strategy import MACDStrategy
from utils.logger_util import LoggerUtil
import time

def test_macd_strategy():
    """MACD 전략 테스트"""
    
    # 로거 초기화
    logger = LoggerUtil().get_logger()
    
    try:
        # MACD 전략 인스턴스 생성 (NYSE:PAXS로 테스트)
        macd_strategy = MACDStrategy(
            ticker="PAXS",
            market="NYS",
            fast_period=12,
            slow_period=26,
            signal_period=9
        )
        
        logger.info("MACD 전략 테스트 시작...")
        
        # 1. 과거 데이터 로드
        logger.info("과거 데이터 로딩 중...")
        success = macd_strategy.loadHistoricalData()
        
        if not success:
            logger.error("과거 데이터 로드 실패")
            return
        
        # 2. 현재 상태 확인
        status = macd_strategy.getStrategyStatus()
        
        print("\n" + "="*60)
        print("MACD 전략 현재 상태")
        print("="*60)
        print(f"종목: {status['ticker']}")
        print(f"현재가: ${status['current_price']:.2f}" if status['current_price'] else "현재가: N/A")
        print(f"데이터 개수: {status['data_length']}개")
        print(f"MACD 파라미터: {status['fast_period']}/{status['slow_period']}/{status['signal_period']}")
        
        if status['current_macd'] is not None:
            print(f"현재 MACD: {status['current_macd']:.6f}")
            print(f"현재 Signal: {status['current_signal']:.6f}")
            print(f"현재 Histogram: {status['current_histogram']:.6f}")
        else:
            print("MACD: 계산 중 (데이터 부족)")
        
        print(f"매수 신호 (골든크로스): {'[+] YES' if status['buy_signal'] else '[-] NO'}")
        print(f"매도 신호 (데드크로스): {'[+] YES' if status['sell_signal'] else '[-] NO'}")
        
        # 3. 실시간 가격 업데이트 시뮬레이션
        print("\n" + "="*60)
        print("실시간 가격 업데이트 시뮬레이션")
        print("="*60)
        
        # 현재 가격 기준으로 약간의 변동 시뮬레이션
        if status['current_price']:
            base_price = status['current_price']
            
            for i in range(5):
                # 작은 가격 변동 시뮬레이션
                price_change = (i - 2) * 0.01  # -0.02 ~ +0.02
                new_price = base_price + price_change
                
                macd_strategy.updatePrice(new_price)
                
                # 업데이트된 상태 확인
                updated_status = macd_strategy.getStrategyStatus()
                
                print(f"\n업데이트 {i+1}: 가격 ${new_price:.2f}")
                
                if updated_status['current_macd'] is not None:
                    print(f"  MACD: {updated_status['current_macd']:.6f}")
                    print(f"  Signal: {updated_status['current_signal']:.6f}")
                    print(f"  Histogram: {updated_status['current_histogram']:.6f}")
                    
                    if updated_status['buy_signal']:
                        print("  [+] 골든크로스 발생! (매수 신호)")
                    elif updated_status['sell_signal']:
                        print("  [-] 데드크로스 발생! (매도 신호)")
                    else:
                        print("  [=] 신호 없음")
                else:
                    print("  MACD 계산 중...")
                
                time.sleep(0.5)  # 시뮬레이션 간격
        
        print("\n" + "="*60)
        print("MACD 전략 테스트 완료")
        print("="*60)
        
    except Exception as e:
        logger.error(f"MACD 전략 테스트 중 오류 발생: {e}")
        raise e

if __name__ == "__main__":
    test_macd_strategy()