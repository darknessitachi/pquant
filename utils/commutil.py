def file2dict(path):
    import json
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def grep_comma(num_str):
    return num_str.replace(',', '')


def str2num(num_str, convert_type='float'):
    num = float(grep_comma(num_str))
    return num if convert_type == 'float' else int(num)


def pathGet(dictionary, path):
    for item in path.split("/"):
        dictionary = dictionary[item]
    return dictionary


def pathSet(dictionary, path, setItem):
    path = path.split("/")
    key = path[-1]
    dictionary = pathGet(dictionary, "/".join(path[:-1]))
    dictionary[key] = setItem


def str2dict(str_):
    """
        str2dict
    :param str_:
    :return:
    """
    import demjson
    # str_ = re.sub(r"\{\s*(\w)", r'{"\1', str_)
    # str_ = re.sub(r"([\'\]\}]),\s*(\w)", r'\1,"\2', str_)
    # str_ = re.sub(r"(\w):", r'\1":', str_)
    # str_ = str_.replace("'", "\"")
    return demjson.decode(str_)


def show_image(image_path):
    """显示图片"""
    from PIL import Image
    img = Image.open(image_path)
    img.show()
    # 关闭图片后输入答案
    s = input('input the pics answer :')
    return s


def get_mac_address():
    import uuid
    # 获取mac地址 link: http://stackoverflow.com/questions/28927958/python-get-mac-address
    return ("".join(c + "-" if i % 2 else c for i, c in enumerate(hex(
        uuid.getnode())[2:].zfill(12)))[:-1]).upper()


def datetime2tick(param_time=None, format="%Y-%m-%d %H:%M:%S"):
    from datetime import datetime
    import time
    if not param_time:
        cur_time = datetime.now()
    elif type(param_time) is str:
        cur_time = datetime.strptime(param_time, format)
    elif type(param_time) is datetime:
        cur_time = param_time
    else:
        raise RuntimeError('参数错误,请输入字符串如:"2010-01-01 12:00:00" 或者 输入datetime类型日期')
    return int(time.mktime(cur_time.timetuple()) * 1000)


def tick2datetime(time_tick):
    import time
    tick = time.localtime(time_tick / 1000)
    return time.strftime("%Y-%m-%d %H:%M:%S", tick)
