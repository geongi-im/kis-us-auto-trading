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