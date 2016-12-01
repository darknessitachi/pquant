import requests
import utils.commutil as cutil
import utils.stockutil as sutil


class HistoryQuotation:
    HEADERS = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, sdch, br",
        "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36"
    }

    api = 'https://xueqiu.com/stock/forchartk/stocklist.json'
    home_url = 'https://xueqiu.com'

    def __init__(self, headers=None):
        self.httpClient = requests.session()
        self.httpClient.headers = self.HEADERS.update(headers) if headers is not None else self.HEADERS
        self.set_cookies()

    def get_data(self, stock, begin, end):
        stock = sutil.get_stock_type(stock_code=stock) + stock

        params = {
            "symbol": stock,
            "period": "1day",
            "type": "normal",
            "begin": cutil.datetime2tick(begin, '%Y%m%d'),
            "end": cutil.datetime2tick(end, '%Y%m%d'),
            "_": cutil.datetime2tick()
        }
        resp = self.httpClient.get(url=self.api, params=params)
        if resp.status_code == 200:
            return resp.json()['chartlist']
        else:
            raise RuntimeError(resp.status_code)

    def set_cookies(self):
        self.httpClient.get(self.home_url)
