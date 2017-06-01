from jqdata.api import get_trade_days
import pandas as pd
import numpy as np
import datetime as dt
import types
from kuanke.user_space_api import *

# 初始化函数，设定要操作的股票、基准等等
def initialize(context):
    # 定义一个全局变量, 保存要操作的股票
    # 000001:平安银行
    g.security = '601009.XSHG'  # '000001.XSHE' #'002142.XSHE':宁波银行
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')


def process_initialize(context):
    # 次新股指数
    g.SubnewStocksIndex = CSubnewStocksIndex(context.current_dt, size=40)
    # 最小市值股指数
    g.SmallestMarketCapsIndex = CSmallestMarketCapsIndex(context.current_dt)
    # 最低市盈率股指数 (ROC取10日)
    g.SmallestPeRatioIndex = CSmallestPeRatioIndex(context.current_dt, rocDays=20)


# 每个单位时间(如果按天回测,则每天调用一次,如果按分钟,则每分钟调用一次)调用一次
def handle_data(context, data):
    # 更新次新股指数
    g.SubnewStocksIndex.update(context.current_dt)
    log.debug('自编次新股指数.最近日期=%s, affected=%d, count=%d', g.SubnewStocksIndex.lastDate, g.SubnewStocksIndex.affected,
              g.SubnewStocksIndex.count)
    log.debug('自编次新股指数.最新值=%f, ROC(%d)=%f, 清仓=%s', g.SubnewStocksIndex.data['myindex'][0], g.SubnewStocksIndex.rocDays,
              g.SubnewStocksIndex.data['roc'][0], g.SubnewStocksIndex.data['clear'][0])
    log.debug('自编次新股指数一览(DataFrame):\n%s', g.SubnewStocksIndex.data[:10])
    # 更新最小市值股指数
    g.SmallestMarketCapsIndex.update(context.current_dt)
    log.debug('自编最小市值指数.最近日期=%s, affected=%d, count=%d', g.SmallestMarketCapsIndex.lastDate,
              g.SmallestMarketCapsIndex.affected, g.SmallestMarketCapsIndex.count)
    log.debug('自编最小市值指数.最新值=%f, ROC(%d)=%f, 清仓=%s', g.SmallestMarketCapsIndex.data['myindex'][0],
              g.SmallestMarketCapsIndex.rocDays, g.SmallestMarketCapsIndex.data['roc'][0],
              g.SmallestMarketCapsIndex.data['clear'][0])
    log.debug('自编最小市值指数一览(DataFrame):\n%s', g.SmallestMarketCapsIndex.data[:10])
    # 更新最低市盈率股指数
    # (下面将用这个指数进行个股择时)
    g.SmallestPeRatioIndex.update(context.current_dt)
    log.debug('自编最低市盈率指数.最近日期=%s, affected=%d, count=%d', g.SmallestPeRatioIndex.lastDate,
              g.SmallestPeRatioIndex.affected, g.SmallestPeRatioIndex.count)
    log.debug('自编最低市盈率指数.最新值=%f, ROC(%d)=%f, 清仓=%s', g.SmallestPeRatioIndex.data['myindex'][0],
              g.SmallestPeRatioIndex.rocDays, g.SmallestPeRatioIndex.data['roc'][0],
              g.SmallestPeRatioIndex.data['clear'][0])
    log.debug('自编最低市盈率指数一览(DataFrame):\n%s', g.SmallestPeRatioIndex.data[:10])

    # 画副图
    record(Subnew=g.SubnewStocksIndex.data['myindex'][0])
    record(SmallMCap=g.SmallestMarketCapsIndex.data['myindex'][0])
    record(SmallPe=g.SmallestPeRatioIndex.data['myindex'][0])
    record(SubnewHold=0 if g.SubnewStocksIndex.data['clear'][0] else 500)
    record(SmallMCapHold=0 if g.SmallestMarketCapsIndex.data['clear'][0] else 500)
    record(SmallPeHold=0 if g.SmallestPeRatioIndex.data['clear'][0] else 500)

    security = g.security

    # 取得当前的现金
    cash = context.portfolio.cash
    held = context.portfolio.positions_value > 0
    # 最低市盈率指数的ROC值 作为择时
    roc = g.SmallestPeRatioIndex.data['roc'][0]
    # 如果上一时间点价格高出五天平均价1%, 则全仓买入
    if not held and roc > 0:
        # 用所有 cash 买入股票
        order_value(security, cash)
        # 记录这次买入
        log.info("Buying %s" % (security))
    # 如果上一时间点价格低于五天平均价, 则空仓卖出
    elif roc <= 0 and context.portfolio.positions[security].closeable_amount > 0:
        # 卖出所有股票,使这只股票的最终持有量为0
        order_target(security, 0)
        # 记录这次卖出
        log.info("Selling %s" % (security))
    # 每日开盘时必须用这个才能获取正确的涨跌停价格
    curdata = get_current_data()
    # 画出上一时间点价格
    record(stock_price=data[security].close)


