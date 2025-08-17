import os
import json
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = 'token.json'

def loadToken():
    """토큰 파일에서 저장된 토큰 정보를 로드"""
    if not os.path.exists(TOKEN_FILE):
        return None
        
    with open(TOKEN_FILE, 'r') as f:
        data = json.load(f)
        
    # 만료 시간 확인 (둘 중 하나라도 만료되면 새로운 토큰 발급)
    now = datetime.now()
    expires_at = datetime.strptime(data['access_token_token_expired'], "%Y-%m-%d %H:%M:%S")
    
    if expires_at <= now:
        return None
        
    return data['access_token']

def saveToken(token_info):
    """토큰 정보를 파일에 저장
    token_info: API 응답의 토큰 정보 (access_token, expires_in, access_token_token_expired 포함)
    """
    data = {
        'access_token': token_info['access_token'],
        'expires_in': token_info['expires_in'],  # 유효기간(초)
        'access_token_token_expired': token_info['access_token_token_expired']  # 만료일시
    }
    
    with open(TOKEN_FILE, 'w') as f:
        json.dump(data, f)

def getToken():
    """토큰 조회 또는 새로 발급"""
    # 저장된 토큰이 있는지 확인
    token = loadToken()
    if token:
        return token
        
    # 환경변수에서 값 가져오기
    app_key = os.getenv("APP_KEY")
    app_secret = os.getenv("APP_SECRET")
    url_base = os.getenv("REST_URL_BASE")

    # 새로운 토큰 발급
    headers = {"content-type":"application/json"}
    body = {
        "grant_type":"client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }
    PATH = "oauth2/tokenP"
    URL = f"{url_base}/{PATH}"
    
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    
    if res.status_code != 200:
        raise Exception("토큰 발급 실패")
        
    token_info = res.json()
    saveToken(token_info)
    
    return token_info['access_token']

def getApprovalKey():
    """웹소켓 접속키를 발급받는 함수"""
    # 환경변수에서 값 가져오기
    REST_URL_BASE = os.getenv("REST_URL_BASE")
    APP_KEY = os.getenv("APP_KEY")
    APP_SECRET = os.getenv("APP_SECRET")
    
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "secretkey": APP_SECRET
    }
    PATH = "oauth2/Approval"
    URL = f"{REST_URL_BASE}/{PATH}"
    
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    
    if res.status_code != 200:
        raise Exception("접속키 발급 실패")
        
    return res.json()["approval_key"] 