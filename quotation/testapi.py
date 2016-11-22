import quotation

if __name__ == '__main__':
    from pprint import pprint
    sina = quotation.use()
    sina.subscribe('600887')
    sina.subscribe('601717')
    pprint(sina.subscribed)
    pprint(sina.refresh())

    lf = quotation.use('lf')
    lf.subscribe('600887')
    lf.subscribe('601717')
    pprint(lf.subscribed)
    pprint(lf.refresh())