# coding=utf-8

from .yjbtrader import YJBTrader


def use(broker, account_file):
    """用于生成特定的券商对象
    :param account_file:
    :param broker:券商名支持 ['ht', 'HT', '华泰’] ['yjb', 'YJB', ’佣金宝'] ['yh', 'YH', '银河'] ['gf', 'GF', '广发']
    :param debug: 控制 debug 日志的显示, 默认为 True
    :param remove_zero: ht 可用参数，是否移除 08 账户开头的 0, 默认 True
    :return the class of trader

    Usage::

        >>> import trade
        >>> user = trade.use('ht')
        >>> user.prepare('ht.json')
    """
    if broker.lower() in ['ht', '华泰']:
        raise RuntimeError('暂不支持!')
    if broker.lower() in ['yjb', '佣金宝']:
        return YJBTrader(account_file)
    if broker.lower() in ['yh', '银河']:
        raise RuntimeError('暂不支持!')
    if broker.lower() in ['xq', '雪球']:
        raise RuntimeError('暂不支持!')
    if broker.lower() in ['gf', '广发']:
        raise RuntimeError('暂不支持!')
