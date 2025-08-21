"""
미국 현지시간 관련 유틸리티 모듈
"""

import pytz
from datetime import datetime


class DateTimeUtil:
    """미국 주식 거래를 위한 시간 관련 유틸리티"""
    
    US_TIMEZONE = pytz.timezone('America/New_York')
    
    @classmethod
    def get_us_now(cls):
        """현재 미국 현지시간 반환"""
        return datetime.now(cls.US_TIMEZONE)
    
    @classmethod
    def get_us_date_str(cls, date_format="%Y%m%d"):
        """현재 미국 현지시간의 날짜 문자열 반환 (기본: YYYYMMDD)"""
        return cls.get_us_now().strftime(date_format)
    
    @classmethod
    def get_us_datetime_str(cls, datetime_format="%Y%m%d%H%M%S"):
        """현재 미국 현지시간의 날짜시간 문자열 반환 (기본: YYYYMMDDHHMMSS)"""
        return cls.get_us_now().strftime(datetime_format)
    
    @classmethod
    def parse_us_datetime(cls, date_str, time_str="000000"):
        """미국 현지시간으로 날짜/시간 문자열 파싱
        
        Args:
            date_str (str): 날짜 문자열 (YYYYMMDD)
            time_str (str): 시간 문자열 (HHMMSS), 기본값 000000
            
        Returns:
            datetime: 미국 현지시간으로 설정된 datetime 객체
        """
        datetime_str = f"{date_str}{time_str}"
        dt = datetime.strptime(datetime_str, "%Y%m%d%H%M%S")
        return cls.US_TIMEZONE.localize(dt)
    
    @classmethod
    def get_time_diff_minutes(cls, start_time, end_time=None):
        """두 시간 사이의 차이를 분 단위로 반환
        
        Args:
            start_time (datetime): 시작 시간
            end_time (datetime): 종료 시간 (기본: 현재 미국 시간)
            
        Returns:
            float: 시간 차이 (분)
        """
        if end_time is None:
            end_time = cls.get_us_now()
        
        return (end_time - start_time).total_seconds() / 60