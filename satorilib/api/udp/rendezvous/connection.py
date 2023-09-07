''' our (persistent) connection to the rendezvous server '''

from satorilib.api.udp.rendezvous.base import UDPRendezvousConnectionBase


class UDPRendezvousConnection(UDPRendezvousConnectionBase):
    ''' conn for server, using signature and key for identity  '''

    def __init__(self, signature: str, key: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signature = signature
        self.key = key

    def checkin(self):
        # self.send(f'CHECKIN|{self.msgId}|{self.signature}|{self.key}')
        self.send(cmd='CHECKIN', msg=[self.signature, self.key])
