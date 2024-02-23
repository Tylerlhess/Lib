from typing import Union
from evrmore import SelectParams
from evrmore.wallet import P2PKHEvrmoreAddress, CEvrmoreAddress, CEvrmoreSecret
from evrmore.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from evrmore.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, OP_EVR_ASSET, OP_DROP, OP_RETURN, SIGHASH_ANYONECANPAY
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
    def networkByte(self) -> bytes:
        return self.networkByteP2PKH

    @property
    def networkByteP2PKH(self) -> bytes:
        # evrmore.params.BASE58_PREFIXES['PUBKEY_ADDR']
        # BASE58_PREFIXES = {'PUBKEY_ADDR': 111,
        #               'SCRIPT_ADDR': 196,
        #               'SECRET_KEY': 239}
        # RVN = return b'\x3c'  # b'0x3c'
        return (111).to_bytes(1, 'big')

    @property
    def networkByteP2SH(self) -> bytes:
        return (196).to_bytes(1, 'big')

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

    @staticmethod
    def generateAddress(pubkey: Union[str, None] = None):
        return P2PKHEvrmoreAddress.from_pubkey(pubkey)

    def _generateScriptPubKeyFromAddress(self, address: str):
        return CEvrmoreAddress(address).to_scriptPubKey()

    def sign(self, message: str):
        return evrmore.signMessage(self._privateKeyObj, message)

    def verify(self, message: str, sig: bytes, address: Union[str, None] = None):
        return evrmore.verify(address=address or self.address, message=message, signature=sig)

    def _checkSatoriValue(self, output: CMutableTxOut) -> bool:
        ''' 
        returns true if the output is a satori output of self.satoriFee
        '''
        nextOne = False
        for i, x in enumerate(s.scriptPubKey):
            if nextOne:
                # doesn't padd with 0s at the end
                # b'rvnt\x06SATORI\x00\xe1\xf5\x05'
                # b'rvnt\x06SATORI\x00\xe1\xf5\x05\x00\x00\x00\x00'
                return x.startswith(bytes.fromhex(
                    AssetTransaction.satoriHex(self.symbol) +
                    TxUtils.padHexStringTo8Bytes(
                        TxUtils.intToLittleEndianHex(
                            TxUtils.toSats(self.satoriFee)))))
            if x == OP_RVN_ASSET:
                nextOne = True
        return False

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
        scriptPubKey: CScript = None,
        returnSats: bool = False,
    ) -> Union[CMutableTxOut, None, tuple[CMutableTxOut, int]]:
        currencyChange = gatheredCurrencySats - currencySats - TxUtils.estimatedFee(
            inputCount=inputCount,
            outputCount=outputCount)
        if currencyChange > 0:
            txout = CMutableTxOut(
                currencyChange,
                scriptPubKey or self._addressObj.to_scriptPubKey())
            if returnSats:
                return txout, currencyChange
            return txout
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
        for i, (txin, txinScriptPubKey) in enumerate(zip(txins, txinScripts)):
            self._signInput(
                tx=tx,
                i=i,
                txin=txin,
                txinScriptPubKey=txinScriptPubKey,
                sighashFlag=SIGHASH_ALL)
        return tx

    def _createPartialOriginatorSimple(self, txins: list, txinScripts: list, txouts: list) -> CMutableTransaction:
        ''' simple version SIGHASH_ANYONECANPAY | SIGHASH_ALL '''
        tx = CMutableTransaction(txins, txouts)
        for i, (txin, txinScriptPubKey) in enumerate(zip(txins, txinScripts)):
            self._signInput(
                tx=tx,
                i=i,
                txin=txin,
                txinScriptPubKey=txinScriptPubKey,
                sighashFlag=SIGHASH_ANYONECANPAY | SIGHASH_ALL)
        return tx

    def _createPartialCompleterSimple(self, txins: list, txinScripts: list, tx: CMutableTransaction) -> CMutableTransaction:
        '''
        simple version SIGHASH_ANYONECANPAY | SIGHASH_ALL
        just adds an input for the RVN fee and signs it
        '''
        # todo, verify the last two outputs at somepoint before this
        tx.vin.extend(txins)
        startIndex = len(tx.vin) - len(txins)
        for i, (txin, txinScriptPubKey) in (
            enumerate(zip(tx.vin[startIndex:], txinScripts), start=startIndex)
        ):
            self._signInput(
                tx=tx,
                i=i,
                txin=txin,
                txinScriptPubKey=txinScriptPubKey,
                sighashFlag=SIGHASH_ANYONECANPAY | SIGHASH_ALL)
        return tx

    def _signInput(
        self,
        tx: CMutableTransaction,
        i: int,
        txin: CMutableTxIn,
        txinScriptPubKey: CScript,
        sighashFlag: int
    ):
        sighash = SignatureHash(txinScriptPubKey, tx, i, sighashFlag)
        sig = self._privateKeyObj.sign(sighash) + bytes([sighashFlag])
        txin.scriptSig = CScript([sig, self._privateKeyObj.pub])
        try:
            VerifyScript(txin.scriptSig, txinScriptPubKey,
                         tx, i, (SCRIPT_VERIFY_P2SH,))
        except EvalScriptError as e:
            # python-ravencoinlib doesn't support OP_RVN_ASSET in txinScriptPubKey
            if str(e) != 'EvalScript: unsupported opcode 0xc0':
                raise EvalScriptError(e)

    # def _createPartialOriginator(self, txins: list, txinScripts: list, txouts: list) -> CMutableTransaction:
    #    ''' not completed - complex version SIGHASH_ANYONECANPAY | SIGHASH_SINGLE '''
    #    tx = CMutableTransaction(txins, txouts)
    #    for i, (txin, txin_scriptPubKey) in enumerate(zip(tx.vin, txinScripts)):
    #        # Use SIGHASH_SINGLE for the originator's inputs
    #        sighash_type = SIGHASH_SINGLE
    #        sighash = SignatureHash(txin_scriptPubKey, tx, i, sighash_type)
    #        sig = self._privateKeyObj.sign(sighash) + bytes([sighash_type])
    #        txin.scriptSig = CScript([sig, self._privateKeyObj.pub])
    #    return tx
    #
    # def _createPartialCompleter(self, txins: list, txinScripts: list, txouts: list, tx: CMutableTransaction) -> CMutableTransaction:
    #    ''' not completed '''
    #    tx.vin.extend(txins)  # Add new inputs
    #    tx.vout.extend(txouts)  # Add new outputs
    #    # Sign new inputs with SIGHASH_ANYONECANPAY and possibly SIGHASH_SINGLE
    #    # Assuming the completer's inputs start from len(tx.vin) - len(txins)
    #    startIndex = len(tx.vin) - len(txins)
    #    for i, (txin, txin_scriptPubKey) in enumerate(zip(tx.vin[startIndex:], txinScripts), start=startIndex):
    #        sighash_type = SIGHASH_ANYONECANPAY  # Or SIGHASH_ANYONECANPAY | SIGHASH_SINGLE
    #        sighash = SignatureHash(txin_scriptPubKey, tx, i, sighash_type)
    #        sig = self._privateKeyObj.sign(sighash) + bytes([sighash_type])
    #        txin.scriptSig = CScript([sig, self._privateKeyObj.pub])
    #    return tx

    def _txToHex(self, tx: CMutableTransaction) -> str:
        return b2x(tx.serialize())

    def _serialize(self, tx: CMutableTransaction) -> bytes:
        return tx.serialize()

    def _deserialize(self, serialTx: bytes) -> CMutableTransaction:
        return CMutableTransaction.deserialize(serialTx)
