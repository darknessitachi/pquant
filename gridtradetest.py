import logging
import math

logging.basicConfig(level='DEBUG', format='[%(asctime)s] [%(levelname)s] %(name)s:%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger('GridTrade')


class GridTrade:
    def __init__(self):
        self.lastPrice = 0  # 最后一网价格
        self.lastNet = 0  # 当前第几网
        self.upPrice = 0  # 上网格价格
        self.downPrice = 0  # 下网格价格

        self.initPrice = 0  # 底仓价格
        self.initSize = 0  # 底仓买入量(份)

        self.upNetSize = 0  # 网格大小(上)(%)
        self.upNetAmount = 0  # 每格资金(上)

        self.downNetSize = 0  # 网格大小(下)
        self.downNetAmount = 0  # 每格资金(下)

    def init(self, k):
        if not self.initPrice:
            self.initPrice = k['open']  # 以开盘价为底仓价格
        self.order(self._createOrder(self.initPrice,self.initSize * self.downNetAmount))
        self.setLastNet(0)

    def update(self, k):
        if k['open'] >= self.upPrice: # 高开
            self.checkSell(k['open'])
        elif k['open'] <= self.downPrice: # 低开
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
        order = {'price': price}
        if (self.lastNet > 0) or (self.lastNet == 0 and size < 0):
            order['amount'] = size * self.upNetAmount
        else:
            order['amount'] = size * self.downNetAmount
        return order

    def calcBuyNum(self, amount, price):
        return amount // price // 100 * 100

    def order(self, order):
        log.info(order)
