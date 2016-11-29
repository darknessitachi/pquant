import datetime
from datetime import timedelta,tzinfo
from functools import lru_cache
import requests
import time

@lru_cache()
def is_holiday(day):
    api = 'http://www.easybots.cn/api/holiday.php'
    params = {'d': day}
    rep = requests.get(api, params)
    print(rep)
    res = rep.json()[day if isinstance(day, str) else day[0]]
    return True if res == "1" else False


def is_holiday_today():
    today = datetime.date.today().strftime('%Y%m%d')
    return is_holiday(today)


def is_trade_time_now(time = time.localtime()):
    now_time = time.localtime()
    now = (now_time.tm_hour, now_time.tm_min, now_time.tm_sec)
    if (9, 15, 0) <= now <= (11, 30, 0) or (13, 0, 0) <= now <= (15, 0, 0):
        return True
    return False


def next_trade_time():
    now_time = datetime.datetime.now()
    now = (now_time.hour, now_time.minute, now_time.second)
    if now < (9, 15, 0):
        next_trade_start = now_time.replace(hour=9, minute=15, second=0, microsecond=0)
    elif (12, 0, 0) < now < (13, 0, 0):
        next_trade_start = now_time.replace(hour=13, minute=0, second=0, microsecond=0)
    elif now > (15, 0, 0):
        distance_next_work_day = 1
        while True:
            target_day = now_time + timedelta(days=distance_next_work_day)
            if is_holiday(target_day.strftime('%Y%m%d')):
                distance_next_work_day += 1
            else:
                break

        day_delta = timedelta(days=distance_next_work_day)
        next_trade_start = (now_time + day_delta).replace(hour=9, minute=15,
                                                          second=0, microsecond=0)
    else:
        return 0
    time_delta = next_trade_start - now_time
    return time_delta.total_seconds()

def is_weekend(now_time):
    return now_time.weekday() >= 5

def is_trade_date(now_time):
    return not (is_holiday(now_time) or is_weekend(now_time))

def get_next_trade_date(now_time):
    """
    :param now_time: datetime.datetime
    :return:
    >>> import datetime
    >>> get_next_trade_date(datetime.date(2016, 5, 5))
    datetime.date(2016, 5, 6)
    """
    now = now_time
    max_days = 365
    days = 0
    while 1:
        days += 1
        now += datetime.timedelta(days=1)
        if is_trade_date(now):
            if isinstance(now, datetime.date):
                return now
            else:
                return now.date()
        if days > max_days:
            raise ValueError('无法确定 %s 下一个交易日' % now_time)

OPEN_TIME = (
    (datetime.time(9, 15, 0), datetime.time(11, 30, 0)),
    (datetime.time(13, 0, 0), datetime.time(15, 0, 0)),
)


def is_tradetime(now_time):
    """
    :param now_time: datetime.time()
    :return:
    """
    now = now_time.time()
    for begin, end in OPEN_TIME:
        if begin <= now < end:
            return True
    else:
        return False


PAUSE_TIME = (
    (datetime.time(11, 30, 0), datetime.time(12, 59, 30)),
)


def is_pause(now_time):
    """
    :param now_time:
    :return:
    """
    now = now_time.time()
    for b, e in PAUSE_TIME:
        if b <= now < e:
            return True


CONTINUE_TIME = (
    (datetime.time(12, 59, 30), datetime.time(13, 0, 0)),
)


def is_continue(now_time):
    now = now_time.time()
    for b, e in CONTINUE_TIME:
        if b <= now < e:
            return True
    return False


CLOSE_TIME = (
    datetime.time(15, 0, 0),
)


def is_closing(now_time, start=datetime.time(14, 54, 30)):
    now = now_time.time()
    for close in CLOSE_TIME:
        if start <= now < close:
            return True
    return False