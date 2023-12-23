import time
# import thread
from satorilib.asynchronous import thread
at = thread.AsyncThread()


class Someting:
    def __init__(self, name):
        self.name = name

    def p(self, x):
        if self.name == 'a':
            print(x)
        if self.name == 'cancel':
            print(x)
            print('canceling')
            at.cancelTask(self.future)

    def supervize(self):
        self.future = at.repeatRun('hello world', task=self.p, interval=1)

    def cancel(self):
        at.cancelTask(self.future)


a = Someting('b')
a.supervize()
time.sleep(10)
a.name = 'a'
time.sleep(10)
a.name = 'cancel'
# a.cancel()
time.sleep(10)
exit()
