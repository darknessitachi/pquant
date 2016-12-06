from utils.strategyTemplate import StrategyTemplate, StrategyState
from collections import defaultdict
import math
import os
import logging
import utils.commutil as cutils
import utils.stockutil as sutils


class Strategy(StrategyTemplate):
    name = '网格交易策略'
    current_path = os.path.dirname(__file__)
    tmp_file_path = current_path + '/' + name + '.tmp'
    config_file_path = current_path + '/' + name + '.json'
    config = cutils.file2dict(config_file_path)
    g = StrategyState()

    def initialize(self):
        self.log = logging.getLogger(self.name)
        self.subscribe()
        if os.path.exists(self.tmp_file_path):
            self.g = self.unserialize(self.tmp_file_path)
        else:
            self.g.stocks = defaultdict(dict)
            for key in self.config.keys():
                self.g.stocks.setdefault(key, {'lastNet': 0, 'upPrice': self._calcPrice(key, 1),
                                               'downPrice': self._calcPrice(key, -1)})

    def subscribe(self):
        for quotation in self.quotation_engines:
            quotation.subscribe(['150176'])

    def _calcPrice(self, stock, net):
        rate = math.pow(1 + self.config[stock]['upSize'] / 100, net) if net > 0 else 1 / math.pow(
            1 + self.config[stock]['downSize'] / 100, -net)
        return sutils.ensure_price(stock, self.config[stock]['initPrice'] * rate)

    def checkBuyOrSell(self, stock, price):
        upPrice = self.g.stocks[stock]['upPrice']
        downPrice = self.g.stocks[stock]['downPrice']
        lastNet = self.g.stocks[stock]['lastNet']
        print(upPrice, downPrice)
        if price >= self.g.stocks[stock]['upPrice']:
            # 卖
            self.log.info("网格{},卖出{},单价{},金额{}".format(lastNet,stock,price,self._calcNumber(stock,lastNet,'buy')))
            self.setLastNet(stock, lastNet + 1)
        elif price <= self.g.stocks[stock]['downPrice']:
            # 买
            self.log.info("网格{},买入{},单价{},金额:{}".format(lastNet,stock, price, self._calcNumber(stock, lastNet, 'sell')))
            self.setLastNet(stock, self.g.stocks[stock]['lastNet'] - 1)

    def setLastNet(self, stock, net):
        self.g.stocks[stock]['lastNet'] = net
        self.g.stocks[stock]['upPrice'] = self._calcPrice(stock, net + 1)
        self.g.stocks[stock]['downPrice'] = self._calcPrice(stock, net - 1)

    def _calcNumber(self, stock, net, type):
        downVal = self.config[stock]['downVal']
        upVal = self.config[stock]['upVal']
        rate = math.pow(1 + self.config[stock]['valCoefficient'] / 100, abs(net))
        if type == 'buy':
            return rate * downVal
        else:
            return rate * upVal

    def strategy(self, event):
        for stock in event.data.keys():
            self.checkBuyOrSell(stock, event.data[stock]['now'])
            self.log.info('{}'.format(event.data))
            # self.log.info('行情数据: H股B: %s' % event.data['150176'])
            self.log.info('检查持仓')
            # self.log.info(self.user.balance)
            self.log.info('\n')

    def clock(self, event):
        """在交易时间会定时推送 clock 事件
        :param event: event.data.clock_event 为 [0.5, 1, 3, 5, 15, 30, 60] 单位为分钟,  ['open', 'close'] 为开市、收市
            event.data.trading_state  bool 是否处于交易时间
        """
        if event.data.clock_event == 'open':
            # 开市了
            self.log.info('open')
        elif event.data.clock_event == 'close':
            # 收市了
            self.log.info('close')
        elif event.data.clock_event == 5:
            # 5 分钟的 clock
            self.log.info("5分钟")

    def log_handler(self):
        """自定义 log 记录方式"""
        # return DefaultLogHandler(self.name, log_type='stdout', filepath='demo1.log')
        pass

    def shutdown(self):
        """
        关闭进程前的调用
        :return:
        """
        self.serialize(self.tmp_file_path, self.g)
        self.log.info("策略已经序列化到临时文件:{}".format(self.tmp_file_path))

    @staticmethod
    def serialize(file, obj):
        import pickle
        f = open(file, 'wb')
        pickle.dump(obj, f)

    @staticmethod
    def unserialize(file):
        import pickle
        f = open(file, 'rb')
        data = pickle.load(f)
        return data