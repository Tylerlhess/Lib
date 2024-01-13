from random import randrange
from evrmore import SelectParams
from evrmore.wallet import P2PKHEvrmoreAddress, CEvrmoreSecret
from satoriwallet import Evrmore
from satoriwallet import evrmore
from satoriwallet import utils as transactionUtils
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

    @property
    def reserve(self) -> int:
        ''' maintain minimum amount of currency at all times to cover fees '''
        return transactionUtils.asSats(3)

    # for neuron
    def currencyTransaction(self, amount: float, address: str):
        ''' creates a transaction to just send rvn '''
        assert (amount > 0 and len(address) == 34)
        sats = transactionUtils.asSats(amount)
        unspentCurrency = [
            x for x in self.unspentCurrency if x.get('value') > 0]
        unspentCurrency = sorted(unspentCurrency, key=lambda x: x['value'])
        haveEvr = sum([x.get('value') for x in unspentCurrency])
        assert (haveEvr >= sats + self.reserve)
        # gather rvn utxos smallest to largest
        gatheredRvn = 0
        gatheredRvnUnspents = []
        while (
            gatheredRvn < sats + transactionUtils.estimatedFee(
                inputCount=len(gatheredRvnUnspents),
                outputCount=2)
        ):
            smallestUnspent = unspentCurrency.pop(0)
            gatheredRvnUnspents.append(smallestUnspent)
            gatheredRvn += smallestUnspent.get('value')
        # make transaction
        # see https://github.com/sphericale/python-evrmorelib/blob/master/examples/spend-p2pkh-txout.py
        from evrmore.wallet import CEvrmoreAddress, CEvrmoreSecret
        from evrmore.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
        from evrmore.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL
        from evrmore.core import b2x, lx, COIN, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
        # vins
        txins = []
        txinScripts = []
        for utxo in gatheredRvnUnspents:
            txin = CMutableTxIn(
                COutPoint(lx(utxo.get('tx_hash')), utxo.get('tx_pos')))
            txin_scriptPubKey = CScript([OP_DUP, OP_HASH160, Hash160(
                self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG])
            txins.append(txin)
            txinScripts.append(txin_scriptPubKey)
        # vouts
        txouts = [
            CMutableTxOut(sats, CEvrmoreAddress(address).to_scriptPubKey())]
        # change
        change = gatheredRvn - sats - transactionUtils.estimatedFee(
            inputCount=len(gatheredRvnUnspents),
            outputCount=2)
        txouts.append(CMutableTxOut(change, self.address.to_scriptPubKey()))
        # create transaction
        tx = CMutableTransaction(txins, txouts)
        for i, (txin, txin_scriptPubKey) in enumerate(zip(txins, txinScripts)):
            sighash = SignatureHash(txin_scriptPubKey, tx, i, SIGHASH_ALL)
            sig = self.privateKey.sign(sighash) + bytes([SIGHASH_ALL])
            txin.scriptSig = CScript([sig, self.privateKey.pub])
            VerifyScript(txin.scriptSig, txin_scriptPubKey,
                         tx, i, (SCRIPT_VERIFY_P2SH,))
        txToBroadcast = b2x(tx.serialize())
        print(txToBroadcast)
        # in theory we can send the serialized tx to the blockchain through electrumx
        result = None
        if self.conn.connected():
            result = self.conn.broadcast(txToBroadcast)
        else:
            # this is dumb, fix it.
            x = Evrmore(self.address, self.scripthash, [
                'moontree.com:50022',  # mainnet ssl evr
                'electrum1-mainnet.evrmorecoin.org:50002',  # ssl
                'electrum2-mainnet.evrmorecoin.org:50002',  # ssl
            ])
            self.conn = x
            result = x.broadcast(b2x(tx.serialize()))
        return result

    def satoriTransaction(self, amount: int, address: str):
        ''' creates a transaction to send satori to one address '''
        return amount, address

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

    def gatherCurrencyUnspents(
        self,
        sats: int = 0,
        inputCount: int = 0,
        outputCount: int = 0,
        randomly: bool = False,
    ) -> list:
        unspentCurrency = [
            x for x in self.unspentCurrency if x.get('value') > 0]
        unspentCurrency = sorted(unspentCurrency, key=lambda x: x['value'])
        haveEvr = sum([x.get('value') for x in unspentCurrency])
        if (haveEvr < self.reserve):
            raise Exception('tx: must retain a reserve of evr to cover fees')
        gatheredRvn = 0
        gatheredRvnUnspents = []
        while (
            gatheredRvn < sats + transactionUtils.estimatedFee(
                inputCount=inputCount + len(gatheredRvnUnspents),
                outputCount=outputCount)
        ):
            if randomly:
                randomUnspent = unspentCurrency.pop(
                    randrange(len(unspentCurrency)))
                gatheredRvnUnspents.append(randomUnspent)
                gatheredRvn += randomUnspent.get('value')
            else:
                smallestUnspent = unspentCurrency.pop(0)
                gatheredRvnUnspents.append(smallestUnspent)
                gatheredRvn += smallestUnspent.get('value')

    def gatherSatoriUnspents(self, sats: int, randomly: bool = False) -> tuple[list, int]:
        unspentSatori = [x for x in self.unspentAssets if x.get(
            'name') == 'SATORI' and x.get('value') > 0]
        unspentSatori = sorted(unspentSatori, key=lambda x: x['value'])
        haveSatori = sum([x.get('value') for x in unspentSatori])
        if (haveSatori >= sats > 0):
            raise Exception('tx: not enough satori to send')
        # gather satori utxos at random
        gatheredSatori = 0
        gatheredSatoriUnspents = []
        while gatheredSatori < sats:
            if randomly:
                randomUnspent = unspentSatori.pop(
                    randrange(len(unspentSatori)))
                gatheredSatoriUnspents.append(randomUnspent)
                gatheredSatori += randomUnspent.get('value')
            else:
                smallestUnspent = unspentSatori.pop(0)
                gatheredSatoriUnspents.append(smallestUnspent)
                gatheredSatori += smallestUnspent.get('value')

    # for server
    def satoriDistribution(self, amountByAddress: dict[str: int]):
        ''' creates a transaction with multiple SATORI asset recipients '''
        if len(amountByAddress) == 0 or len(amountByAddress) > 1000:
            raise Exception('too many or too few recipients')
        # sum total amounts and other variables
        satoriSats = transactionUtils.asSats(sum(amountByAddress.values()))
        (
            gatheredSatoriUnspents,
            gatheredSatori) = self.gatherSatoriUnspents(satoriSats)
        (
            gatheredCurrencyUnspents,
            gatheredCurrency) = self.gatherCurrencyUnspents(
                inputCount=len(gatheredSatoriUnspents),
                outputCount=len(amountByAddress) + 2,)

        # see https://github.com/sphericale/python-evrmorelib/blob/master/examples/spend-p2pkh-txout.py
        from evrmore.wallet import CEvrmoreAddress, CEvrmoreSecret
        from evrmore.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
        from evrmore.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, OP_EVR_ASSET, CScriptOp, OP_DROP
        from evrmore.core import b2x, lx, COIN, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160

        # currency vins
        for utxo in gatheredCurrencyUnspents:
            txin = CMutableTxIn(
                COutPoint(lx(utxo.get('tx_hash')), utxo.get('tx_pos')))
            txin_scriptPubKey = CScript([OP_DUP, OP_HASH160, Hash160(
                self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG])
            txins.append(txin)
            txinScripts.append(txin_scriptPubKey)

        # satori vins
        for utxo in gatheredSatoriUnspents:
            txin = CMutableTxIn(
                COutPoint(lx(utxo.get('tx_hash')), utxo.get('tx_pos')))
            txin_scriptPubKey = CScript([OP_DUP, OP_HASH160, Hash160(
                self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG])
            txins.append(txin)
            txinScripts.append(txin_scriptPubKey)

        # vouts
        # how do I specify an asset output? this doesn't seem right for that:
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG OP_RVN_ASSET 0c72766e6f075341544f524921 75
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG 0c(OP_RVN_ASSET) 72766e(rvn) 74(t) 07(length) 5341544f524921(SATORI) 00e1f50500000000(padded little endian hex of 100000000) 75(drop)
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG 0c(OP_RVN_ASSET) 72766e(rvn) 74(t) 07(length) 5341544f524921(SATORI) 00e1f50500000000(padded little endian hex of 100000000) 75(drop)
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG 0c(OP_RVN_ASSET) 14(20 bytes length of asset information) 657672(evr) 74(t) 07(length of asset name) 5341544f524921(SATORI is asset name) 00e1f50500000000(padded little endian hex of 100000000) 75(drop)
        #         OP_DUP  OP_HASH160 3d5143a9336eaf44990a0b4249fcb823d70de52c OP_EQUALVERIFY OP_CHECKSIG 0c1465767274075341544f52492100e1f5050000000075
        # CScript([OP_DUP, OP_HASH160, Hash160(self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG ])
        # CScript([OP_DUP, OP_HASH160, Hash160(self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG OP_EVR_ASSET 0c ])
        assetInfoLen = '14'
        evr = '657672'
        t = '74'
        assetNameLen = '07'
        assetName = '5341544f524921'
        drop = '75'
        txins = []
        txinScripts = []
        txouts = []
        for address, amount in amountByAddress.items():
            # for asset transfer...? perfect?
            #   >>> Hash160(CRavencoinAddress(address).to_scriptPubKey())
            #   b'\xc2\x0e\xdf\x8cG\xd7\x8d\xac\x052\x03\xddC<0\xdd\x00\x91\xd9\x19'
            #   >>> Hash160(CRavencoinAddress(address))
            #   b'!\x8d"6\xcf\xe8\xf6W4\x830\x85Y\x06\x01J\x82\xc4\x87p' <- looks like what we get with self.pubkey.encode()
            # https://ravencoin.org/assets/
            # https://rvn.cryptoscope.io/api/getrawtransaction/?txid=bae95f349f15effe42e75134ee7f4560f53462ddc19c47efdd03f85ef4ab8f40&decode=1
            sats = transactionUtils.asSats(amount*COIN)
            txout = CMutableTxOut(
                0,
                CScript([
                    OP_DUP, OP_HASH160,
                    transactionUtils.addressToH160Bytes(address),
                    OP_EQUALVERIFY, OP_CHECKSIG, OP_EVR_ASSET,
                    bytes.fromhex(
                        evr + t + assetNameLen + assetName +
                        transactionUtils.padHexStringTo8Bytes(
                            transactionUtils.intToLittleEndianHex(
                                sats))),
                    OP_DROP]))
            txouts.append(txout)
        # change
        assetChange = gatheredSatori - satoriSats
        baseChange = gatheredCurrency - transactionUtils.estimatedFee(
            inputCount=len(gatheredSatoriUnspents) +
            len(gatheredCurrencyUnspents),
            outputCount=len(amountByAddress) + 2)
        txouts.append(
            CMutableTxOut(assetChange, self.address.to_scriptPubKey()))
        txouts.append(
            CMutableTxOut(baseChange, self.address.to_scriptPubKey()))
        # create transaction
        tx = CMutableTransaction(txins, txouts)
        for i, (txin, txin_scriptPubKey) in enumerate(zip(txins, txinScripts)):
            sighash = SignatureHash(txin_scriptPubKey, tx, i, SIGHASH_ALL)
            sig = self.privateKey.sign(sighash) + bytes([SIGHASH_ALL])
            txin.scriptSig = CScript([sig, self.privateKey.pub])
            VerifyScript(txin.scriptSig, txin_scriptPubKey,
                         tx, i, (SCRIPT_VERIFY_P2SH,))

        txToBroadcast = b2x(tx.serialize())
        print(txToBroadcast)
        # in theory we can send the serialized tx to the blockchain through electrumx
        if self.conn.connected():
            self.conn.broadcast(txToBroadcast)
        else:
            # this is dumb, fix it.
            x = Evrmore(self.address, self.scripthash, [
                'moontree.com:50022',  # mainnet ssl evr
                'electrum1-mainnet.evrmorecoin.org:50002',  # ssl
                'electrum2-mainnet.evrmorecoin.org:50002',  # ssl
            ])
            self.conn = x
            x.broadcast(b2x(tx.serialize()))

        # add all inputs and outputs to transaction
        # ?? txbuilder
        # ?? see python-evrmorelib examples
        # sign all inputs
        # ?? see python-evrmorelib
        # ?? if asset input use (get the self.assetVouts corresponding to the
        # ?? unspent).vout.scriptPubKey.hex.hexBytes
        # send
        # ?? use blockchain.transaction.broadcast raw_tx put function in
        # ?? Ravencoin object since that's our connection object

    def sign(self, message: str):
        return evrmore.signMessage(self._privateKeyObj, message)

    def verify(self, message: str, sig: bytes):
        return evrmore.verify(address=self.address, message=message, signature=sig)
