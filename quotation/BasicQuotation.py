import asyncio

import requests
from abc import abstractmethod


class BasicQuotation:
    def __init__(self, url):
        self.__stocks = list()
        self.__url = url
        self._session = requests.session()

    def subscribe(self, stockCode):
        if not self.__stocks.count(stockCode):
            self.__stocks.append(stockCode)

    def unsubscribe(self, stockCode):
        if self.__stocks.count(stockCode):
            self.__stocks.remove(stockCode)

    @property
    def subscribed(self):
        return self.__stocks

    def getQuotationData(self):
        """
            行情数据
        :return: dict
        """
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
            eventLoop = asyncio.get_event_loop()
        except RuntimeError:
            eventLoop = asyncio.new_event_loop()
            asyncio.set_event_loop(eventLoop)
        responseContent = eventLoop.run_until_complete(asyncio.gather(*tasks))
        return responseContent

    async def __getResponseData(self, param):
        headers = {
            'Accept-Encoding': 'gzip'
        }
        response = self._session.get(self.__url + param, timeout=5, headers=headers)
        return self._formatResponseData(param, response.content, response.encoding)

    @abstractmethod
    def _convertRequestParams(self, stockCodes):
        return stockCodes

    @abstractmethod
    def _formatResponseData(self, param, response, encoding):
        """
            解析返回结果
        :param response: 返回结果字符串
        :return: 规范化的 dict
        """
        pass
