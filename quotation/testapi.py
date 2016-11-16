import quotation

if __name__ == '__main__':
    sina = quotation.use()
    sina.subscribe('600887')
    sina.subscribe('601717')
    print(sina.subscribed)
    print(sina.getQuotationData())

    lf = quotation.use('lf')
    lf.subscribe('600887')
    lf.subscribe('601717')
    print(lf.subscribed)
    print(lf.getQuotationData())