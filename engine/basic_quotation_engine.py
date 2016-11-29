# coding: utf-8
import time
from threading import Thread
from abc import abstractclassmethod
from engine.event_engine import Event


class BasicQuotationEngine:
    """行情推送引擎基类"""
    EventType = 'base'
    PushInterval = 1

    def __init__(self, event_engine, clock_engine):
        self.event_engine = event_engine
        self.clock_engine = clock_engine
        self.is_active = True
        self.quotation_thread = Thread(target=self.push_quotation, name="QuotationEngine.%s" % self.EventType)
        self.quotation_thread.setDaemon(False)
        self.init()

    def start(self):
        self.quotation_thread.start()

    def stop(self):
        self.is_active = False

    def push_quotation(self):
        while self.is_active:
            try:
                response_data = self.fetch_quotation()
            except:
                self.wait()
                continue
            event = Event(event_type=self.EventType, data=response_data)
            self.event_engine.put(event)
            self.wait()


    @abstractclassmethod
    def fetch_quotation(self):
        # return your quotation
        return None

    @abstractclassmethod
    def init(self):
        # do something init
        pass

    def wait(self):
        # for receive quit signal
        for _ in range(int(self.PushInterval) + 1):
            time.sleep(1)
