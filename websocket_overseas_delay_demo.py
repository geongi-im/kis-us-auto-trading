# -*- coding: utf-8 -*-
"""
해외주식 실시간지연체결가 수신 데모
KIS OpenAPI WebSocket을 이용한 해외주식 실시간 지연체결가 수신 테스트
"""
import os
import sys
import json
import time
import requests
import asyncio
import traceback
import websockets

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode

clearConsole = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')

### 함수 정의 ###

# AES256 DECODE
def aes_cbc_base64_dec(key, iv, cipher_text):
    """
    :param key:  str type AES256 secret key value
    :param iv: str type AES256 Initialize Vector
    :param cipher_text: Base64 encoded AES256 str
    :return: Base64-AES256 decoded str
    """
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    return bytes.decode(unpad(cipher.decrypt(b64decode(cipher_text)), AES.block_size))


# 웹소켓 접속키 발급
def get_approval(key, secret):
    # url = 'https://openapivts.koreainvestment.com:29443' # 모의투자계좌     
    url = 'https://openapi.koreainvestment.com:9443' # 실전투자계좌
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials",
            "appkey": key,
            "secretkey": secret}
    PATH = "oauth2/Approval"
    URL = f"{url}/{PATH}"
    time.sleep(0.05)
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    approval_key = res.json()["approval_key"]
    return approval_key


# 해외주식 실시간 지연체결가 출력 라이브러리
def stock_delay_price_overseas(data):
    """
    해외주식 실시간 지연체결가 데이터 파싱 및 출력
    """
    recvvalue = data.split('^')  # 수신데이터를 split '^'
    
    print("==== 해외주식 실시간 지연체결가 ====")
    print(f"실시간종목코드: {recvvalue[0]}")
    print(f"종목코드: {recvvalue[1]}")
    print(f"소숫점자리수: {recvvalue[2]}")
    print(f"현지일자: {recvvalue[3]}")
    print(f"현지시간: {recvvalue[4]}")
    print(f"한국일자: {recvvalue[5]}")
    print(f"한국시간: {recvvalue[6]}")
    print("======================================")
    print(f"시가: {recvvalue[7]}")
    print(f"고가: {recvvalue[8]}")  
    print(f"저가: {recvvalue[9]}")
    print(f"현재가: {recvvalue[10]}")
    print(f"대비구분: {recvvalue[11]}")
    print(f"전일대비: {recvvalue[12]}")
    print(f"등락율: {recvvalue[13]}")
    print(f"거래량: {recvvalue[14]}")
    print(f"거래대금: {recvvalue[15]}")
    print("======================================\n")


async def connect():
    try:
        # 앱키와 시크릿키를 환경변수에서 가져오거나 직접 입력
        g_appkey = os.getenv('APP_KEY', '앱키를 입력하세요')
        g_appsecret = os.getenv('APP_SECRET', '앱 시크릿키를 입력하세요')
        
        if g_appkey == '앱키를 입력하세요' or g_appsecret == '앱 시크릿키를 입력하세요':
            print("환경변수 APP_KEY, APP_SECRET을 설정하거나 코드에서 직접 입력해주세요.")
            return
        
        # 웹소켓 접속키 발급
        g_approval_key = get_approval(g_appkey, g_appsecret)
        print(f"approval_key: {g_approval_key}")

        # 웹소켓 URL
        url = 'ws://ops.koreainvestment.com:31000' # 모의투자계좌
        # url = 'ws://ops.koreainvestment.com:21000' # 실전투자계좌

        # 해외주식 실시간 지연체결가 수신 설정
        # HDFSCNT0: 해외주식 실시간 지연체결가
        # DNASAAPL: 미국 나스닥 AAPL (Apple Inc.)
        # DNASTQQQ: 미국 나스닥 TQQQ 
        code_list = [
            ['1', 'HDFSCNT0', 'DNASAAPL'],  # Apple 실시간 지연체결가
            ['1', 'HDFSCNT0', 'DNASTQQQ'],  # TQQQ 실시간 지연체결가
        ]

        senddata_list = []

        for tr_type, tr_id, tr_key in code_list:
            temp = {
                "header": {
                    "approval_key": g_approval_key,
                    "custtype": "P",
                    "tr_type": tr_type,
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": tr_id,
                        "tr_key": tr_key
                    }
                }
            }
            senddata_list.append(json.dumps(temp))

        async with websockets.connect(url, ping_interval=None) as websocket:
            
            # 구독 요청 전송
            for senddata in senddata_list:
                await websocket.send(senddata)
                await asyncio.sleep(0.5)
                print(f"구독 요청 전송: {senddata}")

            print("\n=== 실시간 지연체결가 수신 시작 ===")
            print("Ctrl+C로 종료할 수 있습니다.\n")

            while True:
                data = await websocket.recv()
                
                if data[0] == '0':  # 실시간 데이터
                    recvstr = data.split('|')
                    trid = recvstr[1]

                    if trid == "HDFSCNT0":  # 해외주식 실시간 지연체결가
                        data_cnt = int(recvstr[2])  # 체결데이터 개수
                        print(f"[{time.strftime('%H:%M:%S')}] 지연체결가 데이터 수신 (개수: {data_cnt})")
                        stock_delay_price_overseas(recvstr[3])
                        await asyncio.sleep(0.1)

                else:  # 제어 메시지
                    jsonObject = json.loads(data)
                    trid = jsonObject["header"]["tr_id"]

                    if trid != "PINGPONG":
                        rt_cd = jsonObject["body"]["rt_cd"]

                        if rt_cd == '1':  # 에러
                            if jsonObject["body"]["msg1"] != 'ALREADY IN SUBSCRIBE':
                                print(f"### ERROR: [{jsonObject['header']['tr_key']}] [{rt_cd}] {jsonObject['body']['msg1']}")
                                break
                        elif rt_cd == '0':  # 정상
                            print(f"### SUCCESS: [{jsonObject['header']['tr_key']}] [{rt_cd}] {jsonObject['body']['msg1']}")

                    elif trid == "PINGPONG":
                        print(f"### RECV [PINGPONG] [{time.strftime('%H:%M:%S')}]")
                        await websocket.pong(data)
                        print(f"### SEND [PINGPONG] [{time.strftime('%H:%M:%S')}]")

    except Exception as e:
        print('Exception 발생!')
        print(f'Error: {e}')
        print(traceback.format_exc())
        print('5초 후 재연결 시도...')
        await asyncio.sleep(5)
        await connect()  # 재연결 시도


async def main():
    """메인 함수"""
    try:
        print("=== 해외주식 실시간 지연체결가 수신 데모 ===")
        print("Apple(AAPL)과 TQQQ의 실시간 지연체결가를 수신합니다.")
        print("=========================================\n")
        
        await connect()

    except Exception as e:
        print('Exception 발생!')
        print(f'Error: {e}')
        print(traceback.format_exc())


if __name__ == "__main__":
    try:
        # 웹소켓 실행
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n\nKeyboardInterrupt! 프로그램을 종료합니다.")
        sys.exit(0)

    except Exception:
        print("Exception 발생!")
        print(traceback.format_exc())
        sys.exit(-1)