# 自编指数基类
class CCustomIndex:
    # 类的变量(并不是实例的变量)
    name = 'CustomIndex'

    # 构造函数
    def __init__(self, lastDate, size=40, rocDays=20, clearThreshold=0.01, basis=1000.0):
        if isinstance(lastDate, datetime.datetime):
            lastDate = lastDate.date()
        self.__basis = basis  # 指数基点(默认:1000点)
        self.__lastReqDate = None  # 上次的请求日期
        self.__lastDate = None  # 实际的最近交易日
        self.__size = size  # 最大容量
        self.__rocDays = rocDays  # ROC 指标周期数
        self.__clearThreshold = clearThreshold  # ROC 清仓阈值
        self.__count = 0  # 实际数量
        self.__affected = 0  # 每次更新新增记录数量
        self.__data = []  # 数据frame
        self.update(lastDate)  # 初次获取基础数据
        # log.debug('CCustomIndex:"%s" initialized, size=%d, count=%d', self.name, size, self.count)
        # log.debug('CCustomIndex.name=%s', CCustomIndex.name) # 这与 self.name 不同

    '''
    # 析构函数
    def __del__(self):
        return
    '''

    @property  # 只读属性, 指数基点
    def basis(self):
        return self.__basis

    @property  # 只读属性, 上次更新日期
    def lastDate(self):
        return self.__lastDate

    @property  # 只读属性, 上次请求日期
    def lastReqDate(self):
        return self.__lastReqDate

    @property  # 只读属性, 记录总数
    def count(self):
        return self.__count

    @property  # 只读属性, 容量大小
    def size(self):
        return self.__size

    @property  # 只读属性, 更新的记录条数(即:新增条数)
    def affected(self):
        return self.__affected

    @property  # 只读属性, ROC 周期日数
    def rocDays(self):
        return self.__rocDays

    @property  # 只读属性, clear (清仓标识)阈值
    def clearThreshold(self):
        return self.__clearThreshold

    @property  # 属性, 指数数据表 DataFrame
    def data(self):
        return self.__data

    def update(self, lastDate):
        if isinstance(lastDate, datetime.datetime):
            lastDate = lastDate.date()
        if self.__count > 0 and lastDate <= self.__lastReqDate:
            # log.warn('CCustomIndex:update:no need to update')
            self.__affected = 0
            return
        self.__updateTradingDays(lastDate)
        # log.debug('CCustomIndex:init:origin_date=%s', self.__origin_date)
        df = self.getSumCaps(lastDate)  # 取每日累计市值
        # log.debug('data frame:\n%s', df)
        df = self.calcIndex()
        # log.debug('CCustomIndex:update:data frame[%d]:\n%s', len(self.__data), self.__data)
        self.__lastReqDate = lastDate  # 保存上次请求日期
        return

    def __updateTradingDays(self, endDate):
        self.__trading_days = get_trade_days(end_date=endDate, count=self.__size * 2)
        self.__origin_date = self.__trading_days[0]

    # 每日成分股获取函数
    # @abstractmethod # 抽象函数: 需在子类中实例化.
    def getter(self, adate, i, total):
        raise NotImplementedError('getter: This is an abstract method, please Implement it!')

    # 获取每日累计流通市值
    def getSumCaps(self, endDate):
        df = pd.DataFrame(columns=['date', 'sumcap'])
        self.__affected = 0  # 受影响的行数(即:新增交易日数量)
        i = 0
        adate = endDate
        size = self.__size
        lastReq = self.__lastReqDate  # 最近请求日期
        isEmpty = self.__count == 0
        while adate >= self.__origin_date:  # 必须有个最小日期作为限制,否则可能陷入死循环
            # 若原为空时
            if isEmpty:
                if i == size:  # 则取满 size 个
                    # log.debug('getSumCaps:old empty and i==size: breaked')
                    break
            # 否则, 取从本 reqDate(即endDate) 到上一请求日期之间的那几日
            elif adate <= lastReq:
                # log.debug('getSumCaps:adate<=lastReq: breaked')
                break
            adate = adate + datetime.timedelta(-1)  # 时间倒退一日
            if adate not in self.__trading_days:  # 忽略非交易日
                # log.debug('*date: %s is not a trading day, skipped' % adate)
                continue
            # 动态获取成分股列表
            stocks = self.getter(adate, i, size)
            if len(stocks) > 0:
                df2 = get_fundamentals(query(
                    # 根据深证各指数编制方案,都是按自由流通市值计算的: http://www.cnindex.com.cn/docs/gz_399678.pdf
                    valuation.code, valuation.circulating_market_cap.label('cmcap')
                ).filter(valuation.code.in_(stocks)), date=adate)

                sumcap = df2['cmcap'].sum()  # 每日所有成分股的流通市值累计
                stock_count = len(df2['code'])  # 成分股数量, 用于归一化市值
            else:
                sumcap = 0
            if sumcap == 0: break  # 没数据了, 说明已到头,退出循环
            df = df.append({'date': adate, 'sumcap': sumcap, 'stocks': stock_count}, ignore_index=True)
            i += 1
        # while end
        if i > 0:
            df.set_index(['date'], inplace=True)  # inplace=True 为替换原df, 否则产生新的 df
            # print df['date'] # 被设为 index 后就没有'date'了
            if self.__count > 0:  # 如果原有数据, 则连接
                df = df.append(self.__data)
            # else: log.debug('CCustomIndex:getSumCaps:count=0')
            self.__lastDate = df.index[0]  # 取最近交易日
            self.__count = len(df)
            # log.debug('CCustomIndex:getSumCaps:count=%d, lastDate=%s, result:\n%s', i, self.__lastDate, result)
        self.__data = df
        self.__affected = i  # 新增记录数量
        return self.__data

    # 计算自编指数, 基点 basis 默认为1000点
    def calcIndex(self):
        # if df is None:
        df = self.__data
        len_df = len(df)
        if len_df == 0:
            return df
        if not ('myindex' in df.columns):  # 若是初次计算(尚无这些列)
            df['myindex'] = self.__basis  # 初始化,新建myindex列并全置1
            df['roc'] = np.nan
            df['clear'] = np.nan
            startIndex = len(df) - 1  # 从倒数第2行开始倒序计算
            # log.debug('calcIndex:initial empty:startIndex=%d', startIndex)
        else:
            # 否则, 从上次交易日那行开始倒序计算
            startIndex = list(df.index).index(self.__lastDate) + 1
            # log.debug('calcIndex:not empty:startIndex=%d', startIndex)
        df_sumcap = df['sumcap']
        df_count = df['stocks']
        rocDays = self.__rocDays
        threshold = self.__clearThreshold
        # 自定义指数的算法: 当日指数=前日指数*Σ(当日成分股流通市值归一化)/Σ(前日成分股流通市值归一化)
        for i in reversed(range(startIndex)):  # 从倒数第2个开始滚动计算
            prev = i + 1
            # 计算 myindex
            v = df['myindex'][prev] * (df_sumcap[i] / df_count[i]) / (df_sumcap[prev] / df_count[prev])
            df.ix[i, 'myindex'] = v  # df 修改某个单元值的正确方式!
            # 计算指数的 ROC 值和是否清仓标识 clear
            if i + rocDays < len_df:
                roc = v / df['myindex'][i + rocDays] - 1
                df.ix[i, 'roc'] = roc
                df.ix[i, 'clear'] = roc < threshold

        # 尝试过用 pandas.rolling_by 计算, 不得要领
        self.__data = df
        return self.__data

    # 获取 ROC 值, start=起点, days=天数
    def getROC(self, start=0, days=20):
        ser = self.__data['myindex']
        if start + days < len(ser):
            result = ser[start] / ser[start + days] - 1
        else:
            result = np.nan
        return result

    # 剔除停牌股
    def remove_paused(self, stock_list, adate):
        # 过滤停牌股(研究中无法获取 current_data, 故用 get_price)
        df = get_price(stock_list, count=1, end_date=adate, fields=['paused'])['paused']
        result = [stock for stock in stock_list if df[stock][-1] == 0]
        # dif = len(stock_list) - len(result)
        # if dif > 0: log.debug('%s:remove_paused: %d paused stocks removed on %s', self.name, dif, adate)
        return result

    # 剔除ST股
    def remove_st(self, stock_list, adate):
        # 过滤ST股(研究中无法获取 current_data, 故用 get_extras)
        df = get_extras('is_st', stock_list, count=1, end_date=adate)
        result = [stock for stock in stock_list if df[stock][-1] == False]
        # dif = len(stock_list) - len(result)
        # if dif > 0: log.debug('%s:remove_st: %d ST stocks removed on %s', self.name, dif, adate)
        return result


