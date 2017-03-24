from engine.clock_engine import ClockEngine
from engine.event_engine import EventEngine
from engine.quotation_engine import QuotationEngine
from main_engine import MainEngine
import time

event = EventEngine()
clock = ClockEngine(event)
main = MainEngine(quotation_engines=QuotationEngine)
main.load_strategy()
main.start()

# quotation = QuotationEngine(source='lf', event_engine=event, clock_engine=clock)
# quotation.subscribe(['600887', '600315', '601717'])
# quotation.start()
# event.start()
# time.sleep(100)
# quotation.stop()
# event.stop()
