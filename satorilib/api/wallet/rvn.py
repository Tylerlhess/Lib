from ravencoin import SelectParams
from ravencoin.wallet import P2PKHRavencoinAddress, CRavencoinSecret
from ravencoin.wallet import CRavencoinAddress, CRavencoinSecret
from ravencoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from ravencoin.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, OP_RVN_ASSET, OP_DROP
from ravencoin.core import b2x, lx, COIN, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from satoriwallet import ElectrumXAPI
from satoriwallet import ravencoin
from satoriwallet import TxUtils, AssetTransaction
from satorilib.api.wallet.wallet import Wallet


class RavencoinWallet(Wallet):

    def __init__(self, walletPath, temporary=False):
        super().__init__(walletPath, temporary)
        self.electrumx = ElectrumXAPI(
            chain=self.chain,
            address=self.address,
            scripthash=self.scripthash,
            servers=[
                'moontree.com:50002',
                # 'rvn4lyfe.com:50002', running 1.12  {"jsonrpc":"2.0","error":{"code":-32601,"message":"unknown method \"blockchain.scripthash.get_asset_balance\""},"id":1705041163840}
                # 'ravennode-01.beep.pw:50002', dead
                # 'ravennode-02.beep.pw:50002', dead
                # 'electrum-rvn.dnsalias.net:50002', dead
            ])

    @property
    def symbol(self) -> str:
        return 'rvn'

    @property
    def chain(self) -> str:
        return 'Ravencoin'

    @property
    def satoriOriginalTxHash(self) -> str:
        return 'a015f44b866565c832022cab0dec94ce0b8e568dbe7c88dce179f9616f7db7e3'

    def _generatePrivateKey(self):
        SelectParams('mainnet')
        return CRavencoinSecret.from_secret_bytes(self._entropy)

    def _generateAddress(self):
        return P2PKHRavencoinAddress.from_pubkey(self._privateKeyObj.pub)

    def sign(self, message: str):
        return ravencoin.signMessage(self._privateKeyObj, message)

    def verify(self, message: str, sig: bytes):
        return ravencoin.verify(address=self.address, message=message, signature=sig)

    def _compileInputs(
        self,
        gatheredCurrencyUnspents: list = None,
        gatheredSatoriUnspents: list = None,
    ) -> tuple[list, list]:
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

    def _compileSatoriOutputs(self, amountByAddress: dict[str, float] = None) -> list:
        txouts = []
        for address, amount in amountByAddress.items():
            sats = TxUtils.asSats(amount*COIN)
            txout = CMutableTxOut(
                0,
                CScript([
                    OP_DUP, OP_HASH160,
                    # we might have to use this everywhere, idk.
                    TxUtils.addressToH160Bytes(address),
                    OP_EQUALVERIFY, OP_CHECKSIG, OP_RVN_ASSET,
                    bytes.fromhex(
                        AssetTransaction.satoriHex(self.symbol) +
                        TxUtils.padHexStringTo8Bytes(
                            TxUtils.intToLittleEndianHex(
                                sats))),
                    OP_DROP]))
            txouts.append(txout)
        return txouts

    def _compileCurrencyOutputs(self, currencySats: int, address: str) -> list[CMutableTxOut]:
        return [CMutableTxOut(currencySats, CRavencoinAddress(address).to_scriptPubKey())]

    def _compileSatoriChangeOutputs(
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

    def _compileCurrencyChangeOutputs(
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

    def _createTransaction(self, txins: list, txinScripts: list, txouts: list) -> CMutableTransaction:
        tx = CMutableTransaction(txins, txouts)
        for i, (txin, txin_scriptPubKey) in enumerate(zip(txins, txinScripts)):
            sighash = SignatureHash(txin_scriptPubKey, tx, i, SIGHASH_ALL)
            sig = self.privateKey.sign(sighash) + bytes([SIGHASH_ALL])
            txin.scriptSig = CScript([sig, self.privateKey.pub])
            VerifyScript(txin.scriptSig, txin_scriptPubKey,
                         tx, i, (SCRIPT_VERIFY_P2SH,))
        return tx

    def _txToHex(self, tx: CMutableTransaction) -> str:
        return b2x(tx.serialize())
