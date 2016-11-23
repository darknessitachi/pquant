import re
import requests

def get_stock_type(stock_code):
    """判断股票ID对应的证券市场
    匹配规则
    ['50', '51', '60', '90', '110'] 为 sh
    ['00', '13', '18', '15', '16', '18', '20', '30', '39', '115'] 为 sz
    ['5', '6', '9'] 开头的为 sh， 其余为 sz
    :param stock_code:股票ID, 若以 'sz', 'sh' 开头直接返回对应类型，否则使用内置规则判断
    :return 'sh' or 'sz'"""
    assert type(stock_code) is str, 'stock code need str type'
    if stock_code.startswith(('sh', 'sz')):
        return stock_code[:2]
    if stock_code.startswith(('50', '51', '60', '90', '110', '113', '132', '204')):
        return 'sh'
    if stock_code.startswith(('00', '13', '18', '15', '16', '18', '20', '30', '39', '115', '1318')):
        return 'sz'
    if stock_code.startswith(('5', '6', '9')):
        return 'sh'
    return 'sz'

def get_all_stock_codes():
    """获取所有股票 ID 到 all_stock_code 目录下"""
    all_stock_codes_url = 'http://www.shdjt.com/js/lib/astock.js'
    grep_stock_codes = re.compile('~(\d+)`')
    response = requests.get(all_stock_codes_url)
    stock_codes = grep_stock_codes.findall(response.text)
    return stock_codes

def get_today_ipo():
    """
    查询今天可以申购的新股信息
    :return: 今日可申购新股列表 apply_code申购代码 price发行价格
    """

    import json
    import datetime
    import requests
    from utils.commutil import datetime2tick
    agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:43.0) Gecko/20100101 Firefox/43.0'
    headers = {
        'Host': 'xueqiu.com',
        'User-Agent': agent,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'deflate',
        'Cache-Control': 'no-cache',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://xueqiu.com/hq',
        'Connection': 'keep-alive'
    }


    base_url = 'https://xueqiu.com'
    ipo_url = "https://xueqiu.com/proipo/query.json?column=symbol,name,onl_subcode,onl_subbegdate,actissqty,onl" \
                   "_actissqty,onl_submaxqty,iss_price,onl_lotwiner_stpub_date,onl_lotwinrt,onl_lotwin_amount,stock_" \
                   "income&orderBy=onl_subbegdate&order=desc&stockType=&page=1&size=30&_=%s" % (str(datetime2tick()))

    session = requests.session()
    session.get(base_url, headers=headers)  # 产生cookies
    response = session.get(ipo_url, headers=headers)

    json_data = json.loads(response.text)
    ipo = []

    for line in json_data['data']:
        # if datetime.datetime(2016, 9, 14).ctime()[:10] == line[3][:10]:
        if datetime.datetime.now().ctime()[:10] == line[3][:10]:
            ipo.append({
                'code': line[0],
                'name': line[1],
                'applyCode': line[2],
                'ceiling':line[6],
                'price': line[7]
            })

    return ipo

def verify_code(image_path, broker='yjb'):
    """识别验证码，返回识别后的字符串，使用 tesseract 实现
    :param image_path: 图片路径
    :param broker: 券商 ['ht', 'yjb', 'gf', 'yh']
    :return recognized: verify code string"""
    if broker == 'yjb':
        return yjb_verify_code(image_path)
    else:
        raise RuntimeError('暂不支持!')

def yjb_verify_code(image_path):
    from .captcha import YJBCaptcha
    captcha = YJBCaptcha(imagePath=image_path)
    return captcha.string()
