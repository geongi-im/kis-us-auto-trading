from kis_base import KisBase
from datetime import datetime, timedelta

class KisAccount(KisBase):
    """계좌 관련 API"""
    
    def getUnsettledOrders(self, market="NASD"):
        """미체결내역 조회
        Args:
            market (str): 거래소 코드 (NASD:나스닥, NYSE:뉴욕, AMEX:아멕스 등)
            
        Returns:
            list: 미체결 내역 리스트
        """
        # 실전/모의투자 tr_id 구분
        tr_id = "TTTS3018R" if not self.is_virtual else "VTTS3018R"
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": market,
            "TR_ID": tr_id,
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        path = "uapi/overseas-stock/v1/trading/inquire-nccs"
        
        result = self.sendRequest("GET", path, tr_id, params=params)
        return result.get('output1', [])
    
    def getBalance(self, market="NASD", currency=""):
        """잔고 조회
        Args:
            market (str): 거래소 코드
            currency (str): 통화코드 (USD, HKD 등)
            
        Returns:
            dict: 종목별 잔고 및 평가 정보
        """
        # 실전/모의투자 tr_id 구분
        tr_id = "TTTS3012R" if not self.is_virtual else "VTTS3012R"
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": market,
            "TR_CRCY_CD": currency,
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        path = "uapi/overseas-stock/v1/trading/inquire-balance"
        
        result = self.sendRequest("GET", path, tr_id, params=params)
        
        # output2에서 요약 정보 추출 (안전하게)
        summary = {}
        output2 = result.get('output2', {})
        if isinstance(output2, dict):
            summary = output2
        elif isinstance(output2, list) and len(output2) > 0:
            summary = output2[0]
        
        return {
            "summary": summary,
            "stocks": result.get('output1', [])
        }
    
    def getTradeHistory(self, start_date="", end_date="", market="", buy_sell="", symbol=""):
        """체결내역 조회
        Args:
            start_date (str): 조회 시작일 (YYYYMMDD)
            end_date (str): 조회 종료일 (YYYYMMDD)
            market (str): 거래소 코드
            buy_sell (str): 매매구분 (1:매도, 2:매수)
            symbol (str): 종목코드
            
        Returns:
            list: 체결 내역 리스트
        """
        # 시작/종료일이 없으면 오늘 날짜로 설정
        if not start_date or not end_date:
            today = datetime.today().strftime("%Y%m%d")
            one_month_ago = (datetime.today() - timedelta(days=30)).strftime("%Y%m%d")
            start_date = start_date or one_month_ago
            end_date = end_date or today
        
        # 실전/모의투자 tr_id 구분
        tr_id = "TTTS3035R" if not self.is_virtual else "VTTS3035R"
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "TR_ID": tr_id,
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": "",
            "INQR_STRT_DT": start_date,
            "INQR_END_DT": end_date,
            "SLL_BUY_DVSN": buy_sell,  # 매매구분
            "OVRS_EXCG_CD": market,    # 해외거래소코드
            "PDNO": symbol,            # 종목코드
            "CCLD_NCCS_DVSN": "1"      # 체결미체결구분 1:체결, 2:미체결
        }
        
        path = "uapi/overseas-stock/v1/trading/inquire-ccnl"
        
        result = self.sendRequest("GET", path, tr_id, params=params)
        return result.get('output1', [])
    
    def getCurrentBalance(self, division="01", natn_cd="000", market="00", inqr_dvsn="00"):
        """체결기준현재잔고 조회
        Args:
            division (str): 01:원화, 02:외화
            natn_cd (str): 국가코드(000:전체, 840:미국 등)
            market (str): 시장코드
            inqr_dvsn (str): 조회구분(00:전체, 01:일반, 02:미니)
            
        Returns:
            dict: 잔고 현황
        """
        # 실전/모의투자 tr_id 구분
        tr_id = "CTRP6548R" if not self.is_virtual else "VTRP6548R"
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "TR_ID": tr_id,
            "INQR_DVSN": inqr_dvsn,        # 조회구분
            "UNPR_DVSN": division,         # 단가구분
            "FUND_STTL_ICLD_YN": "N",      # 펀드결제분포함여부
            "FNCG_AMT_AUTO_RDPT_YN": "N",  # 융자금액자동상환여부
            "PRCS_DVSN": "00",             # 처리구분
            "COST_ICLD_YN": "N",           # 비용포함여부
            "CTX_AREA_FK100": "",          # 연속조회검색조건
            "CTX_AREA_NK100": ""           # 연속조회키
        }
        
        path = "uapi/overseas-stock/v1/trading/inquire-present-balance"
        
        result = self.sendRequest("GET", path, tr_id, params=params)
        
        # output2에서 요약 정보 추출 (안전하게)
        summary = {}
        output2 = result.get('output2', {})
        if isinstance(output2, dict):
            summary = output2
        elif isinstance(output2, list) and len(output2) > 0:
            summary = output2[0]
        
        return {
            "summary": summary,
            "stocks": result.get('output1', [])
        }
    
    def getProfitLoss(self, market="", currency="", symbol="", start_date="", end_date=""):
        """기간손익 조회
        Args:
            market (str): 거래소 코드
            currency (str): 통화코드
            symbol (str): 종목코드
            start_date (str): 조회 시작일 (YYYYMMDD)
            end_date (str): 조회 종료일 (YYYYMMDD)
            
        Returns:
            dict: 기간별 손익 정보
        """
        # 시작/종료일이 없으면 오늘 날짜로 설정
        if not start_date or not end_date:
            today = datetime.today().strftime("%Y%m%d")
            one_month_ago = (datetime.today() - timedelta(days=30)).strftime("%Y%m%d")
            start_date = start_date or one_month_ago
            end_date = end_date or today
        
        # 실전/모의투자 tr_id 구분
        tr_id = "TTTS3039R" if not self.is_virtual else "VTTS3039R"
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "TR_ID": tr_id,
            "OVRS_EXCG_CD": market,
            "CRCY_CD": currency,
            "PDNO": symbol,
            "INQR_STRT_DT": start_date,
            "INQR_END_DT": end_date,
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        path = "uapi/overseas-stock/v1/trading/inquire-period-profit"
        
        result = self.sendRequest("GET", path, tr_id, params=params)
        
        # output2에서 요약 정보 추출 (안전하게)
        summary = {}
        output2 = result.get('output2', {})
        if isinstance(output2, dict):
            summary = output2
        elif isinstance(output2, list) and len(output2) > 0:
            summary = output2[0]
        
        return {
            "summary": summary,
            "details": result.get('output1', [])
        }
    
    def getOverseasPresentBalance(self, wcrc_frcr_dvsn="01", natn_cd="840", tr_mket_cd="00", inqr_dvsn_cd="00"):
        """해외주식 체결기준현재잔고 조회 (매수가능 예수금 포함)
        Args:
            wcrc_frcr_dvsn (str): 원화외화구분코드 (01:원화, 02:외화)
            natn_cd (str): 국가코드 (000:전체, 840:미국, 344:홍콩, 156:중국, 392:일본, 704:베트남)
            tr_mket_cd (str): 거래시장코드 (00:전체)
            inqr_dvsn_cd (str): 조회구분코드 (00:전체, 01:일반해외주식, 02:미니스탁)
            
        Returns:
            dict: 체결기준현재잔고 정보 (output1: 보유종목, output2: 계좌요약, output3: 예수금정보)
        """
        # 실전/모의투자 tr_id 구분
        tr_id = "CTRP6504R" if not self.is_virtual else "VTRP6504R"
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "WCRC_FRCR_DVSN_CD": wcrc_frcr_dvsn,
            "NATN_CD": natn_cd,
            "TR_MKET_CD": tr_mket_cd,
            "INQR_DVSN_CD": inqr_dvsn_cd
        }
        
        path = "uapi/overseas-stock/v1/trading/inquire-present-balance"
        
        result = self.sendRequest("GET", path, tr_id, params=params)
        
        return {
            "stocks": result.get('output1', []),       # 보유 종목 리스트
            "summary": result.get('output2', {}),      # 계좌 요약 정보
            "deposit_info": result.get('output3', {})  # 예수금 정보
        }
    
    def getOverseasPurchaseAmount(self, market="NASD", price="0", symbol=""):
        """해외주식 매수가능금액조회
        Args:
            market (str): 해외거래소코드 (NASD : 나스닥 / NYSE : 뉴욕 / AMEX : 아멕스 / SEHK : 홍콩 / SHAA : 중국상해 / SZAA : 중국심천 / TKSE : 일본 / HASE : 하노이거래소 / VNSE : 호치민거래소)
            price (str): 해외주문단가 (23.8) 정수부분 23자리, 소수부분 8자리
            symbol (str): 종목코드
            
        Returns:
            dict: 해외주식 매수 가능금액 조회 정보 (output: 매수가능금액)
        """
        # 실전/모의투자 tr_id 구분
        tr_id = "TTTS3007R" if not self.is_virtual else "VTTS3007R"
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": market, #해외거래소코드
            "OVRS_ORD_UNPR": price, # 해외주문단가 (23.8) 정수부분 23자리, 소수부분 8자리
            "ITEM_CD": symbol, #종목코드
        }
        
        path = "uapi/overseas-stock/v1/trading/inquire-psamount"
        result = self.sendRequest("GET", path, tr_id, params=params)
        return result.get('output', {})
    
    def getOverseasOrderHistory(self, symbol="", start_date="", end_date="", order_div="00", settle_div="00", market="NASD"):
        """현지시간 기준 특정 종목의 해외주식 주문체결내역 조회
        Args:
            symbol (str): 종목코드 (특정 종목을 조회할 경우, 전체 조회시 빈 문자열)
            start_date (str): 주문시작일자 (YYYYMMDD, 현지시각 기준)
            end_date (str): 주문종료일자 (YYYYMMDD, 현지시각 기준)
            order_div (str): 매도매수구분 (00:전체, 01:매도, 02:매수) - 모의계좌는 00만 가능
            settle_div (str): 체결미체결구분 (00:전체, 01:체결, 02:미체결) - 모의계좌는 00만 가능
            market (str): 해외거래소코드 (NASD:나스닥, NYSE:뉴욕, AMEX:아멕스, SEHK:홍콩, SHAA:중국상해, SZAA:중국심천, TKSE:일본, HASE:베트남하노이, VNSE:호치민)
            
        Returns:
            list: 주문체결내역 리스트 (연속조회 포함하여 모든 데이터 반환)
        """
        # 시작/종료일이 없으면 오늘 날짜로 설정
        if not start_date:
            start_date = datetime.today().strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.today().strftime("%Y%m%d")
        
        # 실전/모의투자 tr_id 구분
        tr_id = "TTTS3035R" if not self.is_virtual else "VTTS3035R"
        
        all_data = []
        tr_cont = ""
        ctx_area_fk200 = ""
        ctx_area_nk200 = ""
        
        while True:
            params = {
                "CANO": self.cano,
                "ACNT_PRDT_CD": self.acnt_prdt_cd,
                "PDNO": symbol if symbol else "%",  # 전종목일 경우 "%" 입력, 모의계좌는 ""만 가능
                "ORD_STRT_DT": start_date,          # 주문시작일자 (현지시각 기준)
                "ORD_END_DT": end_date,             # 주문종료일자 (현지시각 기준)
                "SLL_BUY_DVSN": order_div,          # 매도매수구분
                "CCLD_NCCS_DVSN": settle_div,       # 체결미체결구분
                "OVRS_EXCG_CD": market,             # 해외거래소코드
                "SORT_SQN": "DS",                   # DS:정순, AS:역순 (모의계좌는 정렬순서 사용불가)
                "ORD_DT": "",                       # 주문일자 (공백)
                "ORD_GNO_BRNO": "",                 # 주문채번지점번호 (공백)
                "ODNO": "",                         # 주문번호 (공백)
                "CTX_AREA_FK200": ctx_area_fk200,   # 연속조회키1
                "CTX_AREA_NK200": ctx_area_nk200    # 연속조회키2
            }
            
            path = "uapi/overseas-stock/v1/trading/inquire-ccnl"
            result = self.sendRequest("GET", path, tr_id, tr_cont, params=params)
            
            # 현재 페이지 데이터 추가
            current_data = result.get('output', [])
            if current_data:
                all_data.extend(current_data)
            
            # 연속조회 확인
            tr_cont = result.get('tr_cont', '')
            if tr_cont in ["D", "E"]:  # 마지막 페이지
                break
            elif tr_cont in ["F", "M"]:  # 다음 페이지 존재
                ctx_area_fk200 = result.get('ctx_area_fk200', '')
                ctx_area_nk200 = result.get('ctx_area_nk200', '')
                tr_cont = "N"  # 연속조회 플래그 설정
                
                # API 호출 제한을 위한 지연
                import time
                time.sleep(0.1)
            else:
                break
                
        return all_data