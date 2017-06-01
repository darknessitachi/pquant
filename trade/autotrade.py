import pywinauto
import pywinauto.clipboard
import pywinauto.application
import time
import sys
import logging
from collections import defaultdict
from pywinauto.findwindows import WindowNotFoundError, find_element, find_elements, find_window, find_windows

market = {
    "SH": "上海.*",
    "SZ": "深圳.*"
}
direction = {
    'B': "买入",
    'S': "卖出"
}


def format_date(value):
    from datetime import datetime
    return datetime.strptime(value, '%Y%m%d')


def format_market(value):
    import re
    for key, val in market.items():
        m = re.match(val, value)
        if m:
            return key


def format_time(value):
    from datetime import datetime
    return datetime.strptime(value, '%H:%M:%S')


def format_direction(value):
    import re
    for key, val in direction.items():
        m = re.match(val, value)
        if m:
            return key


def get_pos(row, offset=22, height=15):
    return ((offset + (row - 1) * height) + (row - 1) + (offset + row * height) + (row - 1)) // 2


logging.basicConfig(level='INFO', format='[%(asctime)s] [%(levelname)s] %(name)s:%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger('trade')


class HeXin:
    """
        同花顺交易客户端操作类
    """
    is_connected = False
    __app = pywinauto.application.Application()  # app程序handle
    main_window_title_re = '网上股票交易系统.*'

    def __init__(self, process=None):
        self.account = defaultdict()
        if process:
            self.connect(process=process)

    def __init_hwnd(self):
        """
            初始化窗口操作句柄
        :return:
        """
        try:
            self.__main_window = self.__app.window(title_re=self.main_window_title_re)
            self.__dialog_hwnd = find_window(top_level_only=False,
                                             process=self.__app.process,
                                             class_name='AfxMDIFrame42s')
            self.toolbar = self.__app.window(top_level_only=False,
                                             class_name='ToolbarWindow32').wrapper_object()
            self.tree = self.__app.window(top_level_only=False,
                                          class_name='SysTreeView32',
                                          parent=self.__dialog_hwnd).wrapper_object()
        except Exception as e:
            raise TreadError("000001", "初始化窗口连接句柄出错!{}".format(e))

    def __start(self):
        """
            启动应用程序
        """
        app_path = ""
        try:
            log.info('启动程序{}'.format(app_path))
            self.__app.start(app_path)
        except pywinauto.application.AppStartError:
            log.error('程序启动失败，当前路径:{}'.format(app_path))
            sys.exit()

    def __init_account(self):
        self.account.setdefault('ipo_quota', self.get_ipo_quota())
        self.account.setdefault('account_info', self.__getBalance())

    def login(self, account, password, verifyCode):
        self.__start()
        if self.__app.window(title="用户登录").Exists():
            login_window = self.__app.window(title='用户登录')
            login_window.Edit1.SetEditText(account)
            time.sleep(.2)
            login_window.Edit2.SetEditText(password)
            time.sleep(.2)
            login_window.Edit3.SetEditText(verifyCode)
            time.sleep(.2)
            login_window.Button1.Click()
            self.__closePopupWindows()
            return self.__app.window(title_re=self.main_window_title_re).Exists()
        else:
            return False

    def connect(self, process=None):
        try:
            # process = find_element(title_re=title_re).process_id
            self.__app.connect(process=process)
            log.info("已连接应用程序，PID={}".format(process))
            self.__init_hwnd()
            self.__init_account()
            self.is_connected = True
        except pywinauto.application.ProcessNotFoundError:
            self.is_connected = False

    @staticmethod
    def wait(seconds):
        if seconds >= 1:
            log.info('等待{}s...'.format(seconds))
        time.sleep(seconds)

    def __selectTree(self, path, t=1.5):
        log.info('选择左边树路径{}...'.format(path))
        if not self.tree.IsSelected(path):
            self.tree.Select(path)
            time.sleep(t)
        hwnd = find_windows(top_level_only=False, class_name='#32770', parent=self.__dialog_hwnd)[0]
        self.dialog = self.__app.window(handle=hwnd)

    def get_ipo_quota(self):
        path = '\\新股申购\\查询可申购额度'
        response_meta = {
            'wrapper_names': ['market', 'shareholder_account', 'purchase_quota'],
            'columns_index': [1, 2, 3],
            'formats': [format_market, str, int]
        }
        response = self.__getGridData(path=path, response_meta=response_meta)
        return response

    def __buy(self, code, quantity, price=None):
        """买函数
        :param code: 代码， 字符串
        :param quantity: 数量， 字符串
        :param price: 价格

        """
        self.__selectTree('\\买入[F1]')
        self.dialog.Edit1.SetFocus()
        self.wait(0.2)
        self.dialog.Edit1.SetEditText(code)
        self.wait(2)
        if price:
            self.dialog.Edit2.SetFocus()
            self.dialog.Edit2.SetEditText(price)
            self.wait(0.2)
        if quantity != '0':
            self.dialog.Edit3.SetFocus()
            self.dialog.Edit3.SetEditText(quantity)
            self.wait(0.2)
            self.dialog.Button1.Click()
        self.wait(0.2)

    def __sell(self, code, quantity, price=None):
        """
        卖函数
        :param code: 股票代码， 字符串
        :param quantity: 数量， 字符串
        """
        self.__selectTree('\\卖出[F2]')
        self.dialog.Edit1.SetEditText(code)
        time.sleep(0.2)
        if price:
            self.dialog.Edit2.SetEditText(price)
            time.sleep(0.2)
        if quantity != '0':
            self.dialog.Edit3.SetEditText(quantity)
            time.sleep(0.2)
        self.dialog.Button1.Click()
        time.sleep(0.2)

    def __closePopupWindow(self):
        """
        关闭一个弹窗。
        :return: 如果有弹出式对话框，返回True，否则返回False
        """
        popup_hwnd = self.__main_window.PopupWindow()
        if popup_hwnd:
            popup_window = self.__app.window_(handle=popup_hwnd)
            popup_window.SetFocus()
            print(popup_window.Static3.Texts(), popup_window.Static2.Texts())
            popup_window.Button.Click()
            return True
        return False

    def __closePopupWindows(self):
        """
        关闭多个弹出窗口
        :return:
        """
        while self.__closePopupWindow():
            time.sleep(0.5)

    def __getBalance(self):
        """
        获取可用资金
        "balance": {
            "money_type": "币种",
            "current_balance": "可取金额",
            "market_value": "证券市值",
            "asset_balance": "总资产",
            "enable_balance": "可用金额"
        }
        """
        log.info('获取资金股票信息...')
        path = "\\查询[F4]\\资金股票"
        self.__selectTree(path)
        return dict(money_type='RMB',
                    current_balance=float(self.dialog.Static10.Texts()[0]),
                    market_value=float(self.dialog.Static11.Texts()[0]),
                    asset_balance=float(self.dialog.Static12.Texts()[0]),
                    enable_balance=float(self.dialog.Static6.Texts()[0]))

    @staticmethod
    def __cleanClipboardData(data, response_meta):
        """
        清洗剪贴板数据
        :param data: 待清洗数据
        :param response_meta: 清洗格式
                {
                    'wrapper_names': ['stock_code', 'stock_name', 'price', 'max_limit', 'min_limit'],
                    'columns_index': [2, 3, 5, 6, 7],
                    'formats': [str, str, float, int, int]
                }
        :return: list 清洗后的数据
        """
        rows = data.split('\t\r\n')[1:]
        format_info = response_meta.get('formats')
        columns_index = response_meta.get('columns_index')
        result_rows = []
        for row in rows:
            columns = row.split('\t')
            formatted_row = defaultdict()
            for i in range(len(columns_index)):
                value = format_info[i](columns[columns_index[i] - 1])
                name = response_meta.get('wrapper_names')[i]
                formatted_row.setdefault(name, value)
            result_rows.append(formatted_row)
        return result_rows

    def __getCleanedData(self, response_meta):
        """
        读取ListView中的信息
        :return: 清洗后的数据
        """
        self.dialog.CVirtualGridCtrl.TypeKeys('^C')
        data = pywinauto.clipboard.GetData()
        return self.__cleanClipboardData(data, response_meta)

    def __selectTabBarByCoords(self, coords=None):
        """
        选择tab窗口信息
        :param coords: 标签页的相对坐标
        :return:
        """
        self.dialog.CCustomTabCtrl.ClickInput(coords=coords)
        time.sleep(0.5)

    def __selectTabBarByHotKey(self, hotKey):
        self.dialog.CCustomTabCtrl.TypeKeys(hotKey)
        time.sleep(.5)

    def __getGridData(self, path=None, hotKey=None, coords=None, response_meta=None):
        """
        获取CVirtualGridCtrl控件中的数据并根据response_meta信息格式化
        hotkey 与 coords 二选一
        :param path: TreeView path
        :param hotKey:Grid 选择快捷键
        :param coords:相对坐标
        :param response_meta:返回数据的格式化信息
        :return 格式化后的数据
        """
        self.refresh()
        if path:
            self.__selectTree(path)
        if hotKey:
            self.__selectTabBarByHotKey(hotKey=hotKey)
        elif coords:
            self.__selectTabBarByCoords(coords=coords)
        return self.__getCleanedData(response_meta)

    def order(self, direction, code, quantity, price=None):
        """
        下单函数
        :param direction: 买卖方向， 字符串
        :param code: 股票代码， 字符串
        :param quantity: 买卖数量， 字符串
        :param price: 买卖价格，如果price=None市价委托
        :return (boolean,message)
        """
        if direction == 'B':
            self.__buy(code, quantity, price)
        if direction == 'S':
            self.__sell(code, quantity, price)
        self.__closePopupWindows()

    def refresh(self, t=0.5):
        """
        点击刷新按钮
        :param t:刷新后的等待时间
        """
        self.toolbar.button(6).click()
        time.sleep(t)

    def getPosition(self):
        """
        获取持仓
        "positions": {
            "stock_code": "证券代码",
            "stock_name": "证券名称",
            "current_amount": "当前数量",
            "enable_amount": "可卖数量",
            "cost_price": "摊薄成本价",
            "last_price": "最新价",
            'income_ratio':"盈亏比率",
            "income_balance": "摊薄浮动盈亏",
            "market_value": "证券市值"
        }
        :return:
        """
        path = '\\查询[F4]\\资金股票'
        position_meta = {
            'wrapper_names': ['stock_code', 'stock_name',
                              'current_amount', 'enable_amount',
                              'cost_price', 'last_price', 'income_ratio', 'income_balance', 'market_value'],
            'columns_index': [1, 2, 3, 4, 5, 6, 7, 8, 9],
            'formats': [str, str, int, int, float, float, float, float, float]
        }
        return self.__getGridData(path=path, response_meta=position_meta)

    def getEntrust(self):
        """
        获取委托列表
        "entrust": {
            "entrust_no": "委托编号",
            "report_date":"委托日期"
            "report_time": "委托时间",
            "stock_code": "证券代码",
            "stock_name": "证券名称",
            "entrust_amount": "委托数量",
            "business_amount": "成交数量",
            "entrust_price": "委托价格",
            "business_price": "成交价格",
            "entrust_bs": "买卖方向",
            "entrust_status": "委托状态",
            "remark":"备注"
        }
        datetime.datetime.strptime(string,'%Y-%m-%d %H:%M:%S')
        :return:
        """
        path = '\\撤单[F3]'
        entrust_meta = {
            'wrapper_names': ['entrust_no', 'report_date', 'report_time', 'stock_code', 'stock_name',
                              'entrust_amount', 'business_amount',
                              'entrust_price', 'business_price', 'entrust_bs', 'remark'],
            'columns_index': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            'formats': [str, format_date, format_time, str, str, int, int, float, float, format_direction, str]
        }
        entrusts = self.__getGridData(path=path, response_meta=entrust_meta)
        return entrusts

    def cancel_order(self, order_id):
        """
            撤单
        :param order_id: 订单id
        :return:
        """
        orders = self.getEntrust()
        row_pos = []
        for i in range(len(orders)):
            if orders[i].get('entrust_no') == order_id:
                row_pos.append(i + 1)
        for row in row_pos:
            y = get_pos(row)
            print(y)
            self.dialog.CVirtualGridCtrl.ClickInput(coords=(7, get_pos(row)))
            self.wait(.5)
            self.dialog.Button2.Click()
            self.__closePopupWindows()

    def ipo(self):
        log.info('开始新股申购...')
        path = "\\新股申购\\新股申购"
        new_stock_meta = {
            'wrapper_names': ['market', 'stock_code', 'stock_name', 'price', 'max_limit'],
            'columns_index': [1, 2, 3, 4, 5],
            'formats': [format_market, str, str, float, int]
        }
        stocks = self.__getGridData(path=path, coords=(100, 9), response_meta=new_stock_meta)
        for stock in stocks:
            market_ = stock.get('market')
            for m in self.account.get('ipo_quota'):
                if m.get('market') == market_ and m.get('purchase_quota') > 0:
                    purchase_quota = m.get('purchase_quota')
                    self.dialog.Edit1.SetEditText(stock.get('stock_code'))
                    self.wait(.5)
                    if purchase_quota > stock.get('max_limit'):
                        self.dialog.Edit3.SetEditText(stock.get('max_limit'))
                    else:
                        self.dialog.Edit3.SetEditText(purchase_quota)
                    self.dialog['申购[B]'].Click()
                    self.__closePopupWindows()
                    self.wait(3)

    def exit(self):
        self.__app.kill()
        log.info('程序已终止!')


class TreadError(Exception):
    """
        交易错误类
    """
    def __init__(self, code, message):
        self.code = code
        self.message = message