'''
Here's plan for the server - python server, you checkin with it,
it returns a key you use to make a websocket connection with the pubsub server.
'''
import json
import requests
from satorilib import logging
from satorilib.api.wallet import Wallet


class SatoriServerClient(object):
    def __init__(
            self, wallet: 'Wallet', url: str = None,
            *args, **kwargs):
        super(SatoriServerClient, self).__init__(*args, **kwargs)
        self.wallet = wallet
        self.url = url or 'https://satorinet.io'

    def registerWallet(self):
        r = requests.post(
            self.url + '/register/wallet',
            headers=self.wallet.authPayload(asDict=True),
            json=self.wallet.registerPayload())
        r.raise_for_status()
        return r

    def registerStream(self, stream: dict, payload: str = None):
        ''' publish stream {'source': 'test', 'name': 'stream1', 'target': 'target'}'''
        r = requests.post(
            self.url + '/register/stream',
            headers=self.wallet.authPayload(asDict=True),
            json=payload or json.dumps(stream))
        r.raise_for_status()
        return r

    def registerSubscription(self, subscription: dict, payload: str = None):
        ''' subscribe to stream '''
        logging.debug('\nregisterSubscription',
                      payload or json.dumps(subscription))
        r = requests.post(
            self.url + '/register/subscription',
            headers=self.wallet.authPayload(asDict=True),
            json=payload or json.dumps(subscription))
        r.raise_for_status()
        return r

    def registerPin(self, pin: dict, payload: str = None):
        ''' 
        report a pin to the server.
        example: {
            'author': {'pubkey': '22a85fb71485c6d7c62a3784c5549bd3849d0afa3ee44ce3f9ea5541e4c56402d8'}, 
            'stream': {'source': 'satori', 'pubkey': '22a85fb71485c6d7c62a3784c5549bd3849d0afa3ee44ce3f9ea5541e4c56402d8', 'stream': 'stream1', 'target': 'target', 'cadence': None, 'offset': None, 'datatype': None, 'url': None, 'description': 'raw data'},, 
            'ipns': 'ipns', 
            'ipfs': 'ipfs', 
            'disk': 1, 
            'count': 27},
        '''
        r = requests.post(
            self.url + '/register/pin',
            headers=self.wallet.authPayload(asDict=True),
            json=payload or json.dumps(pin))
        logging.debug('lib registerPin:', payload or json.dumps(pin), r)
        r.raise_for_status()
        return r

    def requestPrimary(self):
        ''' subscribe to primary data stream and and publish prediction '''
        r = requests.get(
            self.url + '/request/primary',
            headers=self.wallet.authPayload(asDict=True))
        r.raise_for_status()
        return r

    def getStreams(self, stream: dict, payload: str = None):
        ''' subscribe to primary data stream and and publish prediction '''
        r = requests.post(
            self.url + '/get/streams',
            headers=self.wallet.authPayload(asDict=True),
            json=payload or json.dumps(stream))
        r.raise_for_status()
        return r

    def myStreams(self):
        ''' subscribe to primary data stream and and publish prediction '''
        r = requests.post(
            self.url + '/my/streams',
            headers=self.wallet.authPayload(asDict=True),
            json='{}')
        r.raise_for_status()
        return r

    def removeStream(self, stream: dict = None, payload: str = None):
        ''' removes a stream from the server '''
        if payload is None and stream is None:
            raise ValueError('stream or payload must be provided')
        r = requests.post(
            self.url + '/remove/stream',
            headers=self.wallet.authPayload(asDict=True),
            json=payload or json.dumps(stream or {}))
        r.raise_for_status()
        return r

    def checkin(self):
        r = requests.post(
            self.url + '/checkin',
            headers=self.wallet.authPayload(asDict=True),
            json=self.wallet.registerPayload())
        r.raise_for_status()
        j = r.json()
        # use subscriptions to initialize engine
        # logging.debug('publications.key', j.get('publications.key'))
        # logging.debug('subscriptions.key', j.get('subscriptions.key'))
        # use subscriptions to initialize engine
        logging.debug('subscriptions', j.get('subscriptions'))
        # use publications to initialize engine
        logging.debug('publications', j.get('publications'))
        # use pins to initialize engine and update any missing data
        logging.debug('pins', j.get('pins'))
        # use server version to use the correct api
        logging.debug('server version', j.get('versions', {}).get('server'))
        # use client version to know when to update the client
        logging.debug('client version', j.get('versions', {}).get('client'))
        # from satoriserver.utils import Crypt
        # logging.debug('key', Crypt().decrypt(
        #    toDecrypt=j.get('key'),
        #    key='thiskeyisfromenv',
        #    clean=True))
        return r.json()