# 编指次新股自数
class CSubnewStocksIndex(CCustomIndex):
    # __dateRange = [45, 360] #次新股的上市天数限定范围[from, to]
    @property  # 只读属性
    def dateRange(self):
        return self.__dateRange

    # 构造函数
    def __init__(self, lastDate, size=40, rocDays=20, clearThreshold=0.01, dateRange=[45, 360]):
        self.__dateRange = dateRange
        self.name = 'SubnewStocksIndex'
        # 调用父类的构造函数
        CCustomIndex.__init__(self, lastDate, size, rocDays, clearThreshold)
        # log.debug('CSubnewStocksIndex:__init__:dateRange=%s', self.__dateRange)
        return

    # 每日成分股动态获取函数
    def getter(self, adate, i, total):
        # 根据日期, 获取该日符合要求的个股列表
        # 取得所有最小市值次新股成分股
        # 选取流通市值小于200亿的300只股票,再筛选出其中的次新股
        # log.debug('*CSubnewStocksIndex:getter: date=%s', adate)
        df = get_fundamentals(query(
            valuation.code
        ).filter(
            # valuation.circulating_market_cap <= 200 #流通市值限制
        ).order_by(
            valuation.circulating_market_cap.asc()  # 按流通市值从小到大排序
        ).limit(300), date=adate)
        stock_list = list(df['code'])
        # 筛选出上市日期介于45到360日间的次新股
        lowLimit = self.__dateRange[0]  # 45
        highLimit = self.__dateRange[1]  # 360
        stock_list = [stock for stock in stock_list if
                      lowLimit < (adate - get_security_info(stock).start_date).days < highLimit]
        # 过滤停牌股
        stock_list = self.remove_paused(stock_list, adate)
        # log.debug('CSubnewStocksIndex:getter: stock_list=%s', stock_list)
        return stock_list


