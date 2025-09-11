import asyncio
import json
import os
import requests
import websockets
from typing import Dict, List, Optional, Callable
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
from kis_base import KisBase
from utils.logger_util import LoggerUtil


class KisWebSocket(KisBase):
    """한국투자증권 WebSocket 연결 관리 클래스"""
    
    def __init__(self):
        super().__init__()
        self.logger = LoggerUtil().get_logger()
        
        # WebSocket 연결 정보
        self.ws_url = os.getenv("WS_URL_BASE")
        self.websocket = None
        self.is_connected = False
        
        # 체결통보용 AES 키
        self.aes_key = None
        self.aes_iv = None
        
        # 콜백 함수들
        self.execution_callback = None
        
        # 구독 중인 종목들
        self.subscribed_tickers = set()
        
    def getApprovalKey(self):
        """WebSocket 접속 승인키 발급"""
        try:
            headers = {"content-type": "application/json"}
            body = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "secretkey": self.app_secret
            }
            
            url = f"{self.api_base}/oauth2/Approval"
            response = requests.post(url, headers=headers, data=json.dumps(body))
            
            if response.status_code == 200:
                approval_key = response.json()["approval_key"]
                self.logger.info(f"WebSocket 승인키 발급 완료: {approval_key[:10]}...")
                return approval_key
            else:
                raise Exception(f"승인키 발급 실패: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"승인키 발급 중 오류: {e}")
            raise e
    
    def aes_cbc_base64_dec(self, key: str, iv: str, cipher_text: str) -> str:
        """AES256 복호화"""
        try:
            cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
            return bytes.decode(unpad(cipher.decrypt(b64decode(cipher_text)), AES.block_size))
        except Exception as e:
            self.logger.error(f"AES 복호화 오류: {e}")
            raise e
    
    async def connect(self):
        """WebSocket 연결"""
        try:
            self.logger.info(f"WebSocket 연결 시도: {self.ws_url}")
            approval_key = self.getApprovalKey()
            
            self.websocket = await websockets.connect(self.ws_url, ping_interval=None)
            self.is_connected = True
            
            # 체결통보 구독 설정
            await self.subscribe_execution_notifications(approval_key)
            
            # 메시지 처리 시작
            await self.process_messages()
            
        except Exception as e:
            self.logger.error(f"WebSocket 연결 오류: {e}")
            self.is_connected = False
            raise e
    
    async def subscribe_execution_notifications(self, approval_key: str):
        """해외주식 체결통보 구독"""
        try:
            # 모의투자/실투자에 따른 TR ID 선택
            tr_id = "H0GSCNI9" if self.is_virtual else "H0GSCNI0"
            
            # HTS ID는 환경변수에서 가져오거나 기본값 사용
            hts_id = os.getenv("HTS_ID", "CLAUDE_BOT")
            
            subscribe_data = {
                "header": {
                    "approval_key": approval_key,
                    "custtype": "P",  # 개인
                    "tr_type": "1",   # 등록
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": tr_id,
                        "tr_key": hts_id
                    }
                }
            }
            
            await self.websocket.send(json.dumps(subscribe_data))
            
        except Exception as e:
            self.logger.error(f"체결통보 구독 오류: {e}")
            raise e
    
    async def process_messages(self):
        """WebSocket 메시지 처리"""
        try:
            while self.is_connected:
                message = await self.websocket.recv()
                await self.handle_message(message)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket 연결이 종료되었습니다")
            self.is_connected = False
        except Exception as e:
            self.logger.error(f"메시지 처리 중 오류: {e}")
            self.is_connected = False
    
    async def handle_message(self, message: str):
        """개별 메시지 처리"""
        try:
            if message[0] == '1':  # 체결통보 데이터
                await self.handle_execution_notification(message)
            else:
                # JSON 응답 처리
                json_data = json.loads(message)
                tr_id = json_data.get("header", {}).get("tr_id")
                
                if tr_id == "PINGPONG":
                    await self.handle_pingpong(message)
                elif tr_id in ["H0GSCNI0", "H0GSCNI9"] or tr_id == "(null)":
                    await self.handle_subscription_response(json_data)
                else:
                    self.logger.debug(f"기타 메시지 수신: {message[:100]}...")
                    
        except Exception as e:
            self.logger.error(f"메시지 처리 오류: {e}")
            self.logger.error(f"원본 메시지: {message}")
    
    async def handle_execution_notification(self, message: str):
        """체결통보 데이터 처리"""
        try:
            parts = message.split('|')
            if len(parts) < 4:
                return
                
            tr_id = parts[1]
            encrypted_data = parts[3]
            
            if tr_id in ["H0GSCNI0", "H0GSCNI9"] and self.aes_key and self.aes_iv:
                # AES 복호화
                decrypted_data = self.aes_cbc_base64_dec(self.aes_key, self.aes_iv, encrypted_data)
                execution_info = self.parse_execution_data(decrypted_data)
                
                self.logger.info(f"체결통보 수신: {execution_info}")
                
                # 콜백 함수 호출
                if self.execution_callback:
                    await self.execution_callback(execution_info)
                    
        except Exception as e:
            self.logger.error(f"체결통보 처리 오류: {e}")
    
    def parse_execution_data(self, data: str):
        """체결통보 데이터 파싱"""
        try:
            fields = data.split('^')
            
            # 해외주식 체결통보 필드 매핑
            execution_info = {
                'customer_id': fields[0] if len(fields) > 0 else '',
                'account_no': fields[1] if len(fields) > 1 else '',
                'order_no': fields[2] if len(fields) > 2 else '',
                'original_order_no': fields[3] if len(fields) > 3 else '',
                'buy_sell_gb': fields[4] if len(fields) > 4 else '',
                'correction_gb': fields[5] if len(fields) > 5 else '',
                'order_type': fields[6] if len(fields) > 6 else '',
                'ticker': fields[7] if len(fields) > 7 else '',
                'execution_qty': fields[8] if len(fields) > 8 else '0',
                'execution_price': fields[9] if len(fields) > 9 else '0',
                'execution_time': fields[10] if len(fields) > 10 else '',
                'reject_yn': fields[11] if len(fields) > 11 else '',
                'execution_yn': fields[12] if len(fields) > 12 else '',
                'accept_yn': fields[13] if len(fields) > 13 else '',
                'branch_no': fields[14] if len(fields) > 14 else '',
                'order_qty': fields[15] if len(fields) > 15 else '0',
                'account_name': fields[16] if len(fields) > 16 else '',
                'stock_name': fields[17] if len(fields) > 17 else '',
                'overseas_gb': fields[18] if len(fields) > 18 else '',
                'collateral_type': fields[19] if len(fields) > 19 else '',
                'collateral_date': fields[20] if len(fields) > 20 else ''
            }
            
            return execution_info
            
        except Exception as e:
            self.logger.error(f"체결통보 데이터 파싱 오류: {e}")
            return {}
    
    async def handle_subscription_response(self, json_data: Dict):
        """구독 응답 처리"""
        try:
            rt_cd = json_data.get("body", {}).get("rt_cd")
            msg = json_data.get("body", {}).get("msg1", "")
            msg_cd = json_data.get("body", {}).get("msg_cd", "")
            tr_id = json_data.get("header", {}).get("tr_id")
                        
            if rt_cd == '0':  # 성공
                # AES 키, IV 저장
                output = json_data.get("body", {}).get("output", {})
                if "key" in output and "iv" in output:
                    self.aes_key = output["key"]
                    self.aes_iv = output["iv"]
                    
            elif rt_cd == '1':  # 에러
                if msg != 'ALREADY IN SUBSCRIBE':
                    self.logger.error(f"구독 실패 ({tr_id}): {msg} (MSG_CD: {msg_cd})")
                else:
                    self.logger.info(f"이미 구독 중 ({tr_id})")
            elif rt_cd == '9':  # 시스템 오류
                self.logger.error(f"시스템 오류 ({tr_id}): {msg} (MSG_CD: {msg_cd})")
                # HTS_ID 관련 오류일 가능성이 높음
                if "OPSP0017" in msg_cd:
                    self.logger.error("HTS_ID 설정 오류일 가능성이 있습니다. 환경변수 HTS_ID를 확인해주세요.")
            else:
                self.logger.warning(f"알 수 없는 응답 코드 ({tr_id}): RT_CD={rt_cd}, MSG={msg}")
                    
        except Exception as e:
            self.logger.error(f"구독 응답 처리 오류: {e}")
            self.logger.error(f"응답 데이터: {json_data}")
    
    async def handle_pingpong(self, message: str):
        """PING-PONG 처리"""
        try:
            await self.websocket.pong(message)
        except Exception as e:
            self.logger.error(f"PING-PONG 처리 오류: {e}")
    
    def set_execution_callback(self, callback: Callable):
        """체결통보 콜백 함수 설정"""
        self.execution_callback = callback
    
    async def disconnect(self):
        """WebSocket 연결 해제"""
        try:
            if self.websocket and self.is_connected:
                await self.websocket.close()
                self.is_connected = False
                self.logger.info("WebSocket 연결 해제 완료")
        except Exception as e:
            self.logger.error(f"WebSocket 연결 해제 오류: {e}")
    
    async def reconnect(self, max_retries: int = 5):
        """WebSocket 재연결"""
        for attempt in range(max_retries):
            try:
                self.logger.info(f"재연결 시도 {attempt + 1}/{max_retries}")
                await asyncio.sleep(2 ** attempt)  # 지수 백오프
                await self.connect()
                return True
            except Exception as e:
                self.logger.error(f"재연결 실패 {attempt + 1}: {e}")
                
        self.logger.error("최대 재연결 시도 횟수 초과")
        return False