import asyncio

import requests
from abc import abstractmethod
import logging
import time
import math

class BasicQuotation:
    def __init__(self, url):
        self.__stocks = list()
        self.__url = url
        self._session = requests.session()
        logging.basicConfig(level='INFO', format='[%(asctime)s] [%(levelname)s] %(name)s:%(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        self.log = logging.getLogger('quotation')

    def subscribe(self, code):
        if not self.__stocks.count(code):
            self.log.info('[{}]已添加到订阅列表.'.format(code))
            self.__stocks.append(code)

    def unsubscribe(self, code):
        if self.__stocks.count(code):
            self.log.info('[{}]已从订阅列表中移除.'.format(code))
            self.__stocks.remove(code)

    @property
    def subscribed(self):
        return self.__stocks

    def getQuotationData(self):
        """
            行情数据
        :return: dict
        """
        start = time.time()
        if not self.__stocks:
            print('未订阅任何股票行情！')
            return {}
        tasks = []
        params = self._convertRequestParams(self.__stocks)
        if type(params) is not list:
            params = [params]
        for param in params:
            task = self.__getResponseData(param=param)
            tasks.append(task)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        content = loop.run_until_complete(asyncio.gather(*tasks))
        end = time.time()
        self.log.info('行情刷新完毕，耗时{}ms'.format(math.ceil((end - start)*1000)))
        return content

    async def __getResponseData(self, param):
        headers = {
            'Accept-Encoding': 'gzip'
        }
        url = self.__url + param
        response = self._session.get(url, timeout=5, headers=headers)
        if response.status_code != 200:
            self.log.error('{} BAD RESPONSE: {}'.format(url, response.status_code))
            return
        response_content = response.content
        return self._formatResponseData(param, response_content, response.encoding)

    @abstractmethod
    def _convertRequestParams(self, codes):
        return codes

    @abstractmethod
    def _formatResponseData(self, param, response, encoding):
        """
            解析返回结果
        :param response: 返回结果字符串
        :return: 规范化的 dict
        """
        pass
