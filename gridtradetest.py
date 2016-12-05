import logging
import math

logging.basicConfig(level='DEBUG', format='[%(asctime)s] [%(levelname)s] %(name)s:%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger('GridTrade')


class GridTrade:
    def __init__(self, stock, begin_date, end_date, total_amount):
        self.stock = stock
        self.begin_date = begin_date
        self.end_date = end_date
        self.total_amount = total_amount
        self.cur_amount = total_amount
        self.total_num = 0  # 持仓数量

        self.lastPrice = 0  # 最后一网价格
        self.lastNet = 0  # 当前第几网
        self.upPrice = 0  # 上网格价格
        self.downPrice = 0  # 下网格价格

        self.initPrice = 0  # 底仓价格
        self.initSize = 3  # 底仓买入量(份)

        self.upNetSize = 4  # 网格大小(上)(%)
        self.upNetAmount = 10000  # 每格资金(上)

        self.downNetSize = 3  # 网格大小(下)
        self.downNetAmount = 10000  # 每格资金(下)

    def init(self, k):
        if not self.initPrice:
            self.initPrice = k['open']  # 以开盘价为底仓价格

        price = self.ensurePrice(self.stock, self.initPrice)
        num = self.initSize * self.calcBuyNum(self.downNetAmount, self.initPrice)
        self.order({'price': price, 'num': num})
        self.setLastNet(0)

    def update(self, k):
        if k['open'] >= self.upPrice:  # 高开
            self.checkSell(k['open'])
        elif k['open'] <= self.downPrice:  # 低开
            self.checkBuy(k['open'])
        if k['low'] > self.downPrice:
            self.checkSell(k['high'])
            self.checkBuy(k['close'])
            return
        if k['high'] < self.upPrice:
            self.checkBuy(k['low'])
            self.checkSell(k['close'])
            return
        if k['close'] < self.lastPrice:
            self.checkSell(k['high'])
            self.checkBuy(k['low'])
            self.checkSell(k['close'])
        else:
            self.checkBuy(k['low'])
            self.checkSell(k['high'])
            self.checkBuy(k['close'])

    def setLastNet(self, lastNet):
        self.lastNet = lastNet
        self.lastPrice = self._computePrice(lastNet)
        self.upPrice = self._computePrice(lastNet + 1)
        self.downPrice = self._computePrice(lastNet - 1)

    def checkBuy(self, price):
        while price <= self.downPrice:
            if not self.order(self._createOrder(self.downPrice, 1)):
                return
            self.setLastNet(self.lastNet - 1)

    def checkSell(self, price):
        while price >= self.upPrice:
            if not self.order(self._createOrder(self.upPrice, -1)):
                return
            self.setLastNet(self.lastNet + 1)

    def _computePrice(self, net):
        rate = math.pow(1 + self.upNetSize / 100, net) if net > 0 else 1 / math.pow(1 + self.downNetSize / 100, -net)
        return self.initPrice * rate

    def _createOrder(self, price, size):
        order = {'price': self.ensurePrice(self.stock, price)}
        if (self.lastNet > 0) or (self.lastNet == 0 and size < 0):
            order['num'] = self.calcBuyNum(size * self.upNetAmount, price)
        else:
            order['num'] = self.calcBuyNum(size * self.downNetAmount, price)
        return order

    @staticmethod
    def calcBuyNum(amount, price):
        return amount // price // 100 * 100

    def order(self, order):
        """

        :param order:
        :param orderType: 1 buy -1 sell
        :return:
        """
        amount = order['price'] * order['num']

        if order['num'] > 0:
            if amount > self.total_amount:
                return False
            else:
                self.total_amount += order['price'] * order['num']
                self.total_num += order['num']
                log.info('买入({})-----成交价:{},数量:{},持仓:{},市值:{}'.format(self.lastNet,
                                                                      order['price'],
                                                                      order['num'],
                                                                      self.total_num,
                                                                      abs(self.total_amount - self.cur_amount)))
                return True
        else:
            if abs(order['num']) > self.total_num:
                return False
            else:
                self.total_amount += order['price'] * order['num']
                self.total_num += order['num']
                log.info('卖出({})-----成交价:{},数量:{},持仓:{},市值:{}'.format(self.lastNet,
                                                                      order['price'],
                                                                      order['num'],
                                                                      self.total_num,
                                                                      abs(self.cur_amount - self.total_amount)))
                return True

    @staticmethod
    def ensurePrice(stock, price):
        return round(price, 3) if stock.startswith('150') else round(price, 2)


if __name__ == '__main__':
    from quotation.historyquotation import HistoryQuotation

    his = HistoryQuotation()
    data = his.get_data('601717', '20160101', '20161130')
    grid = GridTrade('601717', '20160101', '20161130', 100000)
    is_init = False
    for i in data:
        if not is_init:
            grid.init(i)
            is_init = True
        grid.update(i)
