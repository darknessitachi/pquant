import requests

HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, sdch, br',
    'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Host': 'localhost.gf.com.cn:37022',
    'Origin': 'http://hippo.gf.com.cn',
    'Referer': 'http://hippo.gf.com.cn/',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36'
}
session = requests.session()
session.headers = HEADERS
resp = session.get('https://localhost.gf.com.cn:37022/getmac')
print (resp.text)
