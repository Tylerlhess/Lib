import datetime as dt


def datetimeToString(time: dt.datetime) -> str:
    return time.strftime('%Y-%m-%d %H:%M:%S.%f')

def datetimeFromString(time: str)-> dt.datetime:
    return dt.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')

def now() -> dt.datetime:
    return dt.datetime.utcnow()

def timeIt(fn) -> float:
    import time
    then = time.time()
    fn()
    now = time.time()
    return now - then
