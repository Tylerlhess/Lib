from typing import Union
from ravencoin import SelectParams
from ravencoin.wallet import P2PKHRavencoinAddress, CRavencoinAddress, CRavencoinSecret
from ravencoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from ravencoin.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, OP_RVN_ASSET, OP_DROP, OP_RETURN
from ravencoin.core import b2x, lx, COIN, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from ravencoin.core.scripteval import EvalScriptError
from satoriwallet import ElectrumXAPI
from satoriwallet import ravencoin
from satoriwallet import TxUtils, AssetTransaction
from satorilib import logging
from satorilib.api.wallet.wallet import Wallet, TransactionFailure


class RavencoinWallet(Wallet):

    def __init__(self, walletPath: str, temporary: bool = False, reserve: float = .1):
        super().__init__(walletPath, temporary=temporary, reserve=reserve)

    def connect(self):
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
            txin = CMutableTxIn(COutPoint(lx(
                utxo.get('tx_hash')),
                utxo.get('tx_pos')))
            txin_scriptPubKey = CScript([
                OP_DUP,
                OP_HASH160,
                Hash160(self.publicKeyBytes),
                OP_EQUALVERIFY,
                OP_CHECKSIG])
            txins.append(txin)
            txinScripts.append(txin_scriptPubKey)
        # satori vins
        for utxo in (gatheredSatoriUnspents or []):
            txin = CMutableTxIn(COutPoint(lx(
                utxo.get('tx_hash')),
                utxo.get('tx_pos')))
            txin_scriptPubKey = CScript([
                OP_DUP,
                OP_HASH160,
                Hash160(self.publicKeyBytes),
                OP_EQUALVERIFY,
                OP_CHECKSIG,
                OP_RVN_ASSET,
                bytes.fromhex(
                    AssetTransaction.satoriHex(self.symbol) +
                    TxUtils.padHexStringTo8Bytes(
                        TxUtils.intToLittleEndianHex(
                            int(utxo.get('value'))))),
                OP_DROP,
            ])
            txins.append(txin)
            txinScripts.append(txin_scriptPubKey)
        return txins, txinScripts

    def _compileSatoriOutputs(self, amountByAddress: dict[str, float] = None) -> list:
        txouts = []
        for address, amount in amountByAddress.items():
            sats = TxUtils.asSats(amount)
            txout = CMutableTxOut(
                0,
                CScript([
                    OP_DUP, OP_HASH160,
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
        return [CMutableTxOut(
            currencySats,
            CRavencoinAddress(address).to_scriptPubKey()
        )]

    def _compileSatoriChangeOutput(
        self,
        satoriSats: int = 0,
        gatheredSatoriSats: int = 0,
    ) -> Union[CMutableTxOut, None]:
        satoriChange = gatheredSatoriSats - satoriSats
        if satoriChange > 0:
            return CMutableTxOut(
                0,
                CScript([
                    OP_DUP, OP_HASH160,
                    TxUtils.addressToH160Bytes(self.address),
                    OP_EQUALVERIFY, OP_CHECKSIG, OP_RVN_ASSET,
                    bytes.fromhex(
                        AssetTransaction.satoriHex(self.symbol) +
                        TxUtils.padHexStringTo8Bytes(
                            TxUtils.intToLittleEndianHex(
                                satoriChange))),
                    OP_DROP]))
        if satoriChange < 0:
            raise TransactionFailure('tx: not enough satori to send')
        return None

    def _compileCurrencyChangeOutput(
        self,
        currencySats: int = 0,
        gatheredCurrencySats: int = 0,
        inputCount: int = 0,
        outputCount: int = 0,
    ) -> Union[CMutableTxOut, None]:
        currencyChange = gatheredCurrencySats - currencySats - TxUtils.estimatedFee(
            inputCount=inputCount,
            outputCount=outputCount)
        if currencyChange > 0:
            return CMutableTxOut(
                currencyChange,
                self._addressObj.to_scriptPubKey())
        if currencyChange < 0:
            # go back and get more?
            raise TransactionFailure('tx: not enough currency to send')
        return None

    def _compileMemoOutput(self, memo: str) -> Union[CMutableTxOut, None]:
        if memo is not None and memo != '' and 4 < len(memo) < 80:
            return CMutableTxOut(
                0,
                CScript([
                    OP_RETURN,
                    # memo.encode().hex().encode() ->b'j\x086d656d6f' -> 3664363536643666 -> '6d656d6f'
                    # -> b'j\x04memo' -> 6d656d6f -> 'memo'
                    # bytes.fromhex(AssetTransaction.memoHex(memo))
                    # memo.encode().hex()  # ->expected a bytes-like object, str found str
                    # bytes([len(memo)]) + memo.encode()  # -> b'\x04memo' 046d656d6f
                    # '6d656d6f'.encode() # -> 3664363536643666 -> 6d656d6f
                    # 'some information'.encode()  # -> 736f6d6520696e666f726d6174696f6e -> 'some information'
                    # 'memomemo'.encode()  # -> 6d656d6f6d656d6f
                    # 'memom'.encode()  # ->6d656d6f6d
                    # 'memo'.encode()  # ->1869440365 # ?????? "hex":"6a046d656d6f"
                    # 'devs'.encode()  # ->1869440365 # ?????? "asm":"OP_RETURN 1937139044","hex":"6a0464657673"
                    # 'creators'.encode()# 63726561746f7273
                    # 'managers'.encode()  # 6d616e6167657273
                    # 'predictors'.encode()  # 707265646963746f7273
                    # 'relayers'.encode()  # 72656c6179657273
                    # 'relay'.encode()  # 72656c6179
                    # 'r'.encode()  # 114 ???
                    # it seems as though we can't do 4 or less probably because of something CScript is doing... idk why.
                    memo.encode()
                ]))
        return None

    def _createTransaction(self, txins: list, txinScripts: list, txouts: list) -> CMutableTransaction:
        tx = CMutableTransaction(txins, txouts)
        for i, (txin, txin_scriptPubKey) in enumerate(zip(txins, txinScripts)):
            sighash = SignatureHash(txin_scriptPubKey, tx, i, SIGHASH_ALL)
            sig = self._privateKeyObj.sign(sighash) + bytes([SIGHASH_ALL])
            txin.scriptSig = CScript([sig, self._privateKeyObj.pub])
            try:
                VerifyScript(txin.scriptSig, txin_scriptPubKey,
                             tx, i, (SCRIPT_VERIFY_P2SH,))
            except EvalScriptError as e:
                # python-ravencoinlib doesn't support OP_RVN_ASSET in txin_scriptPubKey
                if str(e) != 'EvalScript: unsupported opcode 0xc0':
                    raise EvalScriptError(e)
        return tx

    def _txToHex(self, tx: CMutableTransaction) -> str:
        return b2x(tx.serialize())
