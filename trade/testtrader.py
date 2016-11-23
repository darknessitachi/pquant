from trade.yjbtrader import YJBTrader
if __name__ == '__main__':
    user = YJBTrader()
    user.prepare('yjb.json')
    print(user.get_balance())