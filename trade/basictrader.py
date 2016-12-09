# coding: utf-8
import logging
import os
import time
from abc import abstractmethod
from threading import Thread
from utils.commutil import my_assert, pathGet, file2dict
import requests


class LoginError(Exception):
    def __init__(self, message=None):
        super(LoginError, self).__init__()
        self.message = message


class TradeError(Exception):
    def __init__(self, message=None):
        super(TradeError, self).__init__()
        self.message = message


class BasicTrader(object):
    __global_config_path = os.path.dirname(__file__) + '/config/global.json'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Accept': 'text/html, application/xhtml+xml, */*',
        'Accept-Language': 'zh-CN',
        'Accept-Encoding': 'gzip, deflate'
    }
    TRADE_DIRECTIVE = ['home', 'verifyCode', 'login', 'logout', 'buy', 'sell', 'balance', 'position',
                       'entrust', 'ipo', "current_deal", "cancel_entrust"]
    DEFAULT_METHOD = 'get'

    def __init__(self, api_file):
        # TODO 增加全局日志系统
        logging.basicConfig(level='DEBUG',
                            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s ',
                            datefmt='%Y-%m-%d %H:%M:%S')
        self.log = logging.getLogger('交易')

        self.httpClient = requests.session()
        self.httpClient.mount('https://', Ssl3HttpAdapter())
        self.httpClient.headers = self.HEADERS

        self.config = file2dict(path=api_file)
        self.global_config = file2dict(self.__global_config_path)
        self.config.update(self.global_config)

        self.login_status = False  # 登录状态

        self.__heart_active = True  # 是否启动心跳线程
        self.__heart_thread = Thread(target=self.__send_heartbeat)
        self.__heart_thread.setDaemon(True)

    def login(self, limit=10):
        """实现自动登录
        :param limit: 登录次数限制
        """
        for _ in range(limit):
            if self._login():
                self.login_status = True
                break
            else:
                time.sleep(5)
        else:
            raise LoginError('登录失败次数过多, 请检查密码是否正确 / 券商服务器是否处于维护中 / 网络连接是否正常')
        self.__keepalive()

    @abstractmethod
    def _login(self):
        pass

    def is_login(self):
        return self.login_status

    @abstractmethod
    def _default_response_handle(self, resp):
        """格式化response
        :param resp: response
        """
        pass

    def logout(self):
        self.__heart_active = False
        self.__heart_thread.join(timeout=10)
        self.login_status = False
        return self._logout()

    @abstractmethod
    def _logout(self):
        """结束保持 token 在线的进程"""
        pass

    @abstractmethod
    def get_balance(self):
        """获取账户资金状况"""
        pass

    @abstractmethod
    def get_position(self, stock_code):
        """获取持仓"""
        pass

    @abstractmethod
    def get_entrust(self):
        """获取当日委托列表"""
        pass

    def get_config(self, config_key):
        result = {}
        try:
            return pathGet(self.config, config_key)
        except KeyError:
            return result

    def do(self, directive, params=None, data=None, callback=None, handle=None, meta_data=None):
        """
            发起对 api 的请求并过滤返回结果
            :param directive: 指令必需在TRADE_DIRECTIVE定义的列表中
            :param params:  get 请求动态参数
            :param data:    post 请求动态参数
            :param callback:回调函数,缺省执行_default_response_callback 方法
            :param handle: 处理器函数，缺省执行_default_response_handle 方法
            :param meta_data: 格式化元数据信息
        """
        my_assert(directive in self.TRADE_DIRECTIVE, "无效的交易指令{}".format(directive))
        request_api = self.__get_request_api(directive, params, data)
        self.log.info('{}-{}'.format(directive, request_api))
        resp = self.httpClient.request(**request_api)
        if resp.status_code == 200:
            if callback:
                callback(resp)
            if handle and meta_data:
                return handle(resp, meta_data)
            elif handle:
                return handle(resp)
            else:
                return self._default_response_handle(resp)
        else:
            self.log.error('指令[{}]失败,状态码:{},请求地址:{}'.format(directive, resp.status_code, resp.url))
            raise TradeError('指令[{}]失败,状态码:{},请求地址:{}'.format(directive, resp.status_code, resp.url))

    def __get_request_api(self, directive, params, data):
        basic_api = self.get_config('basic')['api']
        config_api = self.get_config(directive)
        cur_params_ = config_api['params'] if 'params' in config_api else {}

        if not params:
            params = {}
        cur_params_.update(params)

        if not data:
            data = {}
        data_ = config_api['data'] if 'data' in config_api else {}
        data_.update(data)

        headers_ = dict({}, **self.httpClient.headers)
        headers_.update(config_api['headers'] if 'headers' in config_api else {})
        request_api = dict(
            method=config_api['method'] if 'method' in config_api else self.DEFAULT_METHOD,
            url=config_api['api'] if 'api' in config_api else basic_api,
            params=cur_params_,
            data=data_,
            headers=headers_
        )
        return request_api

    @abstractmethod
    def _heartbeat(self):
        """
            心跳指令
        :return:
        """
        pass

    def _default_response_callback(self, resp):
        return self._check_status(resp)

    @abstractmethod
    def _check_status(self, resp):
        """
           检查各种状态,抛出相应错误
        :return: 没有错误时返回True
        :except LoginError,TradeError
        """
        pass

    def __keepalive(self):
        """启动保持在线的进程 """
        if self.__heart_thread.is_alive():
            self.__heart_active = True
        else:
            # TODO 线程重起报错 RuntimeError: threads can only be started once
            self.__heart_thread.start()

    def __send_heartbeat(self):
        """每隔10秒查询指定接口保持 token 的有效性"""
        while True:
            if self.__heart_active:
                try:
                    self._check_status(self._heartbeat())
                except LoginError as e:
                    self.log.error(e)
                    self.login_status = False
                    self.__heart_active = False
                except requests.ConnectionError as e:
                    self.log.error(e)
                    continue
                finally:
                    time.sleep(30)
            else:
                time.sleep(5)