# 最小总市值100股自编指数
class CSmallestMarketCapsIndex(CCustomIndex):
    @property  # 市值范围
    def mcapRange(self):
        return self.__mcapRange

    @property  # 股池大小
    def poolSize(self):
        return self.__poolSize

    # 构造函数
    def __init__(self, lastDate, size=40, rocDays=20, clearThreshold=0.01, mcapRange=[0, 500], poolSize=100):
        self.__mcapRange = mcapRange
        self.__poolSize = poolSize
        self.name = 'SmallestMarketCapsIndex'
        # 调用父类的构造函数
        CCustomIndex.__init__(self, lastDate, size, rocDays, clearThreshold)
        return

    # 每日成分股动态获取函数
    def getter(self, adate, i, total):
        # 根据日期, 获取该日符合要求的个股列表
        # 取得所有最小市值次新股成分股
        # 选取流通市值小于200亿的300只股票,再筛选出其中的次新股
        # log.debug('*CSubnewStocksIndex:getter: date=%s', adate)
        poolSize = self.__poolSize
        df = get_fundamentals(query(
            valuation.code
        ).filter(
            valuation.market_cap >= self.__mcapRange[0],  # 总市值下限
            valuation.market_cap <= self.__mcapRange[1]  # 总市值上限
        ).order_by(
            valuation.market_cap.asc()  # 按总市值从小到大排序
        ).limit(poolSize + 100), date=adate)
        stock_list = list(df['code'])
        # 筛选出上市日期大于360日的非次新股
        lowLimit = 360
        stock_list = [stock for stock in stock_list if lowLimit < (adate - get_security_info(stock).start_date).days]
        # 过滤停牌股
        stock_list = self.remove_paused(stock_list, adate)
        # 过滤ST股
        stock_list = self.remove_st(stock_list, adate)
        ##log.debug('CSmallestMarketCapsIndex:getter: stock_list=%s', stock_list)
        return stock_list[:poolSize]


