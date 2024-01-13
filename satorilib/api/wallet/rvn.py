from random import randrange
from ravencoin import SelectParams
# import ravencoin.base58
from ravencoin.wallet import P2PKHRavencoinAddress, CRavencoinSecret
from satoriwallet import Ravencoin
from satoriwallet import ravencoin
from satorilib.api.wallet.wallet import Wallet


class RavencoinWallet(Wallet):

    def __init__(self, walletPath, temporary=False):
        super().__init__(walletPath, temporary)

    def __repr__(self):
        return (
            'RavencoinWallet('
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
        return 'rvn'

    def _generatePrivateKey(self):
        SelectParams('mainnet')
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

    def get(self, allWalletInfo=False):
        ''' gets data from the blockchain, saves to attributes '''
        # x = Ravencoin(self.address, self.scripthash, config.electrumxServers())
        # todo: this list of servers should be parameterized from configuration
        x = Ravencoin(self.address, self.scripthash, [
            'moontree.com:50002',
            # 'rvn4lyfe.com:50002', running 1.12  {"jsonrpc":"2.0","error":{"code":-32601,"message":"unknown method \"blockchain.scripthash.get_asset_balance\""},"id":1705041163840}
            # 'ravennode-01.beep.pw:50002', dead
            # 'ravennode-02.beep.pw:50002', dead
            # 'electrum-rvn.dnsalias.net:50002', dead
        ])
        # todo:
        # on connect ask for peers, add each to our list of electrumxServers
        # if unable to connect, remove that server from our list
        x.get(allWalletInfo)
        self.conn = x
        self.balance = x.balance
        self.stats = x.stats
        self.banner = x.banner
        self.base = x.rvn
        self.transactionHistory = x.transactionHistory
        self.transactions = x.transactions or []
        self.unspentRvn = x.unspentRvn
        self.unspentAssets = x.unspentAssets
        # self.baseVouts = x.rvnVouts
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
        unspentRvn = [x for x in self.unspentRvn if x.get('value') > 0]
        unspentSatori = [x for x in self.unspentAssets if x.get(
            'name') == 'SATORI' and x.get('value') > 0]
        haveRvn = sum([x.get('value') for x in unspentRvn])
        haveSatori = sum([x.get('value') for x in unspentSatori])
        sendSatori = sum(amountByAddress.values())
        assert (haveSatori >= sendSatori > 0)
        assert (haveRvn >= 300000000)  # maintain minimum 3 RVN at all times

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
            randomUnspent = unspentRvn.pop(randrange(len(unspentRvn)))
            gatheredRvnUnspents.append(randomUnspent)
            gatheredRvn += randomUnspent.get('value')

        # see https://github.com/sphericale/python-ravencoinlib/blob/master/examples/spend-p2pkh-txout.py
        from ravencoin.wallet import CRavencoinAddress, CRavencoinSecret
        from ravencoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
        from ravencoin.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL
        from ravencoin.core import b2x, lx, COIN, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160

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
            x = Ravencoin(self.address, self.scripthash,
                          ['moontree.com:50002'])
            self.conn = x
            x.broadcast(b2x(tx.serialize()))

    def sign(self, message: str):
        return ravencoin.signMessage(self._privateKeyObj, message)

    def verify(self, message: str, sig: bytes):
        return ravencoin.verify(address=self.address, message=message, signature=sig)
