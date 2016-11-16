import re
from .BasicQuotation import BasicQuotation

class Sina(BasicQuotation):
    __url = 'http://hq.sinajs.cn/?format=text&list='
    __grep_detail = re.compile(r'(\d+)=([^\s][^,]+?)%s%s' % (r',([\.\d]+)' * 29, r',([-\.\d:]+)' * 2))

    def __init__(self):
        super(Sina, self).__init__(self.__url)

    def _convertRequestParams(self, stockCodes):
        result = self.__resolveStockCodes(stockCodes)
        return ','.join(result)

    @staticmethod
    def __resolveStockCodes(stockCodes):
        """判断股票ID对应的证券市场
        匹配规则
        ['50', '51', '60', '90', '110'] 为 sh
        ['00', '13', '18', '15', '16', '18', '20', '30', '39', '115'] 为 sz
        ['5', '6', '9'] 开头的为 sh， 其余为 sz
        :param stockCodes:股票ID, 若以 'sz', 'sh' 开头直接返回对应类型，否则使用内置规则判断
        :return 'sh' or 'sz'"""
        if type(stockCodes) is not list: stockCodes = [stockCodes]
        result = list()
        for code in stockCodes:
            assert type(code) is str, 'stock code need str type'
            if code.startswith(('sh', 'sz')):
                result.append(code)
            if code.startswith(('50', '51', '60', '90', '110', '113', '132', '204')):
                result.append('sh' + code)
            if code.startswith(('00', '13', '18', '15', '16', '18', '20', '30', '39', '115', '1318')):
                result.append('sz' + code)
            if code.startswith(('5', '6', '9')):
                result.append('sh' + code)
            result.append('sz' + code)
        return result

    def _formatResponseData(self, param, responseData, encoding):
        stockStr = str(responseData,encoding)
        result = self.__grep_detail.finditer(stockStr)
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
    quotation = Sina()
    quotation.subscribe('600887')
    print(quotation.getQuotationData())
