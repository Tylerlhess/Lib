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
        # logging.debug('\nregisterSubscription',
        #              payload or json.dumps(stream))
        r = requests.post(
            self.url + '/register/stream',
            headers=self.wallet.authPayload(asDict=True),
            json=payload or json.dumps(stream))
        r.raise_for_status()
        return r

    def registerSubscription(self, subscription: dict, payload: str = None):
        ''' subscribe to stream '''
        # logging.debug('\nregisterSubscription',
        #              payload or json.dumps(subscription))
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
        authPayload = self.wallet.authPayload(asDict=True)
        try:
            r = requests.post(
                self.url + '/register/pin',
                headers=authPayload,
                json=payload or json.dumps(pin))
            # logging.debug('lib server registerPin:',
            #              payload or json.dumps(pin), r)
            r.raise_for_status()
        except Exception as e:
            logging.error(
                'lib server registerPin error:\n'
                f'payload or json.dumps(pin): {payload or json.dumps(pin)}\n'
                f'self.url + /register/pin: {self.url + "/register/pin/"}\n'
                f'authPayload: {authPayload}\n', e)
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

    def checkin(self) -> dict:
        # r = requests.post(
        #    self.url + '/checkin',
        #    headers=self.wallet.authPayload(asDict=True),
        #    json=self.wallet.registerPayload())
        # if r.text.startswith('unable to verify recent timestamp.'):
        #    logging.error(
        #        'Please sync your system clock. '
        #        'Attempting again with server time.',
        #        r.text, color='red')
        # poor man's solution for getting a prompt from the server:
        # use server's time, that way it doesn't have to remember which
        # prompt it gave to who and we can continue to use the time
        # verification system we have.
        # how it's the default way:
        r = requests.post(
            self.url + '/checkin',
            headers=self.wallet.authPayload(asDict=True),
            json=self.wallet.registerPayload(
                challenge=requests.get(self.url + '/time').text))
        r.raise_for_status()
        # use subscriptions to initialize engine
        # # logging.debug('publications.key', j.get('publications.key'))
        # # logging.debug('subscriptions.key', j.get('subscriptions.key'))
        # use subscriptions to initialize engine
        # logging.debug('subscriptions', j.get('subscriptions'))
        # use publications to initialize engine
        # logging.debug('publications', j.get('publications'))
        # use pins to initialize engine and update any missing data
        # logging.debug('pins', j.get('pins'))
        # use server version to use the correct api
        # logging.debug('server version', j.get('versions', {}).get('server'))
        # use client version to know when to update the client
        # logging.debug('client version', j.get('versions', {}).get('client'))
        # from satoricentral.utils import Crypt
        # # logging.debug('key', Crypt().decrypt(
        #    toDecrypt=j.get('key'),
        #    key='thiskeyisfromenv',
        #    clean=True))
        return r.json()
