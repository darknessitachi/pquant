import time
from threading import Thread

class CountdownTask:
    def __init__(self):
        self._running = True

    def terminate(self):
        self._running = False

    def run(self, n):
        while self._running and n > 0:
            print('T-minus', n)
            n -= 1
            time.sleep(10)

c = CountdownTask()
t = Thread(target=c.run,args=(10,),daemon=True)
t.start()
print(t.is_alive())
time.sleep(20)
c.terminate()
t.join() # 将线程加入到当前线程,并等待终止
print(t.is_alive())