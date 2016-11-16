from .BasicQuotation import BasicQuotation
import json


class Leverfun(BasicQuotation):
    __url = 'https://app.leverfun.com/timelyInfo/timelyOrderForm?stockCode='

    def __init__(self):
        super(Leverfun, self).__init__(self.__url)

    def _formatResponseData(self, param, response_data, encoding):
        stockJson = json.loads(str(response_data,encoding))['data']
        buys = stockJson['buyPankou']
        sells = stockJson['sellPankou']
        stock_detail = dict(
            close=round(stockJson['preClose'], 3),
            now=stockJson['match'],
            buy=buys[0]['price'],
            sell=sells[0]['price'],
        )
        for trade_info_li, name in zip([sells, buys], ['ask', 'bid']):
            for i, trade_info in enumerate(trade_info_li):
                stock_detail['{name}{index}'.format(name=name, index=i + 1)] = trade_info['price']
                stock_detail['{name}{index}_volume'.format(name=name, index=i + 1)] = trade_info['volume'] * 100

        stock_dict = dict()
        stock_dict[param] = stock_detail
        return stock_dict

if __name__ == '__main__':
    lf = Leverfun()
    lf.subscribe('300313')
    lf.subscribe('600887')
    print(lf.subscribed)
    print(lf.getQuotationData())
    lf.unsubscribe('000001')
    lf.unsubscribe('300313')
    lf.subscribe('601717')
    print(lf.subscribed)
    print(lf.getQuotationData())
