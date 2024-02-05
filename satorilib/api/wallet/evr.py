from typing import Union
from evrmore import SelectParams
from evrmore.wallet import P2PKHEvrmoreAddress, CEvrmoreAddress, CEvrmoreSecret
from evrmore.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from evrmore.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, OP_EVR_ASSET, OP_DROP, OP_RETURN
from evrmore.core import b2x, lx, COIN, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from evrmore.core.scripteval import EvalScriptError
from satoriwallet import ElectrumXAPI
from satoriwallet import evrmore
from satoriwallet import TxUtils, AssetTransaction
from satorilib import logging
from satorilib.api.wallet.wallet import Wallet, TransactionFailure


class EvrmoreWallet(Wallet):

    def __init__(
        self,
        walletPath: str,
        temporary: bool = False,
        reserve: float = .1,
        isTestnet: bool = False,
        password: Union[str, None] = None,
    ):
        super().__init__(
            walletPath,
            temporary=temporary,
            reserve=reserve,
            isTestnet=isTestnet,
            password=password)

    def connect(self):
        self.electrumx = ElectrumXAPI(
            chain=self.chain,
            address=self.address,
            scripthash=self.scripthash,
            servers=[
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

    @property
    def symbol(self) -> str:
        return 'evr'

    @property
    def chain(self) -> str:
        return 'Evrmore'

    @property
    def satoriOriginalTxHash(self) -> str:
        # SATORI/TEST 15dd33886452c02d58b500903441b81128ef0d21dd22502aa684c002b37880fe
        return 'df745a3ee1050a9557c3b449df87bdd8942980dff365f7f5a93bc10cb1080188'

    def _generatePrivateKey(self):
        SelectParams('mainnet')
        return CEvrmoreSecret.from_secret_bytes(self._entropy)

    def _generateAddress(self):
        return P2PKHEvrmoreAddress.from_pubkey(self._privateKeyObj.pub)

    def sign(self, message: str):
        return evrmore.signMessage(self._privateKeyObj, message)

    def verify(self, message: str, sig: bytes):
        return evrmore.verify(address=self.address, message=message, signature=sig)

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
                OP_EVR_ASSET,
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
                    OP_EQUALVERIFY, OP_CHECKSIG, OP_EVR_ASSET,
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
            CEvrmoreAddress(address).to_scriptPubKey()
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
                    OP_EQUALVERIFY, OP_CHECKSIG, OP_EVR_ASSET,
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
                self._addressObj.to_scriptPubKey()
            )
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
                    # it seems as though we can't do 4 or less
                    # probably because of something CScript is doing... idk why.
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
                # python-evrmorelib doesn't support OP_RVN_ASSET in txin_scriptPubKey
                if e != 'unsupported opcode 0xc0':
                    raise EvalScriptError(e)
        return tx

    def _txToHex(self, tx: CMutableTransaction) -> str:
        return b2x(tx.serialize())
