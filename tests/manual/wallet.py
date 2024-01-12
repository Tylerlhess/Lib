from satorilib import logging
from satorineuron import config
from satorilib.api.disk import Disk
from satorilib.api.wallet import RavencoinWallet
from satorilib.api.wallet import EvrmoreWallet
Disk.setConfig(config)
x = EvrmoreWallet('/tmp/testwallet.yaml')
x()
a = RavencoinWallet('/tmp/testwalletRVN.yaml')
a()
