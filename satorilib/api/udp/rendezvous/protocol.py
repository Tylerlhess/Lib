"""
this holds the protocol for node-rendezvous communication over udp.

client to server: 'COMMAND|msgId(|data)'
server to client: always responds with 'msgId(|response)'

all conversation is done over UDP, and in chunks of 1028 bytes or less.
the available commands are:
    CHECKIN - the client is checking in with the server
    CHECKIN|msgId|signature|idKey
    
    PORTS - the client is telling the server, not to assign it these ports
    PORTS|msgId|portsTaken
    
    SUBSCRIBE - the client is subscribing to one or more topics
    SUBSCRIBE|msgId|signature|key
"""

import json
from satorilib import logging
from satorilib.concepts import TwoWayDictionary


class UDPRendezvousProtocol():

    @staticmethod
    def toBytes(msg: str) -> bytes:
        return msg.encode()

    @staticmethod
    def fromBytes(msg: bytes) -> str:
        return msg.decode()

    @staticmethod
    def checkinPrefix() -> bytes:
        return b'CHECKIN'

    @staticmethod
    def portsPrefix() -> bytes:
        return b'PORTS'

    @staticmethod
    def subscribePrefix() -> bytes:
        return b'SUBSCRIBE'

    @staticmethod
    def beatPrefix() -> bytes:
        return b'BEAT'

    @staticmethod
    def portsTaken(ports: list[str]) -> bytes:
        if isinstance(ports, list):
            ports = ','.join(ports)
        if isinstance(ports, str):
            ports = ports.encode()
        return UDPRendezvousProtocol.portsPrefix() + b'|' + ports

    @staticmethod
    def subscribe(signature: str, key: str) -> bytes:
        if isinstance(signature, str):
            signature = signature.encode()
        if isinstance(key, str):
            key = key.encode()
        return UDPRendezvousProtocol.subscribePrefix() + b'|' + signature + b'|' + key


class UDPRendezvousMessage():

    @staticmethod
    def fromBytes(data: bytes, ip: str, port: int, sent: bool = False):
        parts = []
        command = None
        msgId = None
        message = None
        try:
            parts = data.split(b'|', 2)
            command = parts[0]
            msgId = parts[1]
        except Exception as e:
            logging.error('fromBytes error: ', e)
        if len(parts) > 2:
            message = parts[2]
        return UDPRendezvousMessage(sent, ip, port, command, msgId, message)

    @staticmethod
    def asStr(msg: bytes) -> str:
        if isinstance(msg, bytes):
            return msg.decode()
        if isinstance(msg, str):
            return msg
        # what else could it be?
        return str(msg)

    @staticmethod
    def isValidCommand(cmd: bytes) -> bool:
        cmd = cmd.encode() if isinstance(cmd, str) else cmd
        return cmd in [
            UDPRendezvousProtocol.checkinPrefix(),
            UDPRendezvousProtocol.portsPrefix(),
            UDPRendezvousProtocol.subscribePrefix(),
            UDPRendezvousProtocol.beatPrefix()]

    def __init__(
        self,
        sent: bool,
        ip: str,
        port: int,
        command: bytes,
        msgId: bytes,
        message: bytes
    ):
        self.malformed = False
        if command is None or msgId is None:
            self.malformed = True
        self.ip = ip
        self.port = port
        self.sent = sent
        self.commandBytes = command
        self.msgIdBytes = msgId
        self.messageBytes = message
        # broken out if present in message
        self.portsTaken = None
        self.setPortsTaken()
        self.signatureBytes = None
        self.keyBytes = None
        self.setSignatureAndKey()
        self.command = UDPRendezvousMessage.asStr(self.commandBytes)
        self.msgId = UDPRendezvousMessage.asStr(self.msgIdBytes)
        self.message = UDPRendezvousMessage.asStr(self.messageBytes)
        self.signature = UDPRendezvousMessage.asStr(self.signatureBytes)
        self.key = UDPRendezvousMessage.asStr(self.keyBytes)

    @property
    def address(self):
        return (self.ip, self.port)

    def setSignatureAndKey(self):
        if self.isCheckIn() or self.isSubscribe():
            if self.messageBytes is not None:
                parts = self.messageBytes.split(b'|', 1)
                if len(parts) == 2:
                    self.signatureBytes = parts[0]
                    self.keyBytes = parts[1]
                else:
                    self.malformed = True

    def setPortsTaken(self):
        if self.isPortsTaken():
            try:
                self.portsTaken = TwoWayDictionary.fromDict(
                    json.loads(self.message))
            except Exception:
                self.portsTaken = TwoWayDictionary()
                self.malformed = True

    def isCheckIn(self):
        return self.commandBytes == UDPRendezvousProtocol.checkinPrefix()

    def isPortsTaken(self):
        return self.commandBytes == UDPRendezvousProtocol.portsPrefix()

    def isSubscribe(self):
        return self.commandBytes == UDPRendezvousProtocol.subscribePrefix()

    def isBeat(self):
        return self.commandBytes == UDPRendezvousProtocol.beatPrefix()
