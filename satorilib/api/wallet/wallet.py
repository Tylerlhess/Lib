import os
import json
from random import randrange
import mnemonic
from satoriwallet.lib import connection
from satoriwallet import TxUtils, Validate
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
        self.currency = None
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
            f'{self.chain}Wallet('
            f'\n\tpublicKey: {self.publicKey},'
            f'\n\tprivateKey: {self.privateKey},'
            f'\n\twords: {self.words},'
            f'\n\taddress: {self.address},'
            f'\n\tscripthash: {self.scripthash},'
            f'\n\tbalance: {self.balance},'
            f'\n\tstats: {self.stats},'
            f'\n\tbanner: {self.banner})')

    @property
    def symbol(self) -> str:
        return 'wallet'

    @property
    def chain(self) -> str:
        return ''

    @property
    def satoriOriginalTxHash(self) -> str:
        return ''

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
    Issuing Transactions: {self.stats.get('source', {}).get('tx_hash', self.satoriOriginalTxHash)}
    '''

    def showBalance(self, currency=False):
        ''' returns a string of balance properly formatted '''
        def invertDivisibility(divisibility: int):
            return (16 + 1) % (divisibility + 8 + 1)

        if currency:
            balance = (self.currency or 0) / int('1' + ('0'*8))
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
        # todo: encrypt wallet file... entropy, words, privateKey
        # do not encrypt publicKey, address, scripthash. we need these without a password,
        # in order to see your words or anything you need to put in your password.

        self.yaml = WalletApi.load(walletPath=self.walletPath)
        if self.yaml == False:
            return False
        self._entropy = self.yaml.get('entropy')
        # # these are regenerated from entropy in every case
        # self.words = self.yaml.get('words')
        # thisWallet = self.yaml.get(self.identifier, {})
        # self.publicKey = thisWallet.get('publicKey')
        # self.privateKey = thisWallet.get('privateKey')
        # self.address = thisWallet.get('address')
        # self.scripthash = thisWallet.get('scripthash')
        if self._entropy is None:
            return False
        logging.info('load', self.publicKey, self.walletPath)
        return True

    def save(self):
        WalletApi.save(
            wallet={
                **(self.yaml if hasattr(self, 'yaml') else {}),
                **{
                    'entropy': self._entropy,
                    'words': self.words,
                    'privateKey': self.privateKey,
                    'publicKey': self.publicKey,
                    'scripthash': self.scripthash,
                    self.identifier: {
                        'address': self.address,
                    }
                }
            },
            walletPath=self.walletPath)

    def regenerate(self):
        saveIt = False
        if not hasattr(self, 'privateKey') or self.privateKey is None:
            saveIt = True
        self.generate()
        if saveIt:
            self.save()

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

    @property
    def reserve(self) -> int:
        ''' maintain minimum amount of currency at all times to cover fees '''
        return TxUtils.asSats(3)

    def showStats(self):
        ''' returns a string of stats properly formatted '''

    def showBalance(self, base=False):
        ''' returns a string of balance properly formatted '''
        def invertDivisibility(divisibility: int):
            return (16 + 1) % (divisibility + 8 + 1)

        if base:
            balance = (self.currency or 0) / int('1' + ('0'*8))
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
        # x = Evrmore(self.address, self.scripthash, config.electrumxServers())
        # todo: this list of servers should be parameterized from configuration

        # todo:
        # on connect ask for peers, add each to our list of electrumxServers
        # if unable to connect, remove that server from our list
        self.electrumx.get(allWalletInfo)
        self.conn = self.electrumx
        self.balance = self.electrumx.balance
        self.stats = self.electrumx.stats
        self.banner = self.electrumx.banner
        self.currency = self.electrumx.currency
        self.transactionHistory = self.electrumx.transactionHistory
        self.transactions = self.electrumx.transactions or []
        self.unspentCurrency = self.electrumx.unspentCurrency
        self.unspentAssets = self.electrumx.unspentAssets
        # self.currencyVouts = self.electrumx.evrVouts
        # self.assetVouts = self.electrumx.assetVouts

    def sign(self, message: str):
        ''' signs a message with the private key '''

    def verify(self, message: str, sig: bytes):
        ''' verifies a message with the public key '''

    def _gatherCurrencyUnspents(
        self,
        sats: int = 0,
        inputCount: int = 0,
        outputCount: int = 0,
        randomly: bool = False,
    ) -> tuple[list, list]:
        unspentCurrency = [
            x for x in self.unspentCurrency if x.get('value') > 0]
        unspentCurrency = sorted(unspentCurrency, key=lambda x: x['value'])
        haveCurrency = sum([x.get('value') for x in unspentCurrency])
        if (haveCurrency < sats + self.reserve):
            raise Exception(
                'tx: must retain a reserve of currency to cover fees')
        gatheredCurrencySats = 0
        gatheredCurrencyUnspents = []
        while (
            gatheredCurrencySats < sats + TxUtils.estimatedFee(
                inputCount=inputCount + len(gatheredCurrencyUnspents),
                outputCount=outputCount)
        ):
            if randomly:
                randomUnspent = unspentCurrency.pop(
                    randrange(len(unspentCurrency)))
                gatheredCurrencyUnspents.append(randomUnspent)
                gatheredCurrencySats += randomUnspent.get('value')
            else:
                smallestUnspent = unspentCurrency.pop(0)
                gatheredCurrencyUnspents.append(smallestUnspent)
                gatheredCurrencySats += smallestUnspent.get('value')
        return (gatheredCurrencySats, gatheredCurrencyUnspents)

    def _gatherSatoriUnspents(
        self,
        sats: int,
        randomly: bool = False
    ) -> tuple[list, int]:
        unspentSatori = [x for x in self.unspentAssets if x.get(
            'name') == 'SATORI' and x.get('value') > 0]
        unspentSatori = sorted(unspentSatori, key=lambda x: x['value'])
        haveSatori = sum([x.get('value') for x in unspentSatori])
        if not (haveSatori >= sats > 0):
            raise Exception('tx: not enough satori to send')
        # gather satori utxos at random
        gatheredSatoriSats = 0
        gatheredSatoriUnspents = []
        while gatheredSatoriSats < sats:
            if randomly:
                randomUnspent = unspentSatori.pop(
                    randrange(len(unspentSatori)))
                gatheredSatoriUnspents.append(randomUnspent)
                gatheredSatoriSats += randomUnspent.get('value')
            else:
                smallestUnspent = unspentSatori.pop(0)
                gatheredSatoriUnspents.append(smallestUnspent)
                gatheredSatoriSats += smallestUnspent.get('value')
        return (gatheredSatoriSats, gatheredSatoriUnspents)

    def _compileInputs(
        self,
        gatheredCurrencyUnspents: list = None,
        gatheredSatoriUnspents: list = None,
    ) -> tuple[list, list]:
        ''' compile inputs '''
        # see https://github.com/sphericale/python-evrmorelib/blob/master/examples/spend-p2pkh-txout.py

    def _compileSatoriOutputs(self, amountByAddress: dict[str, float] = None) -> list:
        ''' compile satori outputs'''
        # see https://github.com/sphericale/python-evrmorelib/blob/master/examples/spend-p2pkh-txout.py
        # vouts
        # how do I specify an asset output? this doesn't seem right for that:
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG OP_RVN_ASSET 0c72766e6f075341544f524921 75
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG 0c(OP_RVN_ASSET) 72766e(rvn) 74(t) 07(length) 5341544f524921(SATORI) 00e1f50500000000(padded little endian hex of 100000000) 75(drop)
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG 0c(OP_RVN_ASSET) 72766e(rvn) 74(t) 07(length) 5341544f524921(SATORI) 00e1f50500000000(padded little endian hex of 100000000) 75(drop)
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG 0c(OP_RVN_ASSET) 14(20 bytes length of asset information) 657672(evr) 74(t) 07(length of asset name) 5341544f524921(SATORI is asset name) 00e1f50500000000(padded little endian hex of 100000000) 75(drop)
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG 0c1465767274075341544f52492100e1f5050000000075
        # CScript([OP_DUP, OP_HASH160, Hash160(self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG ])
        # CScript([OP_DUP, OP_HASH160, Hash160(self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG OP_EVR_ASSET 0c ])
        #
        # for asset transfer...? perfect?
        #   >>> Hash160(CRavencoinAddress(address).to_scriptPubKey())
        #   b'\xc2\x0e\xdf\x8cG\xd7\x8d\xac\x052\x03\xddC<0\xdd\x00\x91\xd9\x19'
        #   >>> Hash160(CRavencoinAddress(address))
        #   b'!\x8d"6\xcf\xe8\xf6W4\x830\x85Y\x06\x01J\x82\xc4\x87p' <- looks like what we get with self.pubkey.encode()
        # https://ravencoin.org/assets/
        # https://rvn.cryptoscope.io/api/getrawtransaction/?txid=bae95f349f15effe42e75134ee7f4560f53462ddc19c47efdd03f85ef4ab8f40&decode=1

    def _compileCurrencyOutputs(self, currencySats: int, address: str) -> list['CMutableTxOut']:
        ''' compile currency outputs'''

    def _compileSatoriChangeOutputs(
        self,
        txouts: list,
        satoriSats: int = 0,
        gatheredSatoriSats: int = 0,
    ) -> list:
        ''' compile satori change outputs '''

    def _compileCurrencyChangeOutputs(
        self,
        txouts: list,
        currencySats: int = 0,
        gatheredCurrencySats: int = 0,
        inputCount: int = 0,
        outputCount: int = 0,
    ) -> list:
        ''' compile currency change outputs '''

    def _createTransaction(self, txins: list, txinScripts: list, txouts: list) -> 'CMutableTransaction':
        ''' create transaction '''

    def _txToHex(self, tx: 'CMutableTransaction') -> str:
        ''' serialize '''

    def _broadcast(self, txHex: str) -> str:
        if self.electrumx.connected():
            return self.electrumx.broadcast(txHex)
        return self.electrumx.broadcast(txHex)

    # for server
    def satoriDistribution(self, amountByAddress: dict[str: float]) -> str:
        ''' creates a transaction with multiple SATORI asset recipients '''
        if len(amountByAddress) == 0 or len(amountByAddress) > 1000:
            raise Exception('too many or too few recipients')
        satoriSats = TxUtils.asSats(sum(amountByAddress.values()))
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self._gatherSatoriUnspents(satoriSats)
        (
            gatheredCurrencyUnspents,
            gatheredCurrencySats) = self._gatherCurrencyUnspents(
                inputCount=len(gatheredSatoriUnspents),
                outputCount=len(amountByAddress) + 2,)
        txins, txinScripts = self._compileInputs(
            gatheredCurrencyUnspents=gatheredCurrencyUnspents,
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        txouts = self._compileCurrencyChangeOutputs(
            txouts=self._compileSatoriChangeOutputs(
                txouts=self._compileSatoriOutputs(amountByAddress),
                satoriSats=satoriSats,
                gatheredSatoriSats=gatheredSatoriSats),
            gatheredCurrencySats=gatheredCurrencySats,
            inputCount=len(gatheredSatoriUnspents) +
            len(gatheredCurrencyUnspents),
            outputCount=len(amountByAddress) + 2)
        tx = self._createTransaction(txins, txinScripts, txouts)
        return self._broadcast(self._txToHex(tx))

    # for neuron
    def currencyTransaction(self, amount: float, address: str):
        ''' creates a transaction to just send rvn '''
        if amount <= 0 or Validate.address(address, self.symbol):
            raise Exception('bad params for currencyTransaction')
        currencySats = TxUtils.asSats(amount)
        (
            gatheredCurrencyUnspents,
            gatheredCurrencySats) = self._gatherCurrencyUnspents(
                sats=currencySats,
                inputCount=0,
                outputCount=1)
        txins, txinScripts = self._compileInputs(
            gatheredCurrencyUnspents=gatheredCurrencyUnspents)
        txouts = self._compileCurrencyChangeOutputs(
            txouts=self._compileCurrencyOutputs(currencySats, address),
            currencySats=currencySats,
            gatheredCurrencySats=gatheredCurrencySats,
            inputCount=len(txins),
            outputCount=2)
        tx = self._createTransaction(txins, txinScripts, txouts)
        return self._broadcast(self._txToHex(tx))

    def satoriTransaction(self, amount: float, address: str):
        ''' creates a transaction to send satori to one address '''
        if amount <= 0 or Validate.address(address, self.symbol):
            raise Exception('satoriTransaction bad params')
        satoriSats = TxUtils.asSats(amount)
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self._gatherSatoriUnspents(satoriSats)
        txins, txinScripts = self._compileInputs(
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        txouts = self._compileCurrencyChangeOutputs(
            txouts=self._compileSatoriChangeOutputs(
                txouts=self._compileSatoriOutputs({address: amount}),
                satoriSats=satoriSats,
                gatheredSatoriSats=gatheredSatoriSats),
            inputCount=len(gatheredSatoriUnspents),
            outputCount=2)
        tx = self._createTransaction(txins, txinScripts, txouts)
        return self._broadcast(self._txToHex(tx))

    def satoriAndCurrencyTransaction(self, satoriAmount: float, currencyAmount: float, address: str):
        ''' creates a transaction to send satori and currency to one address '''
        if satoriAmount <= 0 or currencyAmount <= 0 or Validate.address(address, self.symbol):
            raise Exception('satoriAndCurrencyTransaction bad params')
        satoriSats = TxUtils.asSats(satoriAmount)
        currencySats = TxUtils.asSats(currencyAmount)
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self._gatherSatoriUnspents(satoriSats)
        (
            gatheredCurrencyUnspents,
            gatheredCurrencySats) = self._gatherCurrencyUnspents(
                sats=currencySats,
                inputCount=len(gatheredSatoriUnspents),
                outputCount=4)
        txins, txinScripts = self._compileInputs(
            gatheredCurrencyUnspents=gatheredCurrencyUnspents,
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        txouts = self._compileCurrencyChangeOutputs(
            txouts=self._compileSatoriChangeOutputs(
                txouts=(
                    self._compileSatoriOutputs({address: satoriAmount}) +
                    self._compileCurrencyOutputs(currencySats, address)),
                satoriSats=satoriSats,
                gatheredSatoriSats=gatheredSatoriSats),
            currencySats=currencySats,
            gatheredCurrencySats=gatheredCurrencySats,
            inputCount=(
                len(gatheredSatoriUnspents) +
                len(gatheredCurrencyUnspents)),
            outputCount=4)
        tx = self._createTransaction(txins, txinScripts, txouts)
        return self._broadcast(self._txToHex(tx))

    def satoriOnlyTransaction(self, amount: int, address: str) -> str:
        '''
        if people do not have a balance of rvn, they can still send satori.
        they have to pay the fee in satori, so it's a higher fee, maybe twice
        as much on average as a normal transaction. this is because the 
        variability of the satori price. So this function produces a partial
        transaction that can be sent to the server and the rest of the network 
        to be completed. he who completes the transaction will pay the rvn fee
        and collect the satori fee. we will probably broadcast as a json object.
        '''
        return 'json transaction with incomplete elements'

    def satoriOnlyTransactionCompleted(self, transaction: dict) -> str:
        '''
        a companion function to satoriOnlyTransaction which completes the 
        transaction add in it's own address for the satori fee and injecting the
        necessary rvn inputs to cover the fee.
        '''
        return 'broadcast result'
