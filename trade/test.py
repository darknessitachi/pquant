import Pyro4.util
import sys
import time
import math

sys.excepthook = Pyro4.util.excepthook
user = Pyro4.Proxy("PYRONAME:trade.api@172.20.0.101:9090")
user.logon()
begin_time =  time.time()
for i in range(100):
    user.getPosition()
end_time  = time.time()
print("总耗时{}s".format(math.ceil((end_time - begin_time))))
user.logoff()