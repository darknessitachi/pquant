# coding: utf-8
import logging
import re
import os
import time
import ssl
from threading import Thread
import utils.stockutil as sutils
import utils.commutil as cutils
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager


class LoginError(Exception):
    def __init__(self, message=None):
        super(LoginError, self).__init__()
        self.message = message


class TradeError(Exception):
    def __init__(self, message=None):
        super(TradeError, self).__init__()
        self.message = message


class Ssl3HttpAdapter(HTTPAdapter):
    def __init__(self):
        super(Ssl3HttpAdapter, self).__init__()

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=ssl.PROTOCOL_TLSv1)


class BasicTrader(object):
    __global_config_path = os.path.dirname(__file__) + '/config/global.json'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6'
    }

    def __init__(self, account_filepath, api_filepath, auto_login=True, login_limit=10):
        logging.basicConfig(level='INFO',
                            format='[%(asctime)s] [%(levelname)s] %(name)s:%(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        self.log = logging.getLogger('trader')

        self.httpClient = requests.session()
        self.httpClient.mount('https://', Ssl3HttpAdapter())

        self.__account_info = cutils.file2dict(path=account_filepath)

        self.config = cutils.file2dict(path=api_filepath)
        self.global_config = cutils.file2dict(self.__global_config_path)
        self.config.update(self.global_config)

        self.__heart_active = True
        self.__heart_thread = Thread(target=self.__send_heartbeat)
        self.__heart_thread.setDaemon(True)

        if auto_login:
            self.autologin(limit=login_limit)
            self.__keepalive()

    def _request(self, method, url, data=None, callback=None):
        resp = self.httpClient.request(method=method.upper(), url=url, data=data, headers=self.headers)
        if resp.status_code == 200:
            self.log.debug(resp.headers)
            if callback:
                return callback(resp)
            return resp
        else:
            self.log.error('{}:{}'.format(resp.status_code, url))
            raise requests.RequestException('{}:{}'.format(resp.status_code, url))

    def autologin(self, limit=10):
        """实现自动登录
        :param limit: 登录次数限制
        """
        for _ in range(limit):
            if self.login():
                break
        else:
            raise LoginError('登录失败次数过多, 请检查密码是否正确 / 券商服务器是否处于维护中 / 网络连接是否正常')
        self.__keepalive()

    def login(self):
        pass

    def heartbeat(self):
        return self.balance

    def check_account_live(self, response):
        pass

    def __keepalive(self):
        """启动保持在线的进程 """
        if self.__heart_thread.is_alive():
            self.__heart_active = True
        else:
            self.__heart_thread.start()

    def __send_heartbeat(self):
        """每隔10秒查询指定接口保持 token 的有效性"""
        while True:
            if self.__heart_active:
                try:
                    log_level = self.log.level

                    self.log.setLevel(logging.ERROR)
                    response = self.heartbeat()
                    self.check_account_live(response)

                    self.log.setLevel(log_level)
                except:
                    self.autologin()
                time.sleep(30)
            else:
                time.sleep(1)

    def exit(self):
        """结束保持 token 在线的进程"""
        self.__heart_active = False

    @property
    def balance(self):
        return self.get_balance()

    def get_balance(self):
        """获取账户资金状况"""
        return self.do(self.config['balance'])

    @property
    def position(self):
        return self.get_position()

    def get_position(self):
        """获取持仓"""
        return self.do(self.config['position'])

    @property
    def entrust(self):
        return self.get_entrust()

    def get_entrust(self):
        """获取当日委托列表"""
        return self.do(self.config['entrust'])

    @property
    def current_deal(self):
        return self.get_current_deal()

    def get_current_deal(self):
        """获取当日委托列表"""
        # return self.do(self.config['current_deal'])
        self.log.warning('目前仅在 佣金宝/银河子类 中实现, 其余券商需要补充')

    def get_ipo_limit(self, stock_code):
        """
        查询新股申购额度申购上限
        :param stock_code: 申购代码 ID
        :return:
        """
        self.log.warning('目前仅在 佣金宝子类 中实现, 其余券商需要补充')

    def do(self, params):
        """发起对 api 的请求并过滤返回结果
        :param params: 交易所需的动态参数"""
        request_params = self.create_basic_params()
        request_params.update(params)
        response_data = self.request(request_params)
        try:
            format_json_data = self.format_response_data(response_data)
        except:
            # Caused by server force logged out
            return None
        return_data = self.fix_error_data(format_json_data)
        try:
            self.check_login_status(return_data)
        except LoginError:
            self.autologin()
        return return_data

    def create_basic_params(self):
        """生成基本的参数"""
        pass

    def request(self, params):
        """请求并获取 JSON 数据
        :param params: Get 参数"""
        pass

    def format_response_data(self, data):
        """格式化返回的 json 数据
        :param data: 请求返回的数据 """
        pass

    def fix_error_data(self, data):
        """若是返回错误移除外层的列表
        :param data: 需要判断是否包含错误信息的数据"""
        return data

    def format_response_data_type(self, response_data):
        """格式化返回的值为正确的类型
        :param response_data: 返回的数据
        """
        if type(response_data) is not list:
            return response_data

        int_match_str = '|'.join(self.config['response_format']['int'])
        float_match_str = '|'.join(self.config['response_format']['float'])
        for item in response_data:
            for key in item:
                try:
                    if re.search(int_match_str, key) is not None:
                        item[key] = cutils.str2num(item[key], 'int')
                    elif re.search(float_match_str, key) is not None:
                        item[key] = cutils.str2num(item[key], 'float')
                except ValueError:
                    continue
        return response_data

    def check_login_status(self, return_data):
        pass
