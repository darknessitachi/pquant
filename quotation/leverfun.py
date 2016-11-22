from quotation.basicquotation import BasicQuotation
import json
import logging

class Leverfun(BasicQuotation):
    __crawl_api = 'https://app.leverfun.com/timelyInfo/timelyOrderForm?stockCode='

    def __init__(self):
        super(Leverfun, self).__init__(self.__crawl_api)
        self.log = logging.getLogger("LeverFun")

    def _format_response(self, response, stock):
        json_content = json.loads(response)['data']
        buys = json_content['buyPankou']
        sells = json_content['sellPankou']
        pk = dict(
            close=round(json_content['preClose'], 3),
            now=json_content['match'],
            buy=buys[0]['price'],
            sell=sells[0]['price'],
        )
        for li, name in zip([sells, buys], ['ask', 'bid']):
            for i, trade_info in enumerate(li):
                pk['{name}{index}'.format(name=name, index=i + 1)] = trade_info['price']
                pk['{name}{index}_volume'.format(name=name, index=i + 1)] = trade_info['volume'] * 100

        stock_dict = dict()
        stock_dict[stock] = pk
        return stock_dict


if __name__ == '__main__':
    from pprint import pprint
    lf = Leverfun()
    lf.subscribe('300313')
    lf.subscribe('600887')
    print(lf.subscribed)
    lf.refresh()
    # pprint(lf.refresh())
    lf.unsubscribe('000001')
    lf.unsubscribe('300313')
    lf.subscribe('601717')
    print(lf.subscribed)
    lf.refresh()
    # pprint(lf.refresh())

