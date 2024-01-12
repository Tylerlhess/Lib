from ravencoin.wallet import CRavencoinAddress, CRavencoinSecret
from ravencoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from ravencoin.core.script import CScript, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL
from ravencoin.core import b2x, lx, COIN, COutPoint, CMutableTxOut, CMutableTxIn, CMutableTransaction, Hash160
from satorilib import logging
from satorineuron import config
from satorilib.api.disk import Disk
from satorilib.api.wallet import RavencoinWallet
from satorilib.api.wallet import EvrmoreWallet
Disk.setConfig(config)
r = RavencoinWallet('/Satori/Neuron/wallet/wallet-value.yaml')
r()
x = EvrmoreWallet('/tmp/testwallet.yaml')
x()
a = RavencoinWallet('/tmp/testwalletRVN.yaml')
a()
