import os
import json
import mnemonic
from random import randrange
from satoriwallet.lib import connection
from satorilib import logging
from satorilib.api import system
from satorilib.api.disk.wallet import WalletApi


class Wallet():

    def __init__(self, walletPath, temporary=False):
        self._entropy = None
        self._privateKeyObj = None
        self._addressObj = None
        self.publicKey = None
        self.privateKey = None
        self.words = None
        self.address = None
        self.scripthash = None
        self.stats = None
        self.banner = None
        self.base = None
        self.balance = None
        self.transactionHistory = None
        self.transactions = []  # TransactionStruct
        self.temporary = temporary
        self.walletPath = walletPath

    def __call__(self):
        x = 0
        while x < 5:
            try:
                self.init()
                break
            except TimeoutError:
                logging.error('init wallet connection attempts', x)
                x += 1
        return self

    def __repr__(self):
        return (
            'Wallet('
            f'\n\tpublicKey: {self.publicKey},'
            f'\n\tprivateKey: {self.privateKey},'
            f'\n\twords: {self.words},'
            f'\n\taddress: {self.address},'
            f'\n\tscripthash: {self.scripthash},'
            f'\n\tbalance: {self.balance},'
            f'\n\tstats: {self.stats},'
            f'\n\tbanner: {self.banner})')

    def authPayload(self, asDict: bool = False, challenge: str = None):
        payload = connection.authPayload(self, challenge)
        if asDict:
            return payload
        return json.dumps(payload)

    def registerPayload(self, asDict: bool = False, challenge: str = None):
        payload = {
            **connection.authPayload(self, challenge),
            **system.devicePayload(asDict=True)}
        if asDict:
            return payload
        return json.dumps(payload)

    def init(self):
        ''' try to load, else generate and save '''
        if self.load():
            self.regenerate()
        else:
            self.generate()
            self.save()
        if not self.temporary:
            self.get()

    def load(self):
        wallet = WalletApi.load(walletPath=self.walletPath)
        if wallet == False:
            return False
        self._entropy = wallet.get('entropy')
        self.publicKey = wallet.get('publicKey')
        self.privateKey = wallet.get('privateKey')
        self.words = wallet.get('words')
        self.address = wallet.get('address')
        self.scripthash = wallet.get('scripthash')
        if self._entropy is None:
            return False
        logging.info('load', self.publicKey, self.walletPath)
        return True

    def save(self):
        WalletApi.save(
            wallet={
                'entropy': self._entropy,
                'publicKey': self.publicKey,
                'privateKey': self.privateKey,
                'words': self.words,
                'address': self.address,
                'scripthash': self.scripthash,
            },
            walletPath=self.walletPath)

    def regenerate(self):
        self.generate()

    def generate(self):
        self._entropy = self._entropy or self._generateEntropy()
        self._privateKeyObj = self._generatePrivateKey()
        self._addressObj = self._generateAddress()
        self.words = self.words or self._generateWords()
        self.privateKey = self.privateKey or str(self._privateKeyObj)
        self.publicKey = self.publicKey or self._privateKeyObj.pub.hex()
        self.address = self.address or str(self._addressObj)
        self.scripthash = self.scripthash or self._generateScripthash()

    def _generateScripthash(self):
        # possible shortcut:
        # self.scripthash = '76a914' + [s for s in self._addressObj.to_scriptPubKey().raw_iter()][2][1].hex() + '88ac'
        from base58 import b58decode_check
        from binascii import hexlify
        from hashlib import sha256
        import codecs
        OP_DUP = b'76'
        OP_HASH160 = b'a9'
        BYTES_TO_PUSH = b'14'
        OP_EQUALVERIFY = b'88'
        OP_CHECKSIG = b'ac'
        def DATA_TO_PUSH(address): return hexlify(b58decode_check(address)[1:])

        def sig_script_raw(address): return b''.join(
            (OP_DUP, OP_HASH160, BYTES_TO_PUSH, DATA_TO_PUSH(address), OP_EQUALVERIFY, OP_CHECKSIG))
        def scripthash(address): return sha256(codecs.decode(
            sig_script_raw(address), 'hex_codec')).digest()[::-1].hex()
        return scripthash(self.address)

    def _generateEntropy(self):
        # return m.to_entropy(m.generate())
        return os.urandom(32)

    def _generateWords(self):
        return mnemonic.Mnemonic('english').to_mnemonic(self._entropy)

    def _generatePrivateKey(self):
        ''' returns a private key object '''

    def _generateAddress(self):
        ''' returns an address object '''

    def showStats(self):
        ''' returns a string of stats properly formatted '''

    def showBalance(self, base=False):
        ''' returns a string of balance properly formatted '''
        def invertDivisibility(divisibility: int):
            return (16 + 1) % (divisibility + 8 + 1)

        if base:
            balance = (self.base or 0) / int('1' + ('0'*8))
        else:
            if self.balance == 'unknown':
                return self.balance
            balance = (self.balance /
                       int('1' + ('0'*invertDivisibility(int(self.stats.get('divisions', 8))))))
        headTail = str(balance).split('.')
        if headTail[1] == '0':
            return f"{int(headTail[0]):,}"
        else:
            return f"{int(headTail[0]):,}" + '.' + f"{headTail[1][0:4]}" + '.' + f"{headTail[1][4:]}"

    def get(self, allWalletInfo=False):
        ''' gets data from the blockchain, saves to attributes '''

    def satoriTransaction(self, amountByAddress: dict):
        ''' creates a transaction '''

    def sign(self, message: str):
        ''' signs a message with the private key '''

    def verify(self, message: str, sig: bytes):
        ''' verifies a message with the public key '''
