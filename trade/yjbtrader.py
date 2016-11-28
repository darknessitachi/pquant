#!/usr/bin/env python3
from __future__ import division
import json
import os
import random
import re
import tempfile
import urllib.parse
import demjson
import utils.commutil as cutils
import utils.stockutil as sutils
from trade.basictrader import LoginError
from trade.basictrader import TradeError
from trade.basictrader import BasicTrader


class YJBTrader(BasicTrader):
    api_file = os.path.dirname(__file__) + '/config/yjb.json'
    market = {"sh": 1, "sz": 2}

    def __init__(self, account_file):
        super(YJBTrader, self).__init__(api_file=self.api_file)
        self.account_info = cutils.file2dict(path=account_file)

    def _login(self, throw=False):
        self.do(directive="home")
        verify_code = self.do(directive='verifyCode',
                              handle=self.recognize_code,
                              params=dict(
                                  randomStamp=random.random()
                              ))
        if not verify_code:
            return False

        login_status, result = self.do(directive='login',
                                       data=dict(
                                           mac_addr=cutils.get_mac_address(),
                                           account_content=self.account_info['account'],
                                           password=urllib.parse.unquote(self.account_info['password']),
                                           validateCode=verify_code
                                       ),
                                       handle=self._login_handle)
        if login_status is False and throw:
            raise LoginError(result)
        return login_status

    def _logout(self):
        self.do(directive="logout")

    def recognize_code(self, resp):
        """获取并识别返回的验证码
        :return:失败返回 False 成功返回 验证码"""
        # 保存验证码
        image_path = os.path.join(tempfile.gettempdir(), 'vcode_%d' % os.getpid())
        with open(image_path, 'wb') as f:
            f.write(resp.content)

        verify_code = sutils.verify_code(image_path, 'yjb')
        self.log.debug('verify code detect result: %s' % verify_code)
        os.remove(image_path)
        return verify_code

    def _login_handle(self, resp):
        self.log.debug('login response: %s' % resp.text)
        if resp.text.find('上次登陆') != -1:
            return True, None
        else:
            return False, resp.text

    def _heartbeat(self):
        return self._balance()

    def _check_status(self, data):
        """
            检查各种状态,抛出相应错误
        :param data:
        :return:
        """
        index = 0
        error_no = data[index].get('error_no') if type(data) == list and data[index].get(
            'error_no') is not None else None
        error_info = data[index].get('error_info') if type(data) == list and data[index].get(
            'error_no') is not None else None

        if error_no == '-1':
            raise LoginError('error_no:{},error_info:{}'.format(error_no, error_info))
        elif error_no is not None and error_no != '0':
            raise TradeError('error_no:{},error_info:{}'.format(error_no, error_info))
        return True

    def _balance(self):
        """获取账户资金状况"""
        return self.do(directive='balance',
                       params=self.get_basic_params(),
                       handle=self._default_response_handle)

    def _position(self):
        """获取持仓"""
        return self.do(directive='position',
                       params=self.get_basic_params(),
                       handle=self._default_response_handle)

    def _entrust(self):
        """获取当日委托列表"""
        return self.do(directive='entrust',
                       params=self.get_basic_params(),
                       handle=self._default_response_handle)

    def cancel_entrust(self, entrust_no, stock_code):
        """撤单
        :param entrust_no: 委托单号
        :param stock_code: 股票代码"""
        data = self.do(directive='cancel_entrust',
                       params=dict(
                           self.get_basic_params(),
                           entrust_no=entrust_no,
                           stock_code=stock_code),
                       handle=self._default_response_handle)
        return self._check_status(data)

    @property
    def current_deal(self):
        return self.get_current_deal()

    def get_current_deal(self):
        """获取当日成交列表"""
        """
        [{'business_amount': '成交数量',
        'business_price': '成交价格',
        'entrust_amount': '委托数量',
        'entrust_bs': '买卖方向',
        'stock_account': '证券帐号',
        'fund_account': '资金帐号',
        'position_str': '定位串',
        'business_status': '成交状态',
        'date': '发生日期',
        'business_type': '成交类别',
        'business_time': '成交时间',
        'stock_code': '证券代码',
        'stock_name': '证券名称'}]
        """
        return self.do(directive='current_deal', params=self.get_basic_params(), handle=self._default_response_handle)

    # TODO: 实现买入卖出的各种委托类型
    def buy(self, stock_code, price, amount=0, volume=0, entrust_prop=0):
        """买入卖出股票
        :param stock_code: 股票代码
        :param price: 卖出价格
        :param amount: 卖出股数
        :param volume: 卖出总金额 由 volume / price 取整， 若指定 amount 则此参数无效
        :param entrust_prop: 委托类型，暂未实现，默认为限价委托
        """
        entrust_amount = amount if amount else volume // price // 100 * 100
        return self.__trade(directive='buy',
                            stock_code=stock_code,
                            price=price,
                            entrust_amount=entrust_amount,
                            entrust_prop=entrust_prop)

    def sell(self, stock_code, price, amount=0, volume=0, entrust_prop=0):
        """卖出股票
        :param stock_code: 股票代码
        :param price: 卖出价格
        :param amount: 卖出股数
        :param volume: 卖出总金额 由 volume / price 取整， 若指定 amount 则此参数无效
        :param entrust_prop: 委托类型，暂未实现，默认为限价委托
        """
        entrust_amount = amount if amount else volume // price // 100 * 100
        return self.__trade(directive='sell',
                            stock_code=stock_code,
                            price=price,
                            entrust_amount=entrust_amount,
                            entrust_prop=entrust_prop)

    def __trade(self, directive, stock_code, price, entrust_amount, entrust_prop):
        account = self.__get_shareholder_account(stock_code)
        basic_params = self.get_basic_params()
        params = dict(
            entrust_bs=1 if directive == 'buy' else 2,  # 买入1 卖出2,
            entrust_prop=entrust_prop,
            entrust_price=price,
            entrust_amount=entrust_amount,
            stock_code='{:0>6}'.format(stock_code),
            elig_riskmatch_flag=1
        )
        params.update(account)
        params.update(basic_params)
        return self.do(directive=directive, params=params, handle=self._default_response_handle)

    def ipo(self):
        """
        新股申购
        """
        basic_params = self.get_basic_params()
        ipos = sutils.get_today_ipo()
        for ipo in ipos:
            market = sutils.get_stock_type(ipo['code'])
            params = dict(
                basic_params,
                stock_account=self.account_info[market],  # '沪深帐号'
                exchange_type=self.market[market],  # '沪市1 深市2'
                entrust_prop=0,
                stock_code=ipo['applyCode']
            )
            data = self.do(directive='ipo', params=params, handle=self._default_response_handle)
            if self._check_status(data):
                self.buy(stock_code=ipo['applyCode'],
                         price=0.00,
                         amount=data['enable_amount'] if data['high_amount'] > data['enable_amount'] else data['high_amount'])

    def __get_shareholder_account(self, stock_code):
        """获取股票对应的证券市场和帐号"""
        market = sutils.get_stock_type(stock_code)
        return dict(
            exchange_type=self.market[market],
            stock_account=self.account_info[market]
        )

    @staticmethod
    def get_basic_params():
        basic_params = dict(
            CSRF_Token='undefined',
            timestamp=random.random(),
        )
        return basic_params

    @staticmethod
    def __format_response_data(resp):
        # 获取 returnJSON
        return_json = json.loads(resp.text)['returnJson']
        raw_json_data = demjson.decode(return_json)
        fun_data = raw_json_data['Func%s' % raw_json_data['function_id']]
        return fun_data

    def _default_response_handle(self, resp):
        """格式化response
        :param resp: response
        """
        data = self.__format_response_data(resp)
        if type(data) is not list:
            return data
        int_match_str = '|'.join(self.config['response_format']['int'])
        float_match_str = '|'.join(self.config['response_format']['float'])
        for item in data:
            for key in item:
                try:
                    if re.search(int_match_str, key) is not None:
                        item[key] = cutils.str2num(item[key], 'int')
                    elif re.search(float_match_str, key) is not None:
                        item[key] = cutils.str2num(item[key], 'float')
                except ValueError:
                    continue
        return data


if __name__ == '__main__':
    import time

    user = YJBTrader('yjb.json')
    user.login(10)
    print(user.balance)
    time.sleep(10000)
