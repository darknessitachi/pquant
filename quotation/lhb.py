import aiohttp
import asyncio
import logging
import re
import json
from collections import defaultdict
from urllib.parse import urljoin
import datetime, time
from bs4 import BeautifulSoup

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate, sdch, br",
    "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Referer": "http://data.eastmoney.com/stock/tradedetail.html",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36"
}

base_url = "http://data.eastmoney.com/stock/tradedetail.html"


class BQueue(asyncio.Queue):
    """ Bureaucratic queue """

    def __init__(self, maxsize=0, capacity=0, *, loop=None):
        """
        :param maxsize: a default maxsize from tornado.queues.Queue,
            means maximum queue members at the same time.
        :param capacity: means a quantity of income tries before will refuse
            accepting incoming data
        """
        super().__init__(maxsize, loop=None)
        if capacity is None:
            raise TypeError("capacity can't be None")

        if capacity < 0:
            raise ValueError("capacity can't be negative")

        self.capacity = capacity
        self.put_counter = 0
        self.is_reached = False

    def put_nowait(self, item):

        if not self.is_reached:
            super().put_nowait(item)
            self.put_counter += 1

            if 0 < self.capacity == self.put_counter:
                self.is_reached = True


class LHB(object):
    def __init__(self, max_crawl, max_parse, concurrency=1, timeout=3600, delay=0.5, retries=3,
                 headers=None,
                 cookies=None):
        logging.basicConfig(level='INFO', format='[%(asctime)s] [%(levelname)s] %(name)s:%(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        self.log = logging.getLogger("LHB")
        self.headers = headers
        if not headers:
            self.headers = HEADERS
        else:
            self.headers = HEADERS.update(headers)
        if not cookies:
            cookies = {}
        self.cookies = cookies
        self.client = aiohttp.ClientSession(headers=headers, cookies=cookies)
        self.q_crawl = BQueue(capacity=max_crawl)
        self.q_parse = BQueue(capacity=max_parse)

        self.can_parse = False

        self.retries = retries
        self.data = []
        self.timeout = timeout
        self.delay = delay
        self.brief = defaultdict(set)
        self.concurrency = concurrency

    async def get_parsed_content(self, url):
        data = defaultdict(dict)

        def findall(pattern, string, index=None, default=None):
            pattern_compile = re.compile(pattern)
            patterned = pattern_compile.findall(string)
            if patterned and index is not None:
                try:
                    result = patterned[index]
                except Exception:
                    result = default
            elif patterned:
                result = patterned[0]
            else:
                result = default
            return result

        def convert_type(string, to_type, default=None):
            string = string.replace('%', '')
            if to_type in [int, float]:
                try:
                    return to_type(string)
                except Exception:
                    return default

        def get_sales(tr_str):
            sales_tmp = defaultdict()
            all_td = tr_str.find_all('td')
            sales_a = all_td[1].find_all('a')[1]
            sales_tmp['name'] = sales_a.string
            sales_tmp['code'] = findall(r'[0-9]{8}', sales_a['href'], default=99999999)
            sales_tmp['buy_cash'] = convert_type(all_td[2].string, float, 0.0)
            sales_tmp['buy_ratio'] = convert_type(all_td[3].string, float, 0.0)
            sales_tmp['sell_cash'] = convert_type(all_td[4].string, float, 0.0)
            sales_tmp['sell_ratio'] = convert_type(all_td[5].string, float, 0.0)
            return sales_tmp

        data['date'] = findall(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', url)
        data['code'] = findall(r'[0-9]{6}', url)
        content = await self.get_html_from_url(url)
        bs = BeautifulSoup(content, 'lxml')
        data['buy'] = []
        data['sell'] = []
        for tr in bs.find('table', {'id': 'tab-2'}).find('tbody').find_all('tr'):
            sales = get_sales(tr)
            data['buy'].append(sales)
        for tr in bs.find('table', {'id': 'tab-4'}).find('tbody').find_all('tr'):
            if tr.has_attr('class'):
                continue
            sales = get_sales(tr)
            data['sell'].append(sales)
        return data

    def get_urls(self, document):
        urls_to_parse = []
        data = json.loads(document.replace('var data_tab_2=', ''))['data']
        for d in data:
            urls_to_parse.append(urljoin(base_url, 'lhb,{},{}.html'.format(d['Tdate'], d['SCode'])))
        return urls_to_parse

    async def get_html_from_url(self, url):
        async with self.client.get(url) as response:
            if response.status != 200:
                self.log.error('BAD RESPONSE: {}'.format(response.status))
                return

            return await self.text(response)

    async def text(self, response):
        """Return BODY as text using encoding from .charset."""
        bytes_body = await response.read()
        encoding = response.charset or 'utf-8'
        return bytes_body.decode(encoding, 'ignore')

    async def crawl_url(self):
        current_url = await self.q_crawl.get()
        try:
            if current_url in self.brief['crawling']:
                return  # go to finally block first and then return

            self.log.info('Crawling: {}'.format(current_url))
            self.brief['crawling'].add(current_url)
            urls_to_parse = await self.get_links_from_url(current_url)
            self.brief['crawled'].add(current_url)

            for url in urls_to_parse:
                if self.q_parse.is_reached:
                    self.log.warning('Maximum parse length has been reached')
                    break

                if url not in self.brief['parsing']:
                    await self.q_parse.put(url)
                    self.brief['parsing'].add(url)
                    self.log.info('Captured: {}'.format(url))

            if not self.can_parse and self.q_parse.qsize() > 0:
                self.can_parse = True
        except Exception as exc:
            self.log.warn('Exception {}:'.format(exc))

        finally:
            self.q_crawl.task_done()

    async def parse_url(self):
        url_to_parse = await self.q_parse.get()
        self.log.info('Parsing: {}'.format(url_to_parse))

        try:
            content = await self.get_parsed_content(url_to_parse)
            self.data.append(content)

        except Exception:
            await self.q_parse.put(url_to_parse)
            self.log.error('An error has occurred during parsing{}'.format(url_to_parse),
                           exc_info=True)
        finally:
            self.q_parse.task_done()

    async def get_links_from_url(self, url):
        document = await self.get_html_from_url(url)
        return self.get_urls(document)

    async def __wait(self, name):

        if self.delay > 0:
            self.log.info('{} waits for {} sec.'.format(name, self.delay))
            await asyncio.sleep(self.delay)

    async def crawler(self):
        while True:
            await self.crawl_url()
            await self.__wait('Crawler')
        return

    async def parser(self):
        retries = self.retries
        while True:
            if self.can_parse:
                await self.parse_url()
            elif retries > 0:
                await asyncio.sleep(0.5)
                retries -= 1
            else:
                break
            await self.__wait('Parser')
        return

    async def run(self, start_date, end_date):
        start = time.time()
        print('Start working')
        sd = datetime.datetime.strptime(start_date, '%Y%m%d')
        ed = datetime.datetime.strptime(end_date, '%Y%m%d')
        url = 'http://data.eastmoney.com/DataCenter_V3/stock2016/TradeDetail/pagesize=50,page={},sortRule=-1,sortType=,startDate={},endDate={},gpfw=0,js=var%20data_tab_2.html?rt=24694707'
        step = 50
        for i in range(0, (ed - sd).days, step):
            loop_start_date = sd + datetime.timedelta(days=i)
            loop_end_date = loop_start_date + datetime.timedelta(days=step - 1)
            if loop_end_date > ed:
                loop_end_date = ed
            while True:
                resp = await self.get_html_from_url(
                    url.format(1, loop_start_date.strftime('%Y-%m-%d'), loop_end_date.strftime('%Y-%m-%d')))
                if resp:
                    pages = json.loads(resp.replace('var data_tab_2=', ''))['pages']
                    for page in range(pages):
                        await self.q_crawl.put(url.format(page + 1, loop_start_date.strftime('%Y-%m-%d'),
                                                          loop_end_date.strftime('%Y-%m-%d')))
                    break
                else:
                    break

        def task_completed(future):
            # This function should never be called in right case.
            # The only reason why it is invoking is uncaught exception.
            exc = future.exception()
            if exc:
                self.log.error('Worker has finished with error: {} '
                               .format(exc), exc_info=True)

        tasks = []
        fut_crawl = asyncio.ensure_future(self.crawler())
        fut_crawl.add_done_callback(task_completed)
        tasks.append(fut_crawl)
        for _ in range(self.concurrency):
            fut_parse = asyncio.ensure_future(self.parser())
            fut_parse.add_done_callback(task_completed)
            tasks.append(fut_parse)

        await asyncio.wait_for(self.q_crawl.join(), self.timeout)
        await self.q_parse.join()

        for task in tasks:
            task.cancel()

        self.client.close()

        end = time.time()
        print('Done in {} seconds'.format(end - start))

        if self.brief['crawling'] == self.brief['crawled']:
            self.log.warn('Crawling and crawled urls do not match')
        if len(self.brief['parsing']) == len(self.data):
            self.log.warn('Parsing length does not equal parsed length')
        self.log.info('Total crawled: {}'.format(len(self.brief['crawled'])))
        self.log.info('Total parsed: {}'.format(len(self.data)))
        self.log.info('Starting write to file')
        self._write_json(start_date + '-' + end_date)
        print('Parsed data has been stored.')
        print('Task done!')

    def _write_json(self, name):
        with open('{}-{}.json'.format(name, int(time.time())), 'w') as file:
            json.dump(self.data, file, ensure_ascii=False)


if __name__ == '__main__':
    lhb = LHB(concurrency=10, max_crawl=10000, max_parse=10000, delay=1)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(lhb.run('20050101', '20081231'))
    finally:
        loop.close()
