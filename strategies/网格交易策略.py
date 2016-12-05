import datetime as dt
from dateutil import tz
from utils.strategyTemplate import StrategyTemplate
import os
import utils.commutil as cutils


class Strategy(StrategyTemplate):
    name = '网格交易策略'

    def init(self):
        self.strategy_config_path = os.path.dirname(__file__) + '/{}.json'.format(self.name)
        self.strategy_config = cutils.file2dict(self.strategy_config_path)
        # 通过下面的方式来获取时间戳
        now_dt = self.clock_engine.now_dt
        now = self.clock_engine.now
        # 注册时钟事件
        clock_type = "盘尾"
        moment = dt.time(14, 56, 30, tzinfo=tz.tzlocal())
        self.clock_engine.register_moment(clock_type, moment)
        # 注册时钟间隔事件, 不在交易阶段也会触发, clock_type == minute_interval
        minute_interval = 1.5
        self.clock_engine.register_interval(minute_interval, trading=False)
        self.subscribe()

    def subscribe(self):
        for quotation in self.quotation_engines:
            quotation.subscribe(['150176', '600887', '600315'])
        pass

    def strategy(self, event):

        self.log.info('{}'.format(self.name))
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
        self.log.info("假装在关闭前保存了策略数据")
