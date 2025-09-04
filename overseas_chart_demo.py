# -*- coding: utf-8 -*-
"""
해외주식 분봉조회 데모
AMEX:XLF 종목의 1분봉 120개를 조회하는 테스트 코드
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import ta
from kis_base import KisBase
from kis_price import KisPrice
from utils.logger_util import LoggerUtil

def main():
    """해외주식 분봉 조회 데모 실행"""
    
    # 로거 초기화
    logger = LoggerUtil().get_logger()
    
    # 환경 확인
    is_virtual = os.getenv("IS_VIRTUAL", "true").lower() == "true"
    logger.info(f"실행 환경: {'모의투자' if is_virtual else '실전투자'}")
    
    try:
        # KisPrice 인스턴스 생성
        kis_price = KisPrice()
        kis_base = KisBase()
        
        # 조회 조건 설정
        market = "NYSE"  # AMEX 거래소 코드
        ticker = "PAXS"  # 종목 코드
        time_frame = "5"  # 1분봉
        parse_market = kis_base.changeMarketCode(market)
        
        logger.info(f"분봉 데이터 조회 시작: {parse_market}:{ticker} ({time_frame}분봉)")
        
        # 분봉 데이터 조회 (100개로 수정)
        chart_data = kis_price.getMinuteChartPrice(
            market=parse_market,
            ticker=ticker,
            time_frame=time_frame,
            include_prev_day="1"  # 전일 포함
        )
        
        # 100개로 제한
        if len(chart_data) > 100:
            chart_data = chart_data[:100]
        
        if not chart_data:
            logger.error("분봉 데이터를 가져올 수 없습니다.")
            return
            
        logger.info(f"조회된 분봉 데이터 개수: {len(chart_data)}")
        
        # 데이터프레임 생성 및 정리
        df = pd.DataFrame(chart_data)
        
        if len(df) > 0:
            # 시간 컬럼 생성 (tymd + xhms) - 미국 동부 시간으로 파싱
            df['datetime_us'] = pd.to_datetime(df['tymd'] + df['xhms'], format='%Y%m%d%H%M%S')
            
            # 미국 동부 시간으로 설정 후 한국 시간으로 변환
            us_tz = pytz.timezone('US/Eastern')
            kr_tz = pytz.timezone('Asia/Seoul')
            
            df['datetime_us'] = df['datetime_us'].dt.tz_localize(us_tz)
            df['datetime_kr'] = df['datetime_us'].dt.tz_convert(kr_tz)
            
            # 필요한 컬럼만 선택
            df_cleaned = df[['datetime_us', 'datetime_kr', 'open', 'high', 'low', 'last', 'evol']].copy()
            
            # 표시용 컬럼 추가 (timezone 정보 제거)
            df_cleaned['us_time'] = df_cleaned['datetime_us'].dt.strftime('%Y-%m-%d %H:%M:%S')
            df_cleaned['kr_time'] = df_cleaned['datetime_kr'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # 데이터 타입 변환
            numeric_cols = ['open', 'high', 'low', 'last', 'evol']
            for col in numeric_cols:
                df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
            
            # 시간 순으로 정렬 (MACD 계산을 위해 오름차순 필요)
            df_cleaned = df_cleaned.sort_values('datetime_us', ascending=True).reset_index(drop=True)
            
            # MACD 계산
            df_with_macd = calculate_macd(df_cleaned)
            
            # 골든크로스/데드크로스 검출
            crosses = detect_macd_crosses(df_with_macd)
            
            # 최신 데이터를 위에 표시하기 위해 다시 내림차순 정렬
            df_display = df_with_macd.sort_values('datetime_us', ascending=False).reset_index(drop=True)
            
            # 결과 출력
            print(f"\n{market}:{ticker} {time_frame}분봉 데이터 (최근 {len(df_display)}개)")
            print("=" * 80)
            print(df_display[['us_time', 'kr_time', 'last', 'macd', 'signal', 'histogram']].head(10).to_string(index=False))
            print("=" * 80)
            
            # 골든크로스/데드크로스 출력
            if not crosses['golden_cross'].empty or not crosses['death_cross'].empty:
                print("\n[MACD] 골든크로스/데드크로스 분석")
                print("=" * 80)
                
                if not crosses['golden_cross'].empty:
                    print("\n[+] 골든크로스 발생 시점:")
                    for _, row in crosses['golden_cross'].iterrows():
                        print(f"  미국시간: {row['us_time']}, 한국시간: {row['kr_time']}")
                        print(f"  가격: ${row['last']:.2f}, MACD: {row['macd']:.4f}, Signal: {row['signal']:.4f}\n")
                
                if not crosses['death_cross'].empty:
                    print("\n[-] 데드크로스 발생 시점:")
                    for _, row in crosses['death_cross'].iterrows():
                        print(f"  미국시간: {row['us_time']}, 한국시간: {row['kr_time']}")
                        print(f"  가격: ${row['last']:.2f}, MACD: {row['macd']:.4f}, Signal: {row['signal']:.4f}\n")
            else:
                print("\n[!] 분석 기간 내 골든크로스/데드크로스가 발생하지 않았습니다.")
            
            print("=" * 80)
            
            # CSV 파일로 저장
            filename = f"{ticker}_{time_frame}min_macd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df_with_macd.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"MACD 분석 결과가 {filename} 파일로 저장되었습니다.")
            
            # 기본 통계 정보
            print(f"\n통계 정보:")
            print(f"시작 시간 (미국): {df_display['us_time'].iloc[-1]}")
            print(f"시작 시간 (한국): {df_display['kr_time'].iloc[-1]}")
            print(f"종료 시간 (미국): {df_display['us_time'].iloc[0]}")
            print(f"종료 시간 (한국): {df_display['kr_time'].iloc[0]}")
            print(f"시가: ${df_display['last'].iloc[-1]:.2f}")
            print(f"고가: ${df_display['high'].max():.2f}")
            print(f"저가: ${df_display['low'].min():.2f}")
            print(f"종가: ${df_display['last'].iloc[0]:.2f}")
            print(f"총 거래량: {df_display['evol'].sum():,.0f}")
            
            # NaN이 아닌 경우만 출력
            latest_macd = df_display['macd'].iloc[0]
            latest_signal = df_display['signal'].iloc[0] 
            latest_histogram = df_display['histogram'].iloc[0]
            
            if not pd.isna(latest_macd):
                print(f"현재 MACD: {latest_macd:.4f}")
                print(f"현재 Signal: {latest_signal:.4f}")
                print(f"현재 Histogram: {latest_histogram:.4f}")
            else:
                print("현재 MACD: 계산 중 (데이터 부족)")
                print("현재 Signal: 계산 중 (데이터 부족)")
                print("현재 Histogram: 계산 중 (데이터 부족)")
            
        else:
            logger.warning("조회된 데이터가 없습니다.")
            
    except Exception as e:
        logger.error(f"분봉 조회 중 오류 발생: {e}")
        raise e

def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    """ta 라이브러리를 사용한 정확한 MACD 계산
    Args:
        df: 가격 데이터프레임
        fast_period: 빠른 EMA 기간 (기본 12)
        slow_period: 느린 EMA 기간 (기본 26)
        signal_period: 시그널 라인 기간 (기본 9)
    Returns:
        MACD가 추가된 데이터프레임
    """
    df = df.copy()
    
    # 종가를 기준으로 MACD 계산 (ta 라이브러리 사용)
    close_prices = df['last'].astype(float)
    
    # ta 라이브러리를 사용한 MACD 계산
    macd_line = ta.trend.MACD(close=close_prices, 
                              window_fast=fast_period, 
                              window_slow=slow_period, 
                              window_sign=signal_period).macd()
    
    macd_signal = ta.trend.MACD(close=close_prices, 
                               window_fast=fast_period, 
                               window_slow=slow_period, 
                               window_sign=signal_period).macd_signal()
    
    macd_histogram = ta.trend.MACD(close=close_prices, 
                                  window_fast=fast_period, 
                                  window_slow=slow_period, 
                                  window_sign=signal_period).macd_diff()
    
    # 결과를 데이터프레임에 추가
    df['macd'] = macd_line
    df['signal'] = macd_signal
    df['histogram'] = macd_histogram
    
    return df

def detect_macd_crosses(df):
    """MACD 골든크로스/데드크로스 검출
    Args:
        df: MACD가 계산된 데이터프레임
    Returns:
        dict: 골든크로스와 데드크로스 발생 시점
    """
    df = df.copy()
    
    # MACD와 시그널 라인의 교차점 계산
    df['prev_macd'] = df['macd'].shift(1)
    df['prev_signal'] = df['signal'].shift(1)
    
    # NaN 값 제거 (첫 번째 행)
    df = df.dropna()
    
    # 골든크로스: MACD가 시그널을 아래에서 위로 돌파
    golden_cross_condition = (
        (df['prev_macd'] <= df['prev_signal']) &  # 이전에는 MACD가 시그널 아래
        (df['macd'] > df['signal'])  # 현재는 MACD가 시그널 위
    )
    
    # 데드크로스: MACD가 시그널을 위에서 아래로 돌파
    death_cross_condition = (
        (df['prev_macd'] >= df['prev_signal']) &  # 이전에는 MACD가 시그널 위
        (df['macd'] < df['signal'])  # 현재는 MACD가 시그널 아래
    )
    
    golden_crosses = df[golden_cross_condition].copy()
    death_crosses = df[death_cross_condition].copy()
    
    # 시간 순으로 정렬 (최신순)
    if not golden_crosses.empty:
        golden_crosses = golden_crosses.sort_values('datetime_us', ascending=False)
    if not death_crosses.empty:
        death_crosses = death_crosses.sort_values('datetime_us', ascending=False)
    
    return {
        'golden_cross': golden_crosses,
        'death_cross': death_crosses
    }

if __name__ == "__main__":
    main()