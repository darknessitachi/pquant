# coding: utf-8

import quotation

from .basic_quotation_engine import BasicQuotationEngine


class DefaultQuotationEngine(BasicQuotationEngine):
    """新浪行情推送引擎"""
    EventType = 'quotation'

    def init(self):
        self.q = quotation.use('sina')

    def fetch_quotation(self):
        return self.q.refresh()
