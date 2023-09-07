''' this script describes a single connection between two nodes over UDP '''

import socket
import threading
from satorilib import logging


class UDPConnection:
    ''' raw connection functionality '''

    def __init__(self, port: int, peerPort: int, peerIp: str, messageCallback=None):
        self.port = port
        self.peerIp = peerIp
        self.peerPort = peerPort
        self.sock = None
        self.messageCallback = messageCallback or self.display

    def display(self, msg, addr):
        logging.info(f'from: {addr}, {msg}')

    def show(self):
        logging.info(f'peer ip:  {self.peerIp}')
        logging.info(f'peer port: {self.peerPort}')
        logging.info(f'my port: {self.port}')

    def establish(self):
        def listen():
            while True:
                data, addr = sock.recvfrom(1024)
                self.messageCallback(data, addr)

        logging.info('establishing connection')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', self.port))
        sock.sendto(b'0', (self.peerIp, self.peerPort))
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', self.peerPort))
        listener = threading.Thread(target=listen, daemon=True)
        listener.start()
        logging.info('ready to exchange messages\n')

    def send(self, msg: bytes):
        ''' assumes msg is bytes'''
        if isinstance(msg, str):
            msg = msg.encode()
        self.sock.sendto(msg, (self.peerIp, self.port))
