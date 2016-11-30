import asyncio
import aiohttp
import logging
import time
import math
from abc import abstractclassmethod


class BasicQuotation:
    def __init__(self, crawl_api, headers=None, cookies=None):
        self.__stocks = list()
        self.__crawl_api = crawl_api
        logging.basicConfig(level='INFO', format='[%(asctime)s] [%(levelname)s] %(name)s:%(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        self.log = logging.getLogger('quotation')
        self.headers = headers
        self.event_loop = asyncio.new_event_loop()

        if not cookies:
            self.cookies = dict()
        else:
            self.cookies = cookies

    def subscribe(self, codes):
        if type(codes) is not list:
            if not self.__stocks.count(codes):
                self.log.info('[{}]已添加到订阅列表.'.format(codes))
                self.__stocks.append(codes)
        else:
            for code in codes:
                self.subscribe(code)

    def unsubscribe(self, codes):
        if type(codes) is not list:
            if self.__stocks.count(codes):
                self.log.info('[{}]已从订阅列表中移除.'.format(codes))
                self.__stocks.remove(codes)
        else:
            for code in codes:
                self.unsubscribe(code)

    @property
    def subscribed(self):
        return self.__stocks

    def refresh(self):
        start = time.time()
        if not self.__stocks:
            self.log.info('未订阅任何股票行情.')
            return {}
        asyncio.set_event_loop(self.event_loop)
        future = asyncio.ensure_future(self._run(self.event_loop))
        content = self.event_loop.run_until_complete(future)
        end = time.time()
        result = dict()
        for future_result in content:
            if type(future_result) is dict:
                for j in future_result.keys():
                    result.__setitem__(j, future_result.get(j))
        self.log.info('行情刷新完毕，耗时{}ms'.format(math.ceil((end - start) * 1000)))
        return result

    async def _fetch(self, url, stock):
        async with aiohttp.ClientSession(headers=self.headers, cookies=self.cookies) as session:
            async with session.get(url=url) as response:
                return self._format_response(await response.text(), stock)

    async def _run(self, loop):
        """
            行情数据
        :return: dict
        """

        def task_completed(future):
            # This function should never be called in right case.
            # The only reason why it is invoking is uncaught exception.
            exc = future.exception()
            if exc:
                self.log.error('Worker has finished with error: {} '.format(exc), exc_info=True)

        tasks = []
        for stock in self.__stocks:
            crawl_url = self._curl_handle(self.__crawl_api, stock)
            crawl_future = asyncio.ensure_future(self._fetch(crawl_url, stock))
            crawl_future.add_done_callback(task_completed)
            tasks.append(crawl_future)
        responses = await asyncio.gather(*tasks)
        for task in tasks:
            task.cancel()
        return responses

    def _curl_handle(self, crawl_api, param):
        return crawl_api + param

    @abstractclassmethod
    def _format_response(self, response, stock):
        """
            解析返回结果,需要子类实现
        :param response: 返回结果字符串
        :param stock: 股票代码
        :return: 规范化的 dict
        """
        pass


if __name__ == '__main__':
    q = BasicQuotation('https://app.leverfun.com/timelyInfo/timelyOrderForm?stockCode=')
    q.subscribe('601717')
    q.subscribe('600887')
    q.subscribe('600315')
    q.subscribe(['000001'])
    # print(q.subscribed)
    q.refresh()
    q.unsubscribe(['601717', '000003'])
    # print(q.subscribed)
    q.refresh()
