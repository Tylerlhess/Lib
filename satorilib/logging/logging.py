
import sys
import logging
from typing import Union


def setup(
    level=logging.DEBUG,
    file: Union[str, None] = None,
    format: str = None,
    stdoutAndFile: bool = False,
):
    format = format or '%(asctime)s - %(levelname)s - %(message)s'
    kwargs = {'level': level, 'format': format}
    if file is not None:
        if stdoutAndFile:
            file_handler = logging.FileHandler(file)
            file_handler.setLevel(level)
            # file_handler.setFormatter(format)
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setLevel(level)
            # stream_handler.setFormatter(format)
            kwargs = {'handlers': [file_handler, stream_handler], **kwargs}
        else:
            kwargs = {'filename': file, **kwargs}
    else:
        kwargs = {'stream': sys.stdout, **kwargs}
    logging.basicConfig(**kwargs)

    # Add excepthook to capture unhandled exceptions
    def log_unhandled_exception(exc_type, exc_value, exc_traceback):
        logging.critical("Unhandled exception", exc_info=(
            exc_type, exc_value, exc_traceback))
    sys.excepthook = log_unhandled_exception


def _log(fn, msg, *args, **kwargs):
    if kwargs.get('print'):
        print(msg)
    return fn(msg=msg, *args, **kwargs)


def _getMsg(msgs):
    return ' '.join([str(m) for m in msgs])


def _getArgsKwargs(kwargs):
    args = []
    if 'args' in kwargs.keys():
        args = kwargs.pop('args')
    return args, kwargs


def debug(*msgs, **kwargs):
    args, kwargs = _getArgsKwargs(kwargs)
    return _log(logging.debug, _getMsg(msgs), *args, **kwargs)


def info(*msgs, **kwargs):
    args, kwargs = _getArgsKwargs(kwargs)
    return _log(logging.info, _getMsg(msgs), *args, **kwargs)


def warning(*msgs, **kwargs):
    args, kwargs = _getArgsKwargs(kwargs)
    return _log(logging.warning, _getMsg(msgs), *args, **kwargs)


def error(*msgs, **kwargs):
    args, kwargs = _getArgsKwargs(kwargs)
    return _log(logging.error, _getMsg(msgs), *args, **kwargs)


def critical(*msgs, **kwargs):
    args, kwargs = _getArgsKwargs(kwargs)
    return _log(logging.critical, _getMsg(msgs), *args, **kwargs)
