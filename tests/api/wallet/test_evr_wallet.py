
import unittest
# from unittest.mock import patch, MagicMock
from evrmore.wallet import CEvrmoreSecret, P2PKHEvrmoreAddress
from evrmore.core import CMutableTxOut, CScript
from evrmore.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, OP_EVR_ASSET, OP_DROP
from satorilib.api.wallet.evr import EvrmoreWallet
from satorilib.api.wallet.wallet import  TransactionFailure
from satoriwallet import TxUtils, AssetTransaction
from satorilib.api.disk.wallet import WalletApi

class TestEvrmoreWallet(unittest.TestCase):

    # @patch('satorilib.api.wallet.wallet.WalletApi.config', new_callable=MagicMock)
    # @patch('satorilib.api.wallet.wallet.Wallet.loadRaw', return_value=True)
    def setUp(self):
        # Mock the configuration to return a valid dictionary
        # mock_config.get.return_value = {'some_key': 'some_value'}
        WalletApi.config = {
            '/Satori/Lib/tests/api/wallet/artifacts/wallet.yaml': {
                'entropy': 'rJVnqSyzmJl6Hw5RcWLES8/cZHy0bmHeKdXV1IvYAD4=',
                'address': 'EXybyoeyn7uHWArTJA1iVddBKcAeF99kjb',
                'privateKey': 'L31C2MCzXQuKinRft6NeLBr4HjZ65hgvnLtRiioDMtfzLgEFXfxc',
                'publicKey': '027aebc5ad86be6f9c0005809d1431388f09c3a2d0708f40f5f22ec82b4aaac4ae',
                'scripthash': '01527fc8ceba87a4af978ae157192cf1c6bb0242c6a390a10c65c2e1fcf1c739',
                'words': 'prosper private tumble floor define erosion trick tide fabric mention rain nurse worry cram version miss gift vanish install produce emerge ugly abstract surround'
            }
        }
        self.wallet = EvrmoreWallet(walletPath='/Satori/Lib/tests/api/wallet/artifacts/wallet.yaml')
        self.wallet_values = {
            'entropy': 'rJVnqSyzmJl6Hw5RcWLES8/cZHy0bmHeKdXV1IvYAD4=',
            'address': 'EXybyoeyn7uHWArTJA1iVddBKcAeF99kjb',
            'privateKey': 'L31C2MCzXQuKinRft6NeLBr4HjZ65hgvnLtRiioDMtfzLgEFXfxc',
            'publicKey': '027aebc5ad86be6f9c0005809d1431388f09c3a2d0708f40f5f22ec82b4aaac4ae',
            'scripthash': '01527fc8ceba87a4af978ae157192cf1c6bb0242c6a390a10c65c2e1fcf1c739',
            'words': 'prosper private tumble floor define erosion trick tide fabric mention rain nurse worry cram version miss gift vanish install produce emerge ugly abstract surround'}
        self.vault = ''' TODO: an encrypted wallet '''
        self.vault_values = {}

    def test_symbol(self):
        self.assertEqual(self.wallet.symbol, 'evr')

    def test_chain(self):
        self.assertEqual(self.wallet.chain, 'Evrmore')

    def test_networkByte(self):
        self.assertEqual(self.wallet.networkByte, b'\x21')

    def test_networkByteP2PKH(self):
        self.assertEqual(self.wallet.networkByteP2PKH, b'\x21')

    def test_networkByteP2SH(self):
        self.assertEqual(self.wallet.networkByteP2SH, b'\x5c')

    def test_satoriOriginalTxHash(self):
        self.assertEqual(self.wallet.satoriOriginalTxHash, 'df745a3ee1050a9557c3b449df87bdd8942980dff365f7f5a93bc10cb1080188')

    def test_generatePrivateKey(self):
        private_key = self.wallet._generatePrivateKey()
        self.assertIsInstance(private_key, CEvrmoreSecret)
        wif = str(private_key)
        self.assertEqual(len(private_key), 33)
        self.assertIn(wif[0], ['L', 'K'])

    def test_generateAddress(self):
        address = self.wallet._generateAddress()
        self.assertIsInstance(address, P2PKHEvrmoreAddress)
        wif = str(address)
        self.assertEqual(len(address), 20)
        self.assertEqual(wif[0], 'E')

    def test_generateAddress_static(self):
        result = self.wallet.generateAddress(self.wallet_values["publicKey"])
        self.assertEqual(result, self.wallet_values["address"])
  
    def test_generateScriptPubKeyFromAddress(self):
        script_pubkey = self.wallet._generateScriptPubKeyFromAddress(self.wallet_values["address"])
        self.assertIsInstance(script_pubkey, CScript)
        script_ops = list(script_pubkey)
        # Check the structure of the script
        self.assertEqual(script_ops[0], OP_DUP)
        self.assertEqual(script_ops[1], OP_HASH160)
        self.assertEqual(len(script_ops[2]), 20)  # 20-byte pubkey hash
        self.assertEqual(script_ops[3], OP_EQUALVERIFY)
        self.assertEqual(script_ops[4], OP_CHECKSIG)
        # Verify the script starts with the expected OP_DUP and OP_HASH160 bytes
        self.assertTrue(bytes(script_pubkey).startswith(b'\x76\xa9\x14'))
        
        # Verify the script ends with the expected OP_EQUALVERIFY and OP_CHECKSIG bytes
        self.assertTrue(bytes(script_pubkey).endswith(b'\x88\xac'))
        # self.assertEqual(script_pubkey, b'v\xa9\x14\xa2\x97\x1b\x8f\xcb\x9d\xf5I\x00#\xdd\x10qcL\x9d\xc9\xd6\x86I\x88\xac')

    def test_sign(self):
        result = self.wallet.sign(self.wallet_values["words"])
        self.assertIsNotNone(result)

    def test_verify(self):
        result = self.wallet.verify(self.wallet_values["words"],self.wallet.sign(self.wallet_values["words"]))
        self.assertTrue(result)

    def test_checkSatoriValue(self):
        Script =CScript([
                    OP_DUP, OP_HASH160,
                    TxUtils.addressToH160Bytes(self.wallet_values["address"]),
                    OP_EQUALVERIFY, OP_CHECKSIG, OP_EVR_ASSET,
                    bytes.fromhex(
                        AssetTransaction.satoriHex(self.wallet.symbol) +
                        TxUtils.padHexStringTo8Bytes(
                            TxUtils.intToLittleEndianHex(1))),
                    OP_DROP])
        txt_out = CMutableTxOut(0,Script)
        result = self.wallet._checkSatoriValue(txt_out)
        self.assertTrue(result)



    def test_compileSatoriChangeOutput(self):
        result = self.wallet._compileSatoriChangeOutput(100, 150)
        self.assertIsInstance(result, CMutableTxOut)
        self.assertEqual(result.nValue, 0)
        self.assertIsInstance(result.scriptPubKey, CScript)
        
        # Verify script structure
        script = result.scriptPubKey
        self.assertEqual(script[0], OP_DUP)
        self.assertEqual(script[1], OP_HASH160)
        self.assertEqual(script[23], OP_EQUALVERIFY)
        self.assertEqual(script[24], OP_CHECKSIG)
        self.assertEqual(script[25], OP_EVR_ASSET)
        self.assertEqual(script[-1], OP_DROP)


        # Test case 4: Large change value
        result = self.wallet._compileSatoriChangeOutput(1000000, 2000000)
        self.assertIsInstance(result, CMutableTxOut)
        self.assertEqual(result.nValue, 0)

        # Test case 5: Minimum change value
        result = self.wallet._compileSatoriChangeOutput(100, 101)
        self.assertIsInstance(result, CMutableTxOut)
        self.assertEqual(result.nValue, 0)


    def test_compileSatoriChangeOutput_no_change(self):
        result = self.wallet._compileSatoriChangeOutput(100, 100)
        self.assertIsNone(result)

    def test_compileSatoriChangeOutput_negative_change(self):
        with self.assertRaises(TransactionFailure):
            self.wallet._compileSatoriChangeOutput(200, 100)

if __name__ == '__main__':
    unittest.main()
