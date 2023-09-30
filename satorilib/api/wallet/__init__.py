import os
import json
import mnemonic
from random import randrange
import ravencoin.base58
from ravencoin.wallet import P2PKHRavencoinAddress, CRavencoinSecret
from satoriwallet.apis.ravencoin import Ravencoin
from satoriwallet.lib import sign, verify as satori_verify
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
        self.rvn = None
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
        ravencoin.SelectParams('mainnet')
        return CRavencoinSecret.from_secret_bytes(self._entropy)

    def _generateAddress(self):
        return P2PKHRavencoinAddress.from_pubkey(self._privateKeyObj.pub)

    def showStats(self):
        ''' returns a string of stats properly formatted '''
        def invertDivisibility(divisibility: int):
            return (16 + 1) % (divisibility + 8 + 1)

        divisions = self.stats.get('divisions', 8)
        circulatingSats = self.stats.get(
            'sats_in_circulation', 100000000000000) / int('1' + ('0'*invertDivisibility(int(divisions))))
        headTail = str(circulatingSats).split('.')
        if headTail[1] == '0' or headTail[1] == '00000000':
            circulatingSats = f"{int(headTail[0]):,}"
        else:
            circulatingSats = f"{int(headTail[0]):,}" + '.' + \
                f"{headTail[1][0:4]}" + '.' + f"{headTail[1][4:]}"
        return f'''
    Circulating Supply: {circulatingSats}
    Decimal Points: {divisions}
    Reissuable: {self.stats.get('reissuable', False)}
    Issuing Transactions: {self.stats.get('source', {}).get('tx_hash', 'a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3')}
    '''

    def showBalance(self, rvn=False):
        ''' returns a string of balance properly formatted '''
        def invertDivisibility(divisibility: int):
            return (16 + 1) % (divisibility + 8 + 1)

        if rvn:
            balance = (self.rvn or 0) / int('1' + ('0'*8))
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
        # x = Ravencoin(self.address, self.scripthash, config.electrumxServers())
        x = Ravencoin(self.address, self.scripthash, ['moontree.com:50002'])
        # todo:
        # on connect ask for peers, add each to our list of electrumxServers
        # if unable to connect, remove that server from our list
        x.get(allWalletInfo)
        self.conn = x
        self.balance = x.balance
        self.stats = x.stats
        self.banner = x.banner
        self.rvn = x.rvn
        self.transactionHistory = x.transactionHistory
        self.transactions = x.transactions or []
        self.unspentRvn = x.unspentRvn
        self.unspentAssets = x.unspentAssets
        self.rvnVouts = x.rvnVouts
        self.assetVouts = x.assetVouts

    def satoriTransaction(self, amountByAddress: dict):
        ''' creates a transaction '''

        def estimatedFee(inputCount: int = 0):
            # TODO: sub optimal, replace when we have a lot of users
            feeRate = 150000  # 0.00150000 rvn per item as simple over-estimate
            outputCount = len(amountByAddress)
            return (inputCount + outputCount) * feeRate

        assert (len(amountByAddress) > 0)
        # sum total amounts and other variables
        unspentRvn = [x for x in self.unspentRvn if x.get('value') > 0]
        unspentSatori = [x for x in self.unspentAssets if x.get(
            'name') == 'SATORI' and x.get('value') > 0]
        haveRvn = sum([x.get('value') for x in unspentRvn])
        haveSatori = sum([x.get('value') for x in unspentSatori])
        sendSatori = sum(amountByAddress.values())
        assert (haveSatori >= sendSatori > 0)
        assert (haveRvn >= 300000000)  # maintain minimum 3 RVN at all times

        # # TODO: sub optimal, if you're sending from one address (not HDWallet)
        # # why not order by size, take the ones just big enough and minimize
        # # the number of inputs, and therefore the fee? just replace the whole
        # # thing with HD wallet and optimize everything eventually.
        # loop until gathered > total
        #   gather satori utxos at random
        gatheredSatori = 0
        gatheredSatoriUnspents = []
        while gatheredSatori < sendSatori:
            randomUnspent = unspentSatori.pop(randrange(len(unspentSatori)))
            gatheredSatoriUnspents.append(randomUnspent)
            gatheredSatori += randomUnspent.get('value')

        # loop until estimated fee > sum rvn utxos
        #   gather rvn utxos at random
        #   estimate fee
        gatheredRvn = 0
        gatheredRvnUnspents = []
        while (
            gatheredRvn < estimatedFee(
                inputCount=len(gatheredSatoriUnspents)+len(gatheredRvnUnspents))
        ):
            randomUnspent = unspentRvn.pop(randrange(len(unspentRvn)))
            gatheredRvnUnspents.append(randomUnspent)
            gatheredRvn += randomUnspent.get('value')

        # add all inputs and outputs to transaction
        # ?? txbuilder
        # ?? see python-ravencoinlib examples
        # sign all inputs
        # ?? see python-ravencoinlib
        # ?? if asset input use (get the self.assetVouts corresponding to the
        # ?? unspent).vout.scriptPubKey.hex.hexBytes
        # send
        # ?? use blockchain.transaction.broadcast raw_tx put function in
        # ?? Ravencoin object since that's our connection object

    def sign(self, message: str):
        return sign.signMessage(self._privateKeyObj, message)

    def verify(self, message: str, sig: bytes):
        return satori_verify(address=self.address, message=message, signature=sig)
