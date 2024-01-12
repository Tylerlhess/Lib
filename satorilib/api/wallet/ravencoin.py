from random import randrange
from ravencoin import SelectParams
# import ravencoin.base58
from ravencoin.wallet import P2PKHRavencoinAddress, CRavencoinSecret
from satoriwallet import Ravencoin
from satoriwallet import ravencoin
from satorilib.api.wallet.wallet import Wallet


class RavencoinWallet(Wallet):

    def __init__(self, walletPath, temporary=False):
        walletPath = walletPath.replace('.yaml', '-rvn.yaml')
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
        self.baseVouts = x.rvnVouts
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

        txins = []
        for utxo in gatheredRvnUnspents:
            txin = CMutableTxIn(
                COutPoint(lx(utxo.get('tx_hash')), utxo.get('tx_pos')))
            txin_scriptPubKey = CScript([OP_DUP, OP_HASH160, Hash160(
                self.publicKey), OP_EQUALVERIFY, OP_CHECKSIG])
            sighash = SignatureHash(txin_scriptPubKey, tx, 0, SIGHASH_ALL)
            sig = seckey.sign(sighash) + bytes([SIGHASH_ALL])
            txin.scriptSig = CScript([sig, seckey.pub])
            txins.append(txin)
        for utxo in gatheredSatoriUnspents:
            txin = CMutableTxIn(
                COutPoint(lx(utxo.get('tx_hash')), utxo.get('tx_pos')))
            txin_scriptPubKey = CScript([OP_DUP, OP_HASH160, Hash160(
                self.publicKey), OP_EQUALVERIFY, OP_CHECKSIG])
            sighash = SignatureHash(txin_scriptPubKey, tx, 0, SIGHASH_ALL)
            sig = seckey.sign(sighash) + bytes([SIGHASH_ALL])
            txin.scriptSig = CScript([sig, seckey.pub])
            txins.append(txin)
        txouts = []
        for address, amount in amountByAddress.items():
            txout = CMutableTxOut(
                amount*COIN, CRavencoinAddress(address).to_scriptPubKey())
            txouts.append(txout)
        tx = CMutableTransaction(txins, txouts)
        # assumes 1 input, 1 output to verify?
        # VerifyScript(txin.scriptSig, txin_scriptPubKey, tx, 0, (SCRIPT_VERIFY_P2SH,))
        print(b2x(tx.serialize()))
        # in theory we can send the serialized tx to the blockchain through electrumx
        x = Ravencoin(self.address, self.scripthash, ['moontree.com:50002',])
        x.broadcast(b2x(tx.serialize()))

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
        return ravencoin.signMessage(self._privateKeyObj, message)

    def verify(self, message: str, sig: bytes):
        return ravencoin.verify(address=self.address, message=message, signature=sig)
