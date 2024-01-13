from random import randrange
from evrmore import SelectParams
from evrmore.wallet import P2PKHEvrmoreAddress, CEvrmoreSecret
from satoriwallet import Evrmore
from satoriwallet import evrmore
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
        self.base = x.evr
        self.transactionHistory = x.transactionHistory
        self.transactions = x.transactions or []
        self.unspentEvr = x.unspentEvr
        self.unspentAssets = x.unspentAssets
        # self.baseVouts = x.evrVouts
        # self.assetVouts = x.assetVouts

    # for neuron
    def ravenTransaction(self, amount: int, address: str):
        ''' creates a transaction to just send rvn '''
        return amount, address

    # for neuron
    def satoriTransaction(self, amount: int, address: str):
        ''' creates a transaction to send satori to one address '''
        return amount, address

    # for server
    def satoriDistribution(self, amountByAddress: dict):
        ''' creates a transaction '''

        def estimatedFee(inputCount: int = 0):
            # TODO: sub optimal, replace when we have a lot of users
            feeRate = 150000  # 0.00150000 rvn per item as simple over-estimate
            outputCount = len(amountByAddress)
            return (inputCount + outputCount) * feeRate

        assert (len(amountByAddress) > 0)
        # sum total amounts and other variables
        unspentEvr = [x for x in self.unspentEvr if x.get('value') > 0]
        unspentSatori = [x for x in self.unspentAssets if x.get(
            'name') == 'SATORI' and x.get('value') > 0]
        haveEvr = sum([x.get('value') for x in unspentEvr])
        haveSatori = sum([x.get('value') for x in unspentSatori])
        sendSatori = sum(amountByAddress.values())
        assert (haveSatori >= sendSatori > 0)
        assert (haveEvr >= 300000000)  # maintain minimum 3 RVN at all times

        # gather satori utxos at random
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
            randomUnspent = unspentEvr.pop(randrange(len(unspentEvr)))
            gatheredRvnUnspents.append(randomUnspent)
            gatheredRvn += randomUnspent.get('value')

        # see https://github.com/sphericale/python-evrmorelib/blob/master/examples/spend-p2pkh-txout.py
        from evrmore.wallet import CRavencoinAddress, CRavencoinSecret
        from evrmore.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
        from evrmore.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL
        from evrmore.core import b2x, lx, COIN, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160

        # how do I specify an asset output? this doesn't seem right for that:

        txins = []
        txinScripts = []
        for utxo in gatheredRvnUnspents:
            txin = CMutableTxIn(
                COutPoint(lx(utxo.get('tx_hash')), utxo.get('tx_pos')))
            txin_scriptPubKey = CScript([OP_DUP, OP_HASH160, Hash160(
                self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG])
            txins.append(txin)
            txinScripts.append(txin_scriptPubKey)
        for utxo in gatheredSatoriUnspents:
            txin = CMutableTxIn(
                COutPoint(lx(utxo.get('tx_hash')), utxo.get('tx_pos')))
            txin_scriptPubKey = CScript([OP_DUP, OP_HASH160, Hash160(
                self.publicKey.encode()), OP_EQUALVERIFY, OP_CHECKSIG])  # publicKey string to bytes            sighash = SignatureHash(txin_scriptPubKey, tx, 0, SIGHASH_ALL)
            txins.append(txin)
            txinScripts.append(txin_scriptPubKey)
        txouts = []
        amountOut = 0
        for address, amount in amountByAddress.items():
            txout = CMutableTxOut(
                amount*COIN,
                CRavencoinAddress(address).to_scriptPubKey())
            amountOut += amount*COIN
            txouts.append(txout)
        # change
        assetChange = gatheredSatori - sendSatori
        baseChange = gatheredRvn - amountOut
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
