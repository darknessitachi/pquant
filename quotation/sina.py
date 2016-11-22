import re
from quotation.basicquotation import BasicQuotation
from utils.stockutil import get_stock_type
import logging


class Sina(BasicQuotation):
    __crawl_api = 'http://hq.sinajs.cn/?format=text&list='
    __grep_detail = re.compile(r'(\d+)=([^\s][^,]+?)%s%s' % (r',([\.\d]+)' * 29, r',([-\.\d:]+)' * 2))

    def __init__(self):
        super(Sina, self).__init__(self.__crawl_api)
        self.log = logging.getLogger("sina")

    def _curl_handle(self, crawl_api, param):
        result = get_stock_type(param) + param
        return crawl_api + result

    def _format_response(self, response, stock):
        result = self.__grep_detail.finditer(response)
        stock_dict = dict()
        for stock_match_object in result:
            stock = stock_match_object.groups()
            stock_dict[stock[0]] = dict(
                name=stock[1],
                open=float(stock[2]),
                close=float(stock[3]),
                now=float(stock[4]),
                high=float(stock[5]),
                low=float(stock[6]),
                buy=float(stock[7]),
                sell=float(stock[8]),
                turnover=int(stock[9]),
                volume=float(stock[10]),
                bid1_volume=int(stock[11]),
                bid1=float(stock[12]),
                bid2_volume=int(stock[13]),
                bid2=float(stock[14]),
                bid3_volume=int(stock[15]),
                bid3=float(stock[16]),
                bid4_volume=int(stock[17]),
                bid4=float(stock[18]),
                bid5_volume=int(stock[19]),
                bid5=float(stock[20]),
                ask1_volume=int(stock[21]),
                ask1=float(stock[22]),
                ask2_volume=int(stock[23]),
                ask2=float(stock[24]),
                ask3_volume=int(stock[25]),
                ask3=float(stock[26]),
                ask4_volume=int(stock[27]),
                ask4=float(stock[28]),
                ask5_volume=int(stock[29]),
                ask5=float(stock[30]),
                date=stock[31],
                time=stock[32],
            )
        return stock_dict


if __name__ == '__main__':
    from pprint import pprint
    q = Sina()
    q.subscribe('600887')
    pprint(q.refresh())
