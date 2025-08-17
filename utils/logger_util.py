import logging
from pathlib import Path
from datetime import datetime
import os

class LoggerUtil:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerUtil, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not LoggerUtil._initialized:
            # 루트 디렉토리 경로 찾기 (상위 디렉토리)
            current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            root_dir = current_dir.parent
            
            # 로그 디렉토리를 루트 경로의 logs 폴더로 설정
            log_dir = root_dir / 'logs'

            # 디렉토리가 없으면 생성
            log_dir.mkdir(parents=True, exist_ok=True)

            # 로그 파일 설정
            log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}_log.log"

            # 로거 생성
            self.logger = logging.getLogger('MQLogger')
            self.logger.setLevel(logging.INFO)

            # 이미 핸들러가 있다면 제거
            if self.logger.handlers:
                self.logger.handlers.clear()

            # 파일 핸들러
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)

            # 콘솔 핸들러
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # 포맷터 설정
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            # 핸들러 추가
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
            
            LoggerUtil._initialized = True

    def get_logger(self):
        return self.logger 