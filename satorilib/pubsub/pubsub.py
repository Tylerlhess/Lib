# this uses the websocket-client library and represents a both the subscriber
# and the publisher connection in one. It runs the subscriber in it's own thread
# which means the only downside it has is that it cannot change the on_message
# handler, called router, until after a message has been received. This is a
# limitation, but not a serious one.

# the default router should accept the message and hold it in memory until the
# ipfs sync process is complete. Once it is complete it should send each message
# in reserve to the system that saves it to disk and routes it to the engine.
# since the engine will not even be started until after the router is complete,
# and all messages saved to the disk, this should be fine.

from typing import Union
import json
import time
import threading
from satorilib import logging


class SatoriPubSubConn(object):
    def __init__(
        self, uid: str, payload: Union[dict, str], url: Union[str, None] = None,
        router: Union['function', None] = None, listening: bool = True,
        then: Union[str, None] = None, command: str = 'key', threaded: bool = True,
        *args, **kwargs
    ):
        super(SatoriPubSubConn, self).__init__(*args, **kwargs)
        self.uid = uid
        self.url = url or 'ws://satorinet.io:3000'
        self.router = router
        self.ws = self.connect()
        self.listening = listening
        self.threaded = threaded
        self.shouldReconnect = True
        if self.threaded:
            self.ear = threading.Thread(target=self.listen, daemon=True)
            self.ear.start()
        self.payload = payload
        self.command = command
        self.start = kwargs.get('start', None)
        if self.start is None:
            self.setStart()
        self.send(self.command + ':' + self.payload)
        if then is not None:
            time.sleep(3)
            self.send(then)

    def setStart(self):
        from satorineuron.init.start import getStart
        self.start = getStart()

    def reestablish(self, err: str = '', payload: str = None):
        # logging.debug('connection error', err)
        time.sleep(3)
        while True:
            try:
                # logging.debug('re-establishing pubsub connection')
                self.restart(payload)
            except Exception as _:
                pass
                # logging.debug('restarting pubsub connection failed', e)
            time.sleep(2)
            if (self.ws.connected):
                break

    def restart(self, payload: str = None):
        self = self.__init__(
            uid=self.uid,
            payload=self.payload,
            url=self.url,
            router=self.router,
            listening=self.listening,
            command=self.command,
            then=payload)

    def listen(self):
        while True:
            try:
                response = self.ws.recv()
                # logging.debug('response', response)
            except Exception as _:
                # except WebSocketConnectionClosedException as e:
                # except ConnectionResetError:
                # logging.debug('pubsub broke:', e)
                break
            try:
                self.router(response)
            except Exception as _:
                pass
                # logging.debug('pubsub broke because of router behavior:', e)
        # logging.debug('restarting')
        if self.shouldReconnect:
            self.restart()
            if self.threaded:
                raise Exception('pubsub restarted, start listening again.')

    def connect(self):
        import websocket
        ws = websocket.WebSocket()
        while not ws.connected:
            try:
                ws.connect(f'{self.url}?uid={self.uid}')
                self.start.connPubsubQueue.put(True)
                return ws
            except Exception as e:
                # except OSError as e:
                # OSError: [Errno 99] Cannot assign requested address
                # pubsub server went down
                self.start.connPubsubQueue.put(False)
                logging.error(
                    e, 'failed to connect to pubsub server, retrying...', print=True)
                time.sleep(30)

    def send(
        self,
        payload: Union[str, None] = None,
        title: Union[str, None] = None,
        topic: Union[str, None] = None,
        data: Union[str, None] = None,
        time: Union[str, None] = None,
        observationHash: Union[str, None] = None,
    ):
        if payload is None and title is None and topic is None and data is None:
            raise ValueError(
                'payload or (title, topic, data) must not be None')
        payload = payload or (
            title + ':' + json.dumps({
                'topic': topic,
                'time': str(time),
                'data': str(data),
                'hash': str(observationHash),
            }))
        # logging.debug('sending:', payload)
        try:
            self.ws.send(payload)
        except Exception as e:
            # BrokenPipeError
            # WebSocketConnectionClosedException
            # WebSocketTimeoutException
            self.reestablish(e, payload)

    def publish(self, topic: str, data: str, time: str, observationHash: str):
        self.send(title='publish', topic=topic, data=data,
                  time=time, observationHash=observationHash)

    def disconnect(self, reconnect: bool = False):
        self.shouldReconnect = reconnect
        self.listening = False
        self.send(title='notify', topic='connection', data='False')
        self.start.connPubsubQueue.put(False)
        self.ws.close()  # server should detect we closed the connection
        assert (self.ws.connected == False)

    def setRouter(self, router: 'function' = None):
        self.router = router

# install latest python3 (>3.7)
# pip3 install websocket-client
# python3 clientws.py
