from quotation.historyquotation import HistoryQuotation
from engine.event_engine import Event, EventEngine
from engine.clock_engine import ClockEngine
from threading import Thread
import logging
import time


class FlashbackEngine:
    EventType = 'flashback'
    PushInterval = 1

    def __init__(self, event_engine: EventEngine,clock_engine:ClockEngine):
        self.log = logging.getLogger(self.EventType)
        self.event_engine = event_engine
        self.history_quotation = HistoryQuotation()
        self.is_active = True
        self.quotation_thread = None

    def create_thread(self, stock, begin, end):
        self.quotation_thread = Thread(target=self.push_quotation,
                                       name='FlashbackEngine.{}'.format(stock),
                                       args=(stock, begin, end))

    def start(self):
        self.quotation_thread.start()

    def stop(self):
        self.is_active = False

    def push_quotation(self, stock, begin, end):
        while self.is_active:
            try:
                data = self.history_quotation.get_data(stock, begin, end)
                for i in data:
                    event = Event(event_type=self.EventType, data=i)
                    self.event_engine.put(event)
                    self.wait()
            except Exception as e:
                self.log.error(e)
                self.wait()
                continue
            self.wait()
    def wait(self):
        for _ in range(int(self.PushInterval) + 1):
            time.sleep(1)