# 最低市盈率100股自编指数
class CSmallestPeRatioIndex(CCustomIndex):
    @property  # 市盈率范围
    def peRange(self):
        return self.__peRange

    @property  # 股池大小
    def poolSize(self):
        return self.__poolSize

    # 构造函数
    def __init__(self, lastDate, size=40, rocDays=20, clearThreshold=0.01, peRange=[0, 100], poolSize=100):
        self.__peRange = peRange
        self.__poolSize = poolSize
        self.name = 'SmallestPeRatioIndex'
        # 调用父类的构造函数
        CCustomIndex.__init__(self, lastDate, size, rocDays, clearThreshold)
        return

    # 每日成分股动态获取函数
    def getter(self, adate, i, total):
        # 根据日期, 获取该日符合要求的个股列表
        # 取得所有最小市值次新股成分股
        # 选取流通市值小于200亿的300只股票,再筛选出其中的次新股
        # log.debug('*CSubnewStocksIndex:getter: date=%s', adate)
        poolSize = self.__poolSize
        df = get_fundamentals(query(
            valuation.code
        ).filter(
            valuation.pe_ratio >= self.__peRange[0],  # 动态市盈率下限
            valuation.pe_ratio <= self.__peRange[1]  # 动态市盈率上限
        ).order_by(
            valuation.pe_ratio.asc()  # 按总市值从小到大排序
        ).limit(poolSize + 100), date=adate)
        stock_list = list(df['code'])
        # 筛选出上市日期大于360日的非次新股
        # lowLimit = 360
        # stock_list = [stock for stock in stock_list if lowLimit < (adate - get_security_info(stock).start_date).days]
        # 过滤停牌股
        stock_list = self.remove_paused(stock_list, adate)
        # 过滤ST股
        stock_list = self.remove_st(stock_list, adate)
        # log.debug('CSmallestPeRatioIndex:getter: stock_list=%s', stock_list)
        return stock_list[:poolSize]