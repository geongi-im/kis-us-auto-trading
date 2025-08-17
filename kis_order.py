from kis_base import KisBase

class KisOrder(KisBase):
    """주문 관련 API"""
    
    def _getTrId(self, action):
        """tr_id 맵핑
        action: buy(매수), sell(매도), modify(정정), cancel(취소)
        """
        tr_id_map = {
            "buy": "TTTT1002U",
            "sell": "TTTT1001U",
            "modify": "TTTT1003U",
            "cancel": "TTTT1004U"
        }
        
        # 모의투자면 앞에 V 붙이기
        tr_id = tr_id_map.get(action, "")
        if self.is_virtual:
            tr_id = "V" + tr_id[1:]
            
        return tr_id
    
    def executeOrder(self, action, symbol, quantity, price=0, market="NASD", ord_dvsn="00"):
        """주문 실행
        Args:
            action (str): 'buy' 또는 'sell'
            symbol (str): 종목코드 (예: 'QQQ')
            quantity (int): 주문 수량
            price (float): 주문 가격 (시장가 주문일 경우 무시됨)
            market (str): 거래소 코드 (예: NASD : 나스닥, NYSE : 뉴욕, AMEX : 아멕스)
            ord_dvsn (str): 주문 구분 ('00':지정가)

            [Header tr_id TTTT1002U(미국 매수 주문)]
            00 : 지정가
            32 : LOO(장개시지정가) - 장시작시 지정한 가격이하/이상일 경우에만 체결
            34 : LOC(장마감지정가) - 장마감시 지정한 가격이하/이상일 경우에만 체결
            * 모의투자 VTTT1002U(미국 매수 주문)로는 00:지정가만 가능

            [Header tr_id TTTT1006U(미국 매도 주문)]
            00 : 지정가
            31 : MOO(장개시시장가)
            32 : LOO(장개시지정가)
            33 : MOC(장마감시장가)
            34 : LOC(장마감지정가)
            * 모의투자 VTTT1006U(미국 매도 주문)로는 00:지정가만 가능
        
        Returns:
            dict: 주문 결과 데이터
        """
        tr_id = self._getTrId(action)
        
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": market,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": str(price),
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": ord_dvsn
        }
        
        path = "uapi/overseas-stock/v1/trading/order"
        
        result = self.sendRequest("POST", path, tr_id, body=body)
        print(f"주문 성공: {result['msg1']}")
        if 'output' in result:
            print(f"주문번호: {result['output'].get('KRX_FWDG_ORD_ORGNO', '')}+{result['output'].get('ODNO', '')}+{result['output'].get('ORD_TMD', '')}")
        
        return result.get('output', {})
    
    def buyOrder(self, symbol, quantity, price=0, market="NASD", ord_dvsn="00"):
        """매수 주문
        Args:
            symbol (str): 종목코드 (예: 'QQQ')
            quantity (int): 주문 수량
            price (float): 주문 가격 (시장가 주문일 경우 무시됨)
            market (str): 거래소 코드 (예: NASD : 나스닥, NYSE : 뉴욕, AMEX : 아멕스)
            ord_dvsn (str): 주문 구분 ('00':지정가)

            [주문 구분 코드]
            00 : 지정가
            32 : LOO(장개시지정가) - 장시작시 지정한 가격이하/이상일 경우에만 체결
            34 : LOC(장마감지정가) - 장마감시 지정한 가격이하/이상일 경우에만 체결
            * 모의투자의 경우 00:지정가만 가능
        
        Returns:
            dict: 주문 결과 데이터
        """
        return self.executeOrder('buy', symbol, quantity, price, market, ord_dvsn)
    
    def sellOrder(self, symbol, quantity, price=0, market="NASD", ord_dvsn="00"):
        """매도 주문
        Args:
            symbol (str): 종목코드 (예: 'QQQ')
            quantity (int): 주문 수량
            price (float): 주문 가격 (시장가 주문일 경우 무시됨)
            market (str): 거래소 코드 (예: NASD : 나스닥, NYSE : 뉴욕, AMEX : 아멕스)
            ord_dvsn (str): 주문 구분 ('00':지정가)
            sll_type (str): 매도주문구분 ('00':일반매도)

            [주문 구분 코드]
            00 : 지정가
            31 : MOO(장개시시장가)
            32 : LOO(장개시지정가)
            33 : MOC(장마감시장가)
            34 : LOC(장마감지정가)
            * 모의투자의 경우 00:지정가만 가능
        
        Returns:
            dict: 주문 결과 데이터
        """
        tr_id = self._getTrId('sell')
        
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": market,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": str(price),
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": ord_dvsn,
            "SLL_TYPE": "00"
        }
        
        path = "uapi/overseas-stock/v1/trading/order"
        
        result = self.sendRequest("POST", path, tr_id, body=body)
        print(f"매도 주문 성공: {result['msg1']}")
        if 'output' in result:
            print(f"주문번호: {result['output'].get('KRX_FWDG_ORD_ORGNO', '')}+{result['output'].get('ODNO', '')}+{result['output'].get('ORD_TMD', '')}")
        
        return result.get('output', {})
    
    def modifyOrder(self, symbol, org_order_no, quantity, price, market="NASD", order_type="normal"):
        """주문 정정
        Args:
            symbol (str): 종목코드
            org_order_no (str): 원주문번호
            quantity (int): 정정 수량
            price (float): 정정 가격
            market (str): 거래소 코드
            order_type (str): 주문 타입
            
        Returns:
            dict: 정정 결과 데이터
        """
        tr_id = self._getTrId("modify")
        
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": market,
            "PDNO": symbol,
            "ORGN_ODNO": org_order_no,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": str(price),
            "ORD_SVR_DVSN_CD": "0"
        }
        
        path = "uapi/overseas-stock/v1/trading/order-rvsecncl"
        
        result = self.sendRequest("POST", path, tr_id, body=body)
        print(f"정정 주문 성공: {result['msg1']}")
        
        return result.get('output', {})
    
    def cancelOrder(self, symbol, org_order_no, quantity, market="NASD", order_type="normal"):
        """주문 취소
        Args:
            symbol (str): 종목코드
            org_order_no (str): 원주문번호
            quantity (int): 취소 수량
            market (str): 거래소 코드
            order_type (str): 주문 타입
            
        Returns:
            dict: 취소 결과 데이터
        """
        tr_id = self._getTrId("cancel")
        
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": market,
            "PDNO": symbol,
            "ORGN_ODNO": org_order_no,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": "0",  # 취소 시 0 입력
            "ORD_SVR_DVSN_CD": "0"
        }
        
        path = "uapi/overseas-stock/v1/trading/order-rvsecncl"
        
        result = self.sendRequest("POST", path, tr_id, body=body)
        print(f"취소 주문 성공: {result['msg1']}")
        
        return result.get('output', {}) 