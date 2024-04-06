import datetime as dt


def datetimeToTimestamp(time: dt.datetime) -> str:
    return time.strftime('%Y-%m-%d %H:%M:%S.%f')


def timestampToDatetime(time: str) -> dt.datetime:
    return dt.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f') if '.' in time else dt.datetime.strptime(time, '%Y-%m-%d %H:%M:%S')


def datetimeToSeconds(time: dt.datetime) -> float:
    return time.replace(tzinfo=dt.timezone.utc).timestamp()


def secondsToDatetime(time: float) -> dt.datetime:
    return dt.datetime.fromtimestamp(time, tz=dt.timezone.utc)


def timestampToSeconds(time: str) -> float:
    return datetimeToSeconds(timestampToDatetime(time))


def secondsToTimestamp(time: float) -> str:
    return datetimeToTimestamp(secondsToDatetime(time))


def earliestDate() -> dt.datetime:
    return dt.datetime(1000, 1, 1)


def now() -> dt.datetime:
    return dt.datetime.utcnow()


def timeIt(fn) -> float:
    import time
    then = time.time()
    fn()
    now = time.time()
    return now - then


def isValidTimestamp(time: str) -> bool:
    def tryTimeConvert():
        try:
            timestampToDatetime(time)
            return True
        except Exception as _:
            return False

    return isinstance(time, str) and 18 < len(time) < 27 and tryTimeConvert()
