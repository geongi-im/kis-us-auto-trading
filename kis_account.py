from kis_base import KisBase
from datetime import datetime, timedelta
from utils.datetime_util import DateTimeUtil

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
            market (str): 거래소 코드 ([모의] NASD:나스닥, NYSE:뉴욕, AMEX:아멕스 / [실전] NASD:미국전체, NAS:나스닥, NYSE:뉴욕, AMEX:아멕스)
            currency (str): 통화코드 (USD, HKD 등)
            
        Returns:
            dict: 종목별 잔고 및 평가 정보
        """
        parse_market = self.changeMarketCode(market, length=4)

        # 실전/모의투자 tr_id 구분
        tr_id = "TTTS3012R" if not self.is_virtual else "VTTS3012R"
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": parse_market,
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
    
    def getTradeHistory(self, start_date="", end_date="", market="", buy_sell="", ticker=""):
        """체결내역 조회
        Args:
            start_date (str): 조회 시작일 (YYYYMMDD)
            end_date (str): 조회 종료일 (YYYYMMDD)
            market (str): 거래소 코드
            buy_sell (str): 매매구분 (1:매도, 2:매수)
            ticker (str): 종목코드
            
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
            "PDNO": ticker,            # 종목코드
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
    
    def getProfitLoss(self, market="", currency="", ticker="", start_date="", end_date=""):
        """기간손익 조회
        Args:
            market (str): 거래소 코드
            currency (str): 통화코드
            ticker (str): 종목코드
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
            "PDNO": ticker,
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
    
    def getOverseasPurchaseAmount(self, market="NASD", price="0", ticker=""):
        """해외주식 매수가능금액조회
        Args:
            market (str): 해외거래소코드 (NASD : 나스닥 / NYSE : 뉴욕 / AMEX : 아멕스 / SEHK : 홍콩 / SHAA : 중국상해 / SZAA : 중국심천 / TKSE : 일본 / HASE : 하노이거래소 / VNSE : 호치민거래소)
            price (str): 해외주문단가 (23.8) 정수부분 23자리, 소수부분 8자리
            ticker (str): 종목코드
            
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
            "ITEM_CD": ticker, #종목코드
        }
        
        path = "uapi/overseas-stock/v1/trading/inquire-psamount"
        result = self.sendRequest("GET", path, tr_id, params=params)
        return result.get('output', {})
    
    def getOverseasOrderHistory(self, ticker="", start_date="", end_date="", order_div="00", settle_div="00", market="NASD", sort="DS", ctx_area_fk200="", ctx_area_nk200="", fetch_all=False):
        """현지시간 기준 특정 종목의 해외주식 주문체결내역 조회
        Args:
            ticker (str): 종목코드 (특정 종목을 조회할 경우, 전체 조회시 빈 문자열) - 모의계좌는 ""만 가능
            start_date (str): 주문시작일자 (YYYYMMDD, 현지시각 기준)
            end_date (str): 주문종료일자 (YYYYMMDD, 현지시각 기준)
            order_div (str): 매도매수구분 (00:전체, 01:매도, 02:매수) - 모의계좌는 00만 가능
            settle_div (str): 체결미체결구분 (00:전체, 01:체결, 02:미체결) - 모의계좌는 00만 가능
            market (str): 해외거래소코드 (NASD:나스닥, NYSE:뉴욕, AMEX:아멕스 등) - 모의계좌는 ""만 가능
            sort (str): 정렬순서 (DS:정순, AS:역순) - 모의계좌는 DS만 가능
            ctx_area_fk200 (str): 연속조회키1 (첫 호출시 공백, 연속조회시 이전 응답값 사용)
            ctx_area_nk200 (str): 연속조회키2 (첫 호출시 공백, 연속조회시 이전 응답값 사용)
            fetch_all (bool): 모든 페이지 자동 조회 여부 (True: 전체 조회, False: 1페이지만 조회)
            
        Returns:
            fetch_all=False: dict {'data': 주문체결내역 리스트, 'ctx_area_fk200': 연속조회키1, 'ctx_area_nk200': 연속조회키2, 'has_more': 추가데이터여부}
            fetch_all=True: list 모든 주문체결내역 리스트 (연속조회 자동 처리)
        """
        # 시작/종료일이 없으면 미국 현지시간 기준 오늘 날짜로 설정
        if not start_date:
            start_date = DateTimeUtil.get_us_date_str()
        if not end_date:
            end_date = DateTimeUtil.get_us_date_str()
        
        # 모의투자 제약사항 적용
        if self.is_virtual:
            # ticker = ""           # 모의투자는 ""만 가능
            order_div = "00"      # 모의투자는 00만 가능
            settle_div = "00"     # 모의투자는 00만 가능  
            market = "%"           # 모의투자는 "%"만 가능
            sort = "DS"           # 모의투자는 DS(정순)만 가능
        
        if fetch_all:
            # 전체 데이터 조회 모드: 단일 페이지 함수를 반복 호출
            all_data = []
            current_ctx_area_fk200 = ctx_area_fk200
            current_ctx_area_nk200 = ctx_area_nk200
            page_count = 0
            
            while True:
                page_count += 1
                # 자기 자신을 단일 페이지 모드로 호출
                result = self.getOverseasOrderHistory(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    order_div=order_div,
                    settle_div=settle_div,
                    market=market,
                    sort=sort,
                    ctx_area_fk200=current_ctx_area_fk200,
                    ctx_area_nk200=current_ctx_area_nk200,
                    fetch_all=False  # 무한재귀 방지
                )
                
                # 현재 페이지 데이터 추가
                current_data = result['data']
                if current_data:
                    all_data.extend(current_data)
                
                # 연속조회 확인
                if result['has_more']:
                    current_ctx_area_fk200 = result['ctx_area_fk200']
                    current_ctx_area_nk200 = result['ctx_area_nk200']
                    
                    # API 호출 제한을 위한 지연
                    import time
                    time.sleep(0.3)
                else:
                    break
            
            # self.logger.info(f"해외주식 주문내역 전체 조회 완료: 종목 {ticker}, 총 {len(all_data)}건, {page_count}페이지")
            return all_data
        
        # 단일 페이지 조회 모드
        tr_id = "TTTS3035R" if not self.is_virtual else "VTTS3035R"
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": ticker,
            "ORD_STRT_DT": start_date,
            "ORD_END_DT": end_date,
            "SLL_BUY_DVSN": order_div,
            "CCLD_NCCS_DVSN": settle_div,
            "OVRS_EXCG_CD": market,
            "SORT_SQN": sort,
            "ORD_DT": "",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "CTX_AREA_FK200": ctx_area_fk200,
            "CTX_AREA_NK200": ctx_area_nk200
        }
        
        path = "uapi/overseas-stock/v1/trading/inquire-ccnl"
        # 연속조회인 경우 tr_cont="N" 헤더 추가
        tr_cont_header = "N" if ctx_area_nk200 else ""
        result = self.sendRequest("GET", path, tr_id, params=params, tr_cont=tr_cont_header)

        # 데이터 추출
        data = result.get('output', [])
        
        # 연속조회키 추출
        next_ctx_area_fk200 = result.get('ctx_area_fk200', '')
        next_ctx_area_nk200 = result.get('ctx_area_nk200', '').strip()
        
        # tr_cont 헤더로 연속조회 여부 판단
        tr_cont = result.get('tr_cont', '')
        has_more = tr_cont in ['F', 'M']  # F or M: 다음 데이터 있음, D or E: 마지막 데이터
        
        # self.logger.info(f"해외주식 주문내역 조회: {len(data)}건 조회, tr_cont: {tr_cont}, 연속조회 가능: {has_more}")
        # if has_more:
            # self.logger.info(f"연속조회키: {next_ctx_area_nk200[:20]}...")
        
        return {
            'data': data,
            'ctx_area_fk200': next_ctx_area_fk200,
            'ctx_area_nk200': next_ctx_area_nk200,
            'has_more': has_more,
            'tr_cont': tr_cont
        }
