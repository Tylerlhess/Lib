''' our (persistent) connection to the rendezvous server '''

import time
import socket
import threading
from satorilib import logging
from satorilib.api.udp.rendezvous.protocol import UDPRendezvousMessage, UDPRendezvousProtocol


class UDPRendezvousConnectionBase:
    ''' raw connection functionality '''

    def __init__(self, messageCallback=None):
        # could allow us to keep track of which messages were responded to
        self.msgId = 0
        self.sock = None
        self.rendezvousServer = ('161.35.238.159', 49152)
        self.rendezvousPort = 49152
        self.messageCallback = messageCallback or self.display
        self.port = None
        self.inbox = {}
        self.outbox = {}
        self.lastBeat = 0.0

    def display(self, msg, addr):
        logging.info(f'from: {addr}, {msg}', print=True)

    def show(self):
        logging.info(f'my port: {self.port}', print=True)

    def establish(self):
        ''' connect to rendezvous '''
        def listen():
            '''
            listen for messages from rendezvous server
            saves lastBeat time or saves message to inbox
            message from server is of this format: f'{msgId}|{msg}'
            calls the callback function with the message and address            
            '''
            while True:
                data, addr = self.sock.recvfrom(1024)
                print('RECEIVED DATA')
                print(data, addr)
                try:
                    msgs = data.split(b'|')
                    if msgs[1] == b'beat':
                        self.lastBeat = time.time()
                    else:
                        self.inbox[int(msgs[0])] = data
                except Exception as e:
                    logging.warning('error pushing message to inbox', e, data)
                self.messageCallback(data, addr)

        def heartbeat():
            '''
            sends heartbeat to rendezvous server 3 times per 5 minutes,
            unless received a heartbeat from server, then skip 1.
            '''
            beats = 0
            skip = True
            while True:
                print(f'heartbeat {beats}, {skip}, {self.lastBeat}')
                if not skip:
                    beats -= 1
                    self.sock.sendto(
                        UDPRendezvousProtocol.beatPrefix() +
                        f'|{beats}'.encode(),
                        self.rendezvousServer)
                skip = False
                time.sleep(99)
                if self.lastBeat > time.time() - 99:
                    skip = True

        logging.info('connecting to rendezvous server', print=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', self.rendezvousPort))
        self.listener = threading.Thread(target=listen, daemon=True)
        self.listener.start()
        # self.sock.sendto(b'0', self.rendezvousServer)
        logging.info('ready to exchange messages\n', print=True)
        self.heart = threading.Thread(target=heartbeat, daemon=True)
        self.heart.start()
        self.send(UDPRendezvousProtocol.checkinPrefix())

    def send(self, cmd: str, msgs: list[str] = None):
        ''' format and send a message to rendezvous server '''
        if not UDPRendezvousMessage.isValidCommand(cmd):
            logging.error('command not valid', cmd, print=True)
        if isinstance(cmd, bytes):
            cmd = cmd.decode()
        msgs = [
            msg.decode() if isinstance(msg, bytes) else msg
            for msg in (msgs or [])]
        self.push(
            '|'.join([
                x for x in [cmd, str(self.msgId), *msgs]
                if x is not None and len(x) > 0]).encode())
        self.msgId += 1

    def push(self, msg: bytes, msgId: int = None):
        ''' push message to rendezvous server '''
        if isinstance(msg, str):
            msgId = msgId or msg.split('|')[1]
            msg = msg.encode()
        else:
            msgId = msgId or msg.split(b'|')[1]
        try:
            self.outbox[int(msgId)] = msg
        except Exception as e:
            logging.warning('error pushing message to outbox', e, msg)
        self.sock.sendto(msg, self.rendezvousServer)
