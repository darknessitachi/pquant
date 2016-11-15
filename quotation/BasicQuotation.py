import asyncio

import requests
from abc import abstractmethod


class BaseQuotation:
    __url = None
    __stocks = list()
    max_num = 800

    def __init__(self, url, stocks):
        self.__url = url
        self.__stocks = stocks
        self._session = None

    def addStock(self, stockCode):
        self.__stocks.append(stockCode)

    def removeStock(self, stockCode):
        self.__stocks.remove(stockCode)

    def getQuotationData(self):
        """
            行情数据
        :return: dict
        """
        self._session = requests.session()
        tasks = []
        stacks = self.resolveStockCodes(self.__stocks)
        params = self.convertRequestParams(stacks)
        if type(params) is not list:
            params = [params]
        for param in params:
            task = self.awaitResponseData(param=param)
            tasks.append(task)
        try:
            eventLoop = asyncio.get_event_loop()
        except RuntimeError:
            eventLoop = asyncio.new_event_loop()
            asyncio.set_event_loop(eventLoop)
        responseContent = eventLoop.run_until_complete(asyncio.gather(*tasks))
        return self.formatResponseData(responseContent)

    async def awaitResponseData(self, param):
        content, encoding = await self.getResponseData(param)
        return str(content, encoding=encoding)

    async def getResponseData(self, param):
        headers = {
            'Accept-Encoding': 'gzip'
        }
        response = requests.get(self.__url, params=param, timeout=5, headers=headers)
        print(response.url)
        return response.content, response.encoding
        # async with self._session.get(self.__url + param, timeout=5, headers=headers) as r:
        #     response_text = await r.content
        #     return response_text

    @abstractmethod
    def convertRequestParams(self, stockCodes):
        pass

    @abstractmethod
    def resolveStockCodes(self, stockCodes):
        """
            解析标的代码到对应行情提供商的代码,需要子类实现
            如：
            股票代码        新浪          腾讯
            600887      sh600887       s600887
        :param stockCodes: 标的代码list
        :return: 返回股票编码列表['sh600887','sh601717']
        """
        pass

    @abstractmethod
    def formatResponseData(self, response):
        """
            解析返回结果
        :param response: 返回结果字符串
        :return: 规范化的 dict
        """
        pass
