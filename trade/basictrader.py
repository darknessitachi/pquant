# coding: utf-8
import logging
import re
import os
import time
import ssl
from threading import Thread
import random
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
                                       ssl_version=ssl.PROTOCOL_TLSv1_2)


class BasicTrader(object):
    __global_config_path = os.path.dirname(__file__) + '/config/global.json'

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Accept': 'text/html, application/xhtml+xml, */*',
        'Accept-Language': 'zh-CN',
        'Accept-Encoding': 'gzip, deflate'
    }

    TRADE_DIRECTIVE = ['home', 'verifyCode', 'login', 'logout', 'buy', 'sell', 'balance', 'position',
                       'entrust', 'ipo']
    DEFAULT_METHOD = 'get'

    def __init__(self, api_file):
        logging.basicConfig(level='DEBUG',
                            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s ',
                            datefmt='%Y-%m-%d %H:%M:%S')
        self.log = logging.getLogger('交易')

        self.httpClient = requests.session()
        self.httpClient.mount('https://', Ssl3HttpAdapter())

        self.config = cutils.file2dict(path=api_file)
        self.global_config = cutils.file2dict(self.__global_config_path)
        self.config.update(self.global_config)

        self.__heart_active = True
        self.__heart_thread = Thread(target=self.__send_heartbeat)
        self.__heart_thread.setDaemon(True)

    # TODO 增加注解
    def _request(self, request_api):
        self.log.debug(
            'url:{},params:{},data:{}'.format(request_api['url'], request_api['params'], request_api['data']))
        resp = self.httpClient.request(method=request_api['method'],
                                       url=request_api['url'],
                                       params=request_api['params'],
                                       data=request_api['data'],
                                       headers=request_api['headers'])
        if resp.status_code == 200:
            self.log.debug('status:{},url:{}'.format(resp.status_code, request_api['url']))
            return resp
        else:
            self.log.error(
                'status:{},url:{},params:{},data:{},response_text:{}'.format(resp.status_code,
                                                                             request_api['url'],
                                                                             request_api['params'],
                                                                             request_api['data'],
                                                                             resp.text))
            return False

    def do(self, directive, params=None, data=None, callback=None, handle=None, add_basic_params=True):
        """发起对 api 的请求并过滤返回结果
        :param add_basic_params:
        :param data:
        :param directive:
        :param callback:
        :param handle:
        :param params: 交易所需的动态参数"""
        if not directive or type(directive) is not str or directive not in self.TRADE_DIRECTIVE:
            raise TradeError("无效的交易指令")
        request_api = self.__get_request_api(directive, params, data, add_basic_params)
        resp = self._request(request_api)
        if callback:
            callback(resp)
        if handle:
            return handle(resp)
        return resp.text

    def __get_request_api(self, directive, params, data, add_basic_params):
        basic = self.get_config('basic')
        config_api = self.get_config(directive)

        basic_params = basic['params']
        cur_params_ = config_api['params'] if 'params' in config_api else {}
        cur_params_ = self.__resolve_params(cur_params_)
        if not params:
            params = {}
        if add_basic_params:
            cur_params_ = cur_params_.update(basic_params)
        cur_params_ = params.update(cur_params_)

        if not data:
            data = {}
        data_ = config_api['data'] if 'data' in config_api else {}
        data_ = data_.update(data)

        request_api = dict(
            method=config_api['method'] if 'method' in config_api else self.DEFAULT_METHOD,
            url=config_api['api'] if 'api' in config_api else basic['api'],
            params=cur_params_,
            data=data_,
            headers=config_api['headers'] if 'headers' in config_api else self.HEADERS
        )
        return request_api

    def autologin(self, limit=10):
        """实现自动登录
        :param limit: 登录次数限制
        """
        for _ in range(limit):
            if self.login():
                break
        else:
            raise LoginError('登录失败次数过多, 请检查密码是否正确 / 券商服务器是否处于维护中 / 网络连接是否正常')
            # self.__keepalive()

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

    def logout(self):
        """结束保持 token 在线的进程"""
        self.__heart_active = False
        self.__heart_thread.join(timeout=10)

    @property
    def balance(self):
        return self.get_balance()

    def get_balance(self):
        """获取账户资金状况"""
        return self.do(params=self.config['balance'], callback=self.format_response_data)

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

    def get_config(self, config_key):
        result = {}
        try:
            return cutils.pathGet(self.config, config_key)
        except KeyError:
            return result

    def __resolve_params(self, dict_):
        result = {}
        if type(dict_) is not dict:
            return dict_
        for key, val in dict_.items():
            if type(val) is not dict:
                result.setdefault(key,val)
            elif 'eval' in val and 'formula' in val:
                if val.get('eval'):
                    result.setdefault(key, eval(val.get('formula')))
                else:
                    result.setdefault(key, val.get('formula'))

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
