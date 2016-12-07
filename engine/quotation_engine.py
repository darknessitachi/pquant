# coding: utf-8
import time
import logging
from threading import Thread
from engine.event_engine import Event
import quotation


class QuotationEngine:
    """行情推送引擎基类"""
    EventType = 'quotation'
    PushInterval = 60

    def __init__(self, event_engine, clock_engine, source=None):
        self.log = logging.getLogger(self.EventType)
        self.event_engine = event_engine
        self.clock_engine = clock_engine
        self.is_active = True
        self.quotation = quotation.use('lf')
        self.quotation_thread = Thread(target=self.push_quotation, name="QuotationEngine.%s" % self.EventType)
        self.quotation_thread.setDaemon(False)
        self.init()

    def subscribe(self, codes):
        self.quotation.subscribe(codes)

    def unsubscribe(self, codes):
        self.quotation.unsubscribe(codes)

    def start(self):
        self.quotation_thread.start()

    def stop(self):
        self.is_active = False

    def push_quotation(self):
        while self.is_active:
            try:
                response_data = self.fetch_quotation()
            except Exception as e:
                self.log.error(e)
                self.wait()
                continue
            event = Event(event_type=self.EventType, data=response_data)
            self.event_engine.put(event)
            self.wait()

    def fetch_quotation(self):
        # return your quotation
        return self.quotation.refresh()

    def init(self):
        pass

    def wait(self):
        # for receive quit signal
        for _ in range(int(self.PushInterval) + 1):
            time.sleep(1)
