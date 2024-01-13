from random import randrange
from evrmore import SelectParams
from evrmore.wallet import P2PKHEvrmoreAddress, CEvrmoreSecret
from satoriwallet import Evrmore
from satoriwallet import evrmore
from satoriwallet import TxUtils, Validate, AssetTransaction
from evrmore.wallet import CEvrmoreAddress, CEvrmoreSecret
from evrmore.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from evrmore.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, OP_EVR_ASSET, OP_DROP
from evrmore.core import b2x, lx, COIN, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from satorilib.api.wallet.wallet import Wallet


class EvrmoreWallet(Wallet):

    def __init__(self, walletPath, temporary=False):
        super().__init__(walletPath, temporary)

    def __repr__(self):
        return (
            'EvrmoreWallet('
            f'\n\tpublicKey: {self.publicKey},'
            f'\n\tprivateKey: {self.privateKey},'
            f'\n\twords: {self.words},'
            f'\n\taddress: {self.address},'
            f'\n\tscripthash: {self.scripthash},'
            f'\n\tbalance: {self.balance},'
            f'\n\tstats: {self.stats},'
            f'\n\tbanner: {self.banner})')

    @property
    def identifier(self):
        return 'evr'

    def _generatePrivateKey(self):
        SelectParams('mainnet')
        return CEvrmoreSecret.from_secret_bytes(self._entropy)

    def _generateAddress(self):
        return P2PKHEvrmoreAddress.from_pubkey(self._privateKeyObj.pub)

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
    Issuing Transactions: {self.stats.get('source', {}).get('tx_hash', 'df745a3ee1050a9557c3b449df87bdd8942980dff365f7f5a93bc10cb1080188')}
    '''
    # SATORI df745a3ee1050a9557c3b449df87bdd8942980dff365f7f5a93bc10cb1080188
    # SATORI/TEST 15dd33886452c02d58b500903441b81128ef0d21dd22502aa684c002b37880fe

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

    def get(self, allWalletInfo=False):
        ''' gets data from the blockchain, saves to attributes '''
        # x = Evrmore(self.address, self.scripthash, config.electrumxServers())
        # todo: this list of servers should be parameterized from configuration
        x = Evrmore(self.address, self.scripthash, [
            'moontree.com:50022',  # mainnet ssl evr
            'electrum1-mainnet.evrmorecoin.org:50002',  # ssl
            'electrum2-mainnet.evrmorecoin.org:50002',  # ssl
            # 'electrum1-mainnet.evrmorecoin.org:50001',  # tcp
            # 'electrum2-mainnet.evrmorecoin.org:50001',  # tcp
            # 'moontree.com:50021',  # mainnet tcp evr
            # 'moontree.com:50031', # testnet tcp evr
            # 'moontree.com:50032', # testnet ssl evr
            # 'electrum1-mainnet.evrmorecoin.org:50004', # wss
            # 'electrum2-mainnet.evrmorecoin.org:50004', # wss
            # 'electrum1-testnet.evrmorecoin.org:50001', # tcp
            # 'electrum1-testnet.evrmorecoin.org:50002', # ssl
            # 'electrum1-testnet.evrmorecoin.org:50004', # wss
        ])
        # todo:
        # on connect ask for peers, add each to our list of electrumxServers
        # if unable to connect, remove that server from our list
        x.get(allWalletInfo)
        self.conn = x
        self.balance = x.balance
        self.stats = x.stats
        self.banner = x.banner
        self.currency = x.currency
        self.transactionHistory = x.transactionHistory
        self.transactions = x.transactions or []
        self.unspentCurrency = x.unspentCurrency
        self.unspentAssets = x.unspentAssets
        # self.currencyVouts = x.evrVouts
        # self.assetVouts = x.assetVouts

    def gatherCurrencyUnspents(
        self,
        sats: int = 0,
        inputCount: int = 0,
        outputCount: int = 0,
        randomly: bool = False,
    ) -> tuple[list, list]:
        unspentCurrency = [
            x for x in self.unspentCurrency if x.get('value') > 0]
        unspentCurrency = sorted(unspentCurrency, key=lambda x: x['value'])
        haveEvr = sum([x.get('value') for x in unspentCurrency])
        if (haveEvr < self.reserve):
            raise Exception('tx: must retain a reserve of evr to cover fees')
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

    def gatherSatoriUnspents(
        self,
        sats: int,
        randomly: bool = False
    ) -> tuple[list, int]:
        unspentSatori = [x for x in self.unspentAssets if x.get(
            'name') == 'SATORI' and x.get('value') > 0]
        unspentSatori = sorted(unspentSatori, key=lambda x: x['value'])
        haveSatori = sum([x.get('value') for x in unspentSatori])
        if (haveSatori >= sats > 0):
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

    def compileInputs(
        self,
        gatheredCurrencyUnspents: list = None,
        gatheredSatoriUnspents: list = None,
    ) -> tuple[list, list]:
        # see https://github.com/sphericale/python-evrmorelib/blob/master/examples/spend-p2pkh-txout.py
        # currency vins
        txins = []
        txinScripts = []
        for utxo in (gatheredCurrencyUnspents or []):
            txin = CMutableTxIn(
                COutPoint(lx(utxo.get('tx_hash')), utxo.get('tx_pos')))
            txin_scriptPubKey = CScript([OP_DUP, OP_HASH160, Hash160(
                self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG])
            txins.append(txin)
            txinScripts.append(txin_scriptPubKey)
        # satori vins
        for utxo in (gatheredSatoriUnspents or []):
            txin = CMutableTxIn(
                COutPoint(lx(utxo.get('tx_hash')), utxo.get('tx_pos')))
            txin_scriptPubKey = CScript([OP_DUP, OP_HASH160, Hash160(
                self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG])
            txins.append(txin)
            txinScripts.append(txin_scriptPubKey)

        return txins, txinScripts

    def compileSatoriOutputs(self, amountByAddress: dict[str, float] = None) -> list:
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
        txouts = []
        for address, amount in amountByAddress.items():
            # for asset transfer...? perfect?
            #   >>> Hash160(CRavencoinAddress(address).to_scriptPubKey())
            #   b'\xc2\x0e\xdf\x8cG\xd7\x8d\xac\x052\x03\xddC<0\xdd\x00\x91\xd9\x19'
            #   >>> Hash160(CRavencoinAddress(address))
            #   b'!\x8d"6\xcf\xe8\xf6W4\x830\x85Y\x06\x01J\x82\xc4\x87p' <- looks like what we get with self.pubkey.encode()
            # https://ravencoin.org/assets/
            # https://rvn.cryptoscope.io/api/getrawtransaction/?txid=bae95f349f15effe42e75134ee7f4560f53462ddc19c47efdd03f85ef4ab8f40&decode=1
            sats = TxUtils.asSats(amount*COIN)
            txout = CMutableTxOut(
                0,
                CScript([
                    OP_DUP, OP_HASH160,
                    TxUtils.addressToH160Bytes(address),
                    OP_EQUALVERIFY, OP_CHECKSIG, OP_EVR_ASSET,
                    bytes.fromhex(
                        AssetTransaction.satoriEvrHex() +
                        TxUtils.padHexStringTo8Bytes(
                            TxUtils.intToLittleEndianHex(
                                sats))),
                    OP_DROP]))
            txouts.append(txout)
        return txouts

    def compileCurrencyOutputs(self, currencySats: int, address: str) -> list[CMutableTxOut]:
        return [CMutableTxOut(currencySats, CEvrmoreAddress(address).to_scriptPubKey())]

    def compileSatoriChangeOutputs(
        self,
        txouts: list,
        satoriSats: int = 0,
        gatheredSatoriSats: int = 0,
    ) -> list:
        satoriChange = gatheredSatoriSats - satoriSats
        if satoriChange > 0:
            txouts.append(CMutableTxOut(
                satoriChange, self.address.to_scriptPubKey()))
        elif satoriChange < 0:
            raise Exception('tx: not enough satori to send')
        return txouts

    def compileCurrencyChangeOutputs(
        self,
        txouts: list,
        currencySats: int = 0,
        gatheredCurrencySats: int = 0,
        inputCount: int = 0,
        outputCount: int = 0,
    ) -> list:
        currencyChange = gatheredCurrencySats - currencySats - TxUtils.estimatedFee(
            inputCount=inputCount,
            outputCount=outputCount)
        if currencyChange > 0:
            txouts.append(
                CMutableTxOut(currencyChange, self.address.to_scriptPubKey()))
        elif currencyChange < 0:
            # go back and get more?
            raise Exception('tx: not enough currency to send')
        return txouts

    def createTransaction(self, txins: list, txinScripts: list, txouts: list) -> CMutableTransaction:
        # create transaction
        tx = CMutableTransaction(txins, txouts)
        for i, (txin, txin_scriptPubKey) in enumerate(zip(txins, txinScripts)):
            sighash = SignatureHash(txin_scriptPubKey, tx, i, SIGHASH_ALL)
            sig = self.privateKey.sign(sighash) + bytes([SIGHASH_ALL])
            txin.scriptSig = CScript([sig, self.privateKey.pub])
            VerifyScript(txin.scriptSig, txin_scriptPubKey,
                         tx, i, (SCRIPT_VERIFY_P2SH,))
        return tx

    def txToHex(self, tx: CMutableTransaction) -> str:
        return b2x(tx.serialize())

    def broadcast(self, txHex: str) -> str:
        print(txHex)
        # in theory we can send the serialized tx to the blockchain through electrumx
        if self.conn.connected():
            return self.conn.broadcast(txHex)
        # this is dumb, fix it.
        x = Evrmore(self.address, self.scripthash, [
            'moontree.com:50022',  # mainnet ssl evr
            'electrum1-mainnet.evrmorecoin.org:50002',  # ssl
            'electrum2-mainnet.evrmorecoin.org:50002',  # ssl
        ])
        self.conn = x
        return x.broadcast(txHex)

    # for server
    def satoriDistribution(self, amountByAddress: dict[str: float]) -> str:
        ''' creates a transaction with multiple SATORI asset recipients '''
        if len(amountByAddress) == 0 or len(amountByAddress) > 1000:
            raise Exception('too many or too few recipients')
        satoriSats = TxUtils.asSats(sum(amountByAddress.values()))
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self.gatherSatoriUnspents(satoriSats)
        (
            gatheredCurrencyUnspents,
            gatheredCurrencySats) = self.gatherCurrencyUnspents(
                inputCount=len(gatheredSatoriUnspents),
                outputCount=len(amountByAddress) + 2,)
        txins, txinScripts = self.compileInputs(
            gatheredCurrencyUnspents=gatheredCurrencyUnspents,
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        txouts = self.compileCurrencyChangeOutputs(
            txouts=self.compileSatoriChangeOutputs(
                txouts=self.compileSatoriOutputs(amountByAddress),
                satoriSats=satoriSats,
                gatheredSatoriSats=gatheredSatoriSats),
            gatheredCurrencySats=gatheredCurrencySats,
            inputCount=len(gatheredSatoriUnspents) +
            len(gatheredCurrencyUnspents),
            outputCount=len(amountByAddress) + 2)
        tx = self.createTransaction(txins, txinScripts, txouts)
        return self.broadcast(self.txToHex(tx))

    # for neuron
    def currencyTransaction(self, amount: float, address: str):
        ''' creates a transaction to just send rvn '''
        if amount <= 0 or Validate.address(address, self.identifier):
            raise Exception('bad params for currencyTransaction')
        currencySats = TxUtils.asSats(amount)
        (
            gatheredCurrencyUnspents,
            gatheredCurrencySats) = self.gatherCurrencyUnspents(
                sats=currencySats,
                inputCount=0,
                outputCount=1)
        txins, txinScripts = self.compileInputs(
            gatheredCurrencyUnspents=gatheredCurrencyUnspents)
        txouts = self.compileCurrencyChangeOutputs(
            txouts=self.compileCurrencyOutputs(currencySats, address),
            currencySats=currencySats,
            gatheredCurrencySats=gatheredCurrencySats,
            inputCount=len(txins),
            outputCount=2)
        tx = self.createTransaction(txins, txinScripts, txouts)
        return self.broadcast(self.txToHex(tx))

    def satoriTransaction(self, amount: float, address: str):
        ''' creates a transaction to send satori to one address '''
        if amount <= 0 or Validate.address(address, self.identifier):
            raise Exception('satoriTransaction bad params')
        satoriSats = TxUtils.asSats(amount)
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self.gatherSatoriUnspents(satoriSats)
        txins, txinScripts = self.compileInputs(
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        txouts = self.compileCurrencyChangeOutputs(
            txouts=self.compileSatoriChangeOutputs(
                txouts=self.compileSatoriOutputs({address: amount}),
                satoriSats=satoriSats,
                gatheredSatoriSats=gatheredSatoriSats),
            inputCount=len(gatheredSatoriUnspents),
            outputCount=2)
        tx = self.createTransaction(txins, txinScripts, txouts)
        return self.broadcast(self.txToHex(tx))

    def satoriAndCurrencyTransaction(self, satoriAmount: float, currencyAmount: float, address: str):
        ''' creates a transaction to send satori and currency to one address '''
        if satoriAmount <= 0 or currencyAmount <= 0 or Validate.address(address, self.identifier):
            raise Exception('satoriAndCurrencyTransaction bad params')
        satoriSats = TxUtils.asSats(satoriAmount)
        currencySats = TxUtils.asSats(currencyAmount)
        (
            gatheredSatoriUnspents,
            gatheredSatoriSats) = self.gatherSatoriUnspents(satoriSats)
        (
            gatheredCurrencyUnspents,
            gatheredCurrencySats) = self.gatherCurrencyUnspents(
                sats=currencySats,
                inputCount=len(gatheredSatoriUnspents),
                outputCount=4)
        txins, txinScripts = self.compileInputs(
            gatheredCurrencyUnspents=gatheredCurrencyUnspents,
            gatheredSatoriUnspents=gatheredSatoriUnspents)
        txouts = self.compileCurrencyChangeOutputs(
            txouts=self.compileSatoriChangeOutputs(
                txouts=(
                    self.compileSatoriOutputs({address: satoriAmount}) +
                    self.compileCurrencyOutputs(currencySats, address)),
                satoriSats=satoriSats,
                gatheredSatoriSats=gatheredSatoriSats),
            currencySats=currencySats,
            gatheredCurrencySats=gatheredCurrencySats,
            inputCount=(
                len(gatheredSatoriUnspents) +
                len(gatheredCurrencyUnspents)),
            outputCount=4)
        tx = self.createTransaction(txins, txinScripts, txouts)
        return self.broadcast(self.txToHex(tx))

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

    def sign(self, message: str):
        return evrmore.signMessage(self._privateKeyObj, message)

    def verify(self, message: str, sig: bytes):
        return evrmore.verify(address=self.address, message=message, signature=sig)
