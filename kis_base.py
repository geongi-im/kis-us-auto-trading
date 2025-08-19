import os
import requests
import json
import traceback
from utils.token_manager import getToken
from utils.logger_util import LoggerUtil

class KisBase:
    """한국투자증권 API 기본 클래스 - 공통 인증 및 요청 처리"""
    
    def __init__(self):
        # 로거 초기화
        self.logger = LoggerUtil().get_logger()
        
        # 실전/모의 구분
        self.is_virtual = True if os.getenv("IS_VIRTUAL", "true").lower() == "true" else False
        
        # 환경변수 로드
        self.api_base = os.getenv("REST_URL_BASE")
        self.app_key = os.getenv("APP_KEY")
        self.app_secret = os.getenv("APP_SECRET")
        self.account_no = os.getenv("ACCOUNT_NO")
        
        # 계좌번호 분리
        self.cano = self.account_no[:8]
        self.acnt_prdt_cd = self.account_no[8:]
        
        # 토큰 발급
        self.access_token = getToken()
    
    def getHeaders(self, tr_id):
        """공통 헤더 생성"""
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": tr_id
        }
        
        # 분봉 조회 API의 경우 custtype 헤더 추가
        if tr_id == "HHDFS76950200":
            headers["custtype"] = "P"
            
        return headers
    
    def sendRequest(self, method, path, tr_id, params=None, body=None, retry_count=0):
        """API 요청 전송 공통 메서드"""
        import time
        
        # API 요청 빈도 제한 (0.1초 대기)
        time.sleep(0.1)
        
        url = f"{self.api_base}/{path}"
        headers = self.getHeaders(tr_id)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, data=json.dumps(body))
            else:
                raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")
            
            res_data = response.json()
            
            # 토큰 만료 에러 체크 (응답 코드와 상관없이 먼저 확인)
            if res_data.get('msg_cd') == 'EGW00123' and retry_count == 0:
                self.logger.info("토큰이 만료되어 자동 갱신을 시도합니다.")
                try:
                    # 토큰 재발급
                    self.access_token = getToken()
                    self.logger.info("토큰 갱신 완료, API 요청을 다시 시도합니다.")
                    # 갱신된 토큰으로 재시도 (1회만)
                    return self.sendRequest(method, path, tr_id, params, body, retry_count + 1)
                except Exception as token_error:
                    self.logger.error(f"토큰 갱신 실패: {token_error}")
                    raise Exception(f"토큰 갱신 실패: {token_error}")
            
            if response.status_code != 200:
                self.logger.error(f"API 요청 오류: {response.status_code}")
                self.logger.error(response.text)
                raise Exception(f"API 요청 실패: {path}")
            
            if res_data.get('rt_cd') != '0':
                self.logger.error(f"API 오류: {res_data.get('msg_cd')} - {res_data.get('msg1')}")
                raise Exception(f"API 응답 오류: {res_data.get('msg1')}")
                
            return res_data
        
        except Exception as e:
            self.logger.error(f"API 요청 중 오류 발생: {e}")
            self.logger.error(traceback.format_exc())
            raise e 