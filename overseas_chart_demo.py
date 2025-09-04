# -*- coding: utf-8 -*-
"""
해외주식 분봉조회 데모
AMEX:XLF 종목의 1분봉 120개를 조회하는 테스트 코드
"""

import os
import pandas as pd
from datetime import datetime
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
        
        # 조회 조건 설정
        market = "AMS"  # AMEX 거래소 코드
        ticker = "XLF"  # 종목 코드
        time_frame = "1"  # 1분봉
        
        logger.info(f"분봉 데이터 조회 시작: {market}:{ticker} ({time_frame}분봉)")
        
        # 분봉 데이터 조회
        chart_data = kis_price.getMinuteChartPrice(
            market=market,
            ticker=ticker,
            time_frame=time_frame,
            include_prev_day="1"  # 전일 포함
        )
        
        if not chart_data:
            logger.error("분봉 데이터를 가져올 수 없습니다.")
            return
            
        logger.info(f"조회된 분봉 데이터 개수: {len(chart_data)}")
        
        # 데이터프레임 생성 및 정리
        df = pd.DataFrame(chart_data)
        
        if len(df) > 0:
            # 시간 컬럼 생성 (tymd + xhms)
            df['datetime'] = pd.to_datetime(df['tymd'] + df['xhms'], format='%Y%m%d%H%M%S')
            
            # 필요한 컬럼만 선택
            df_cleaned = df[['datetime', 'open', 'high', 'low', 'last', 'evol']].copy()
            
            # 데이터 타입 변환
            numeric_cols = ['open', 'high', 'low', 'last', 'evol']
            for col in numeric_cols:
                df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
            
            # 최신 시간 순으로 정렬
            df_cleaned = df_cleaned.sort_values('datetime', ascending=False).reset_index(drop=True)
            
            # 결과 출력
            print(f"\n{market}:{ticker} 1분봉 데이터 (최근 {len(df_cleaned)}개)")
            print("=" * 80)
            print(df_cleaned.head(10).to_string(index=False))
            print("=" * 80)
            
            # CSV 파일로 저장
            filename = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df_cleaned.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"분봉 데이터가 {filename} 파일로 저장되었습니다.")
            
            # 기본 통계 정보
            print(f"\n통계 정보:")
            print(f"시작 시간: {df_cleaned['datetime'].iloc[-1]}")
            print(f"종료 시간: {df_cleaned['datetime'].iloc[0]}")
            print(f"시가: ${df_cleaned['open'].iloc[-1]:.2f}")
            print(f"고가: ${df_cleaned['high'].max():.2f}")
            print(f"저가: ${df_cleaned['low'].min():.2f}")
            print(f"종가: ${df_cleaned['last'].iloc[0]:.2f}")
            print(f"총 거래량: {df_cleaned['evol'].sum():,.0f}")
            
        else:
            logger.warning("조회된 데이터가 없습니다.")
            
    except Exception as e:
        logger.error(f"분봉 조회 중 오류 발생: {e}")
        raise e

if __name__ == "__main__":
    main()