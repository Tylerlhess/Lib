import datetime as dt


def datetimeToString(time: dt.datetime):
    return time.strftime('%Y-%m-%d %H:%M:%S.%f')


def datetimeFromString(time: str):
    return dt.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')


def now():
    return dt.datetime.utcnow()
