from kis_base import KisBase

class KisPrice(KisBase):
    """시세 관련 API"""
    
    def getPrice(self, market, ticker):
        """현재가 조회
        Args:
            market (str): 거래소 코드 (NAS:나스닥, NYS:뉴욕, AMS:아멕스 등)
            ticker (str): 종목코드
            
        Returns:
            dict: 현재가 정보
        """
        tr_id = "HHDFS00000300"
        
        params = {
            "AUTH": "",
            "EXCD": market,
            "SYMB": ticker
        }
        
        path = "uapi/overseas-price/v1/quotations/price"
        
        result = self.sendRequest("GET", path, tr_id, params=params)
        return result.get('output', {})
    
    def getDailyPrice(self, market, ticker, base_date=""):
        """일별시세 조회
        Args:
            market (str): 거래소 코드
            ticker (str): 종목코드
            base_date (str): 기준일(YYYYMMDD)
            
        Returns:
            list: 일별 시세 리스트
        """
        tr_id = "HHDFS76240000"
        
        params = {
            "AUTH": "",
            "EXCD": market,
            "SYMB": ticker,
            "GUBN": "0",
            "BYMD": base_date,
            "MODP": "0"
        }
        
        path = "uapi/overseas-price/v1/quotations/dailyprice"
        
        result = self.sendRequest("GET", path, tr_id, params=params)
        return result.get('output2', [])
    
    def getStockDetail(self, market, ticker):
        """현재가 상세 조회
        Args:
            market (str): 거래소 코드
            ticker (str): 종목코드
            
        Returns:
            dict: 현재가 상세 정보
        """
        tr_id = "HHDFS76200200"
        
        params = {
            "AUTH": "",
            "EXCD": market,
            "SYMB": ticker
        }
        
        path = "uapi/overseas-price/v1/quotations/price-detail"
        
        result = self.sendRequest("GET", path, tr_id, params=params)
        return result.get('output', {})
    
    def getAskingPrice(self, market, ticker):
        """호가 조회
        Args:
            market (str): 거래소 코드
            ticker (str): 종목코드
            
        Returns:
            dict: 호가 정보
        """
        tr_id = "HHDFS76410000"
        
        params = {
            "AUTH": "",
            "EXCD": market,
            "SYMB": ticker
        }
        
        path = "uapi/overseas-price/v1/quotations/asking-price-exp"
        
        result = self.sendRequest("GET", path, tr_id, params=params)
        return {
            "time": result.get('output1', {}),
            "asks": result.get('output2', []),
            "bids": result.get('output3', [])
        }
    
    def getMinuteChartPrice(self, market, ticker, time_frame="1", include_prev_day="1"):
        """분봉 조회
        Args:
            market (str): 거래소 코드
            ticker (str): 종목코드
            time_frame (str): 시간단위(1, 3, 5, 10, 15, 30, 60분)
            include_prev_day (str): 전일포함여부(0:미포함, 1:포함)
            
        Returns:
            list: 분봉 데이터 리스트
        """
        tr_id = "HHDFS76950200"
        
        params = {
            "AUTH": "",
            "EXCD": market,
            "SYMB": ticker,
            "NMIN": time_frame,
            "PINC": include_prev_day,  # 전일 포함 여부 (0:불포함, 1:포함)
            "NEXT": "",
            "NREC": "120",
            "FILL": "",
            "KEYB": ""
        }
        
        path = "uapi/overseas-price/v1/quotations/inquire-time-itemchartprice"
        
        result = self.sendRequest("GET", path, tr_id, params=params)
        return result.get('output2', [])
    
    def searchStocks(self, market="NAS", name="", min_price="", max_price="", country=""):
        """종목 검색
        Args:
            market (str): 거래소 코드 (NAS, NYS 등)
            name (str): 종목명/코드 검색어
            min_price (str): 최소가격
            max_price (str): 최대가격
            country (str): 국가코드
            
        Returns:
            list: 검색 결과 리스트
        """
        tr_id = "HHDFS71410000"
        
        params = {
            "AUTH": "",
            "EXCD": market,
            "CO_CD_NM": name,
            "CO_CD": "",
            "SECT": "",
            "PR_STR": min_price,
            "PR_END": max_price,
            "SECT_CODE": "",
            "VOL_STR": "",
            "VOL_END": "",
            "EPS_STR": "",
            "EPS_END": "",
            "PER_STR": "",
            "PER_END": "",
            "SECN_NM": "",
            "FORW_YN": "",
            "FORW_CNT": "",
            "GLOB_YN": "",
            "REGN": country  # 국가 코드
        }
        
        path = "uapi/overseas-price/v1/quotations/inquire-search"
        
        result = self.sendRequest("GET", path, tr_id, params=params)
        return result.get('output', []) 