import sys
import traceback
import os
import utils.commutil as cutils
import logging


class Object(object):
    def copy(self, **kwargs):
        import copy
        o = copy.copy(self)
        o.__dict__.update(kwargs)
        return o

    @classmethod
    def from_dict(cls, dict):
        o = cls()
        o.__dict__.update(dict)
        return o


class StrategyObject(Object):
    # copy object from us to user space
    def copy(self, o):
        if o is None:
            return self
        for k in self.__dict__:
            setattr(self, k, getattr(o, k, None))
        return self

    @classmethod
    def copy_of(cls, o):
        if o is None:
            return None
        self = cls()
        return self.copy(o) or self

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, str(self.__dict__))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


StrategyState_instance_count = 0


class StrategyState(StrategyObject):
    def __init__(self):
        StrategyObject.__init__(self)
        StrategyObject.__setattr__(self, 'fields', set())
        pass

    def __setstate__(self, state):
        self.__dict__.update(state)
        global StrategyState_instance_count
        StrategyState_instance_count += 1

    # 不管有多少个 PersistentState, 反序列话之后都只有一个 g, __dict__ 合并在一起
    def __reduce__(self):
        return get_g, (), self.__dict__

    def __setattr__(self, name, value):
        if value is not None and name not in self.fields:
            import pickle as pickle
            try:
                pickle.dumps(name)
                pickle.dumps(value)
            except Exception as e:
                pass
                # log.error("g.%s 不能通过pickle序列化, 在模拟交易时进程重启后会丢失状态, 请不要把此对象放在 g 中. 序列化时的错误: %s" \
                #           % (name, e))
            self.fields.add(name)
        StrategyObject.__setattr__(self, name, value)

    pass


g = StrategyState()


def get_g():
    return g


class StrategyTemplate(StrategyObject):
    name = 'DefaultStrategyTemplate'

    def __init__(self, user, log_handler, main_engine):
        self.user = user
        self.main_engine = main_engine
        self.clock_engine = main_engine.clock_engine
        self.quotation_engines = main_engine.quotation_engines
        # 优先使用自定义 log 句柄, 否则使用主引擎日志句柄
        logging.basicConfig(level=logging.DEBUG)
        self.log = logging.getLogger("strategy")

        self.initialize()

    def initialize(self):
        # 进行相关的初始化操作
        pass

    def strategy(self, event):
        """:param event event.data 为所有股票的信息，结构如下
        {'162411':
        {'ask1': '0.493',
         'ask1_volume': '75500',
         'ask2': '0.494',
         'ask2_volume': '7699281',
         'ask3': '0.495',
         'ask3_volume': '2262666',
         'ask4': '0.496',
         'ask4_volume': '1579300',
         'ask5': '0.497',
         'ask5_volume': '901600',
         'bid1': '0.492',
         'bid1_volume': '10765200',
         'bid2': '0.491',
         'bid2_volume': '9031600',
         'bid3': '0.490',
         'bid3_volume': '16784100',
         'bid4': '0.489',
         'bid4_volume': '10049000',
         'bid5': '0.488',
         'bid5_volume': '3572800',
         'buy': '0.492',
         'close': '0.499',
         'high': '0.494',
         'low': '0.489',
         'name': '华宝油气',
         'now': '0.493',
         'open': '0.490',
         'sell': '0.493',
         'turnover': '420004912',
         'volume': '206390073.351'}}
        """

    def run(self, event):
        try:
            self.strategy(event)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.log.error(repr(traceback.format_exception(exc_type,
                                                           exc_value,
                                                           exc_traceback)))

    def clock(self, event):
        pass

    def log_handler(self):
        """
        优先使用在此自定义 log 句柄, 否则返回None, 并使用主引擎日志句柄
        :return: log_handler or None
        """
        return None

    def shutdown(self):
        """
        关闭进程前调用该函数
        :return:
        """
        pass
