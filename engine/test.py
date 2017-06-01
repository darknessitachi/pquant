import unittest
from .event_engine import EventEngine


class EventEngineTest(unittest.TestCase):
    def test_start(self):
        eventEngine = EventEngine()
        eventEngine.start()

