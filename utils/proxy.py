import asyncio
from asyncio import Queue
import aiohttp
import time
import re


class Crawl:
    def __init__(self, url, test_url, *, number=10, max_tasks=5):
        self.url = url
        self.test_url = test_url
        self.number = number
        self.max_tasks = max_tasks
        self.url_queue = Queue()
        self.raw_proxy_queue = Queue()
        self.session = aiohttp.ClientSession()  # tips: connection pool

    async def fetch_page(self, url):
        async with aiohttp.get(url) as response:
            try:
                assert response.status == 200
                print("OK!", response.url)
                return await response.text()
            except AssertionError:
                print('Error!', response.url, response.status)

    async def filter_page(self, url):
        page = await self.fetch_page(url)
        if page:
            pattern = re.compile(
                r'<tr>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td>.*?</td>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?</tr>',
                re.S)
            data = pattern.findall(page)
            print(len(data))
            for raw in data:
                item = list(map(lambda word: word.lower(), raw))
                await self.raw_proxy_queue.put(
                    {'ip': item[0], 'port': item[1], 'anonymous': item[2], 'protocol': item[3], 'speed': item[4],
                     'checking-time': item[5]})
            if not self.raw_proxy_queue.empty():
                print('OK! raw_proxy_queue size: ', self.raw_proxy_queue.qsize())

    async def verify_proxy(self, proxy):
        addr = proxy['protocol'] + '://' + proxy['ip'] + ':' + proxy['port']
        conn = aiohttp.ProxyConnector(proxy=addr)
        try:
            session = aiohttp.ClientSession(connector=conn)
            with aiohttp.Timeout(10):
                start = time.time()
                async with session.get(
                        self.test_url) as response:  # close connection and response, otherwise will tip: Unclosed connection and Unclosed response
                    end = time.time()
                    try:
                        assert response.status == 200
                        print('Good proxy: {} {}s'.format(proxy['ip'], end - start))
                    except:  # ProxyConnectionError, HttpProxyError and etc?
                        print('Bad proxy: {}, {}, {}s'.format(proxy['ip'], response.status, end - start))
        except:
            print('timeout {}, q size: {}'.format(proxy['speed'], self.raw_proxy_queue.qsize()))
        finally:  # close session when timeout
            session.close()

    async def fetch_worker(self):
        while True:
            url = await self.url_queue.get()
            try:
                await self.filter_page(url)
            finally:
                self.url_queue.task_done()

    async def verify_worker(self):
        while True:
            raw_proxy = await self.raw_proxy_queue.get()
            if raw_proxy['protocol'] == 'https':  # only http can be used
                continue
            try:
                await self.verify_proxy(raw_proxy)
            finally:
                try:
                    self.raw_proxy_queue.task_done()
                except:
                    pass

    async def run(self):
        await asyncio.wait([self.url_queue.put(self.url + repr(i + 1)) for i in range(self.number)])
        fetch_tasks = [asyncio.ensure_future(self.fetch_worker()) for _ in range(self.max_tasks)]
        verify_tasks = [asyncio.ensure_future(self.verify_worker()) for _ in range(10 * self.max_tasks)]
        tasks = fetch_tasks + verify_tasks
        await self.url_queue.join()
        self.session.close()  # close session, otherwise shows error
        print("url_queue done")
        self.raw_proxy_queue.join()
        print("raw_proxy_queue done")
        await self.proxy_queue.join()
        for task in tasks:
            task.cancel()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    crawler = Crawl('http://www.ip84.com/gn-http/', test_url='https://www.baidu.com')
    loop.run_until_complete(crawler.run())
    loop.close()