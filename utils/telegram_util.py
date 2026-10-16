import os
import json
import time
import logging
from contextlib import ExitStack

import requests
from dotenv import load_dotenv

load_dotenv()

# logger_util 이 파일/콘솔 핸들러를 붙이는 로거 이름. 설정 전이면 경고만 stderr 로 나간다.
logger = logging.getLogger('MQLogger')

API_BASE_URL = "https://api.telegram.org"
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2
MAX_RETRY_AFTER_SECONDS = 60
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class TelegramSendError(RuntimeError):
    """Telegram 이 전송을 거부했거나 재시도 후에도 응답을 받지 못한 경우"""


class TelegramUtil:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_test_id = os.getenv('TELEGRAM_CHAT_TEST_ID')

    def _request(self, method, data, open_files=None):
        """Telegram Bot API 호출. 네트워크 오류/429/5xx 는 재시도하고 마지막 응답(dict)을 돌려준다.

        open_files 는 매 시도마다 새로 연 파일 dict 를 돌려주는 함수다.
        재시도할 때 파일 포인터가 끝에 가 있으면 빈 파일이 올라가므로 매번 다시 연다.
        읽기 타임아웃 뒤 재시도하면 이미 도착한 메시지가 한 번 더 갈 수 있다.
        """
        url = f"{API_BASE_URL}/bot{self.bot_token}/{method}"
        last_error = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            wait_seconds = RETRY_BACKOFF_SECONDS * attempt
            try:
                with ExitStack() as stack:
                    files = open_files(stack) if open_files else None
                    response = requests.post(
                        url,
                        data=data,
                        files=files,
                        timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
                    )
            except (requests.ConnectionError, requests.Timeout) as e:
                last_error = self._mask_token(e)
                logger.warning("Telegram %s 네트워크 오류(%s/%s): %s", method, attempt, MAX_ATTEMPTS, last_error)
            else:
                result = self._parse_response(response)
                if result.get("ok") or response.status_code not in RETRYABLE_STATUS_CODES:
                    return result
                retry_after = (result.get("parameters") or {}).get("retry_after")
                if retry_after:
                    wait_seconds = min(int(retry_after) + 1, MAX_RETRY_AFTER_SECONDS)
                logger.warning(
                    "Telegram %s 응답 오류(%s/%s): status=%s %s",
                    method, attempt, MAX_ATTEMPTS, response.status_code, result.get("description"),
                )
                if attempt == MAX_ATTEMPTS:
                    return result

            if attempt < MAX_ATTEMPTS:
                time.sleep(wait_seconds)

        # 원래 예외를 체인으로 달면 traceback 에 토큰이 든 URL 이 그대로 찍힌다
        raise TelegramSendError(f"Telegram {method} 전송 실패: {last_error}") from None

    def _mask_token(self, error):
        """requests 예외 메시지에는 /bot<토큰>/ 이 든 URL 이 들어가므로 토큰을 가린다"""
        text = f"{type(error).__name__}: {error}"
        if self.bot_token:
            text = text.replace(self.bot_token, "***")
        return text

    @staticmethod
    def _parse_response(response):
        """프록시 오류 페이지처럼 JSON 이 아닌 응답도 Telegram 형식 dict 로 맞춘다"""
        try:
            result = response.json()
        except ValueError:
            result = None
        if not isinstance(result, dict):
            result = {
                "ok": False,
                "error_code": response.status_code,
                "description": response.text[:300],
            }
        return result

    def _send_text(self, chat_id, message):
        """텍스트 전송. 실패하면 TelegramSendError 를 던진다"""
        result = self._request("sendMessage", {
            "chat_id": chat_id,
            "parse_mode": "html",
            "text": message,
        })
        if not result.get("ok"):
            raise TelegramSendError(f"Telegram sendMessage 실패: {str(result)[:300]}")
        return result

    def sendMessage(self, message):
        """일반 메시지 전송"""
        return self._send_text(self.chat_id, message)

    def sendPhoto(self, photo_path, caption=""):
        """이미지 전송. Telegram 응답 dict 를 돌려주므로 호출 측에서 ok 를 확인한다"""
        payload = {
            "chat_id": self.chat_id,
            "caption": caption,
            "parse_mode": "html"
        }
        return self._request(
            "sendPhoto",
            payload,
            lambda stack: {"photo": stack.enter_context(open(photo_path, 'rb'))},
        )

    def sendTestMessage(self, message):
        """테스트용 채팅방으로 메시지 전송"""
        return self._send_text(self.chat_test_id, message)

    def sendMultiplePhoto(self, photo_paths, caption=""):
        """여러 장의 이미지 한 번에 전송. Telegram 응답 dict 를 돌려준다"""
        media = []
        for index, _ in enumerate(photo_paths):
            # 첫 번째 이미지에만 캡션 추가
            media.append({
                'type': 'photo',
                'media': f'attach://photo{index}',
                'caption': caption if index == 0 else "",
                'parse_mode': 'html'
            })

        payload = {
            'chat_id': self.chat_id,
            'media': json.dumps(media)
        }
        return self._request(
            "sendMediaGroup",
            payload,
            lambda stack: {
                f'photo{index}': stack.enter_context(open(photo_path, 'rb'))
                for index, photo_path in enumerate(photo_paths)
            },
        )
