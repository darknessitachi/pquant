from engine.clock_engine import ClockEngine
from engine.event_engine import EventEngine
from engine.flashback_engine import FlashbackEngine
from main_engine import MainEngine

def GridTrade(beginDate, endDate, code):

    main = MainEngine(quotation_engines=FlashbackEngine)
    main.load_strategy()
    flashback = main.get_quotation(FlashbackEngine.EventType)
    flashback.create_thread(stock=code, begin=beginDate, end=endDate)
    main.start()


GridTrade('20140801', '20161130', '150176')
