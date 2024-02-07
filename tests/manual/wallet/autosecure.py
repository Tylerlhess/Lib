
from satorilib.api.disk import Cache  # Disk
from satorilib.api.wallet import RavencoinWallet
from satorineuron import config
Cache.setConfig(config)
wallet = RavencoinWallet(
    config.walletPath('wallet.yaml'),
    reserve=0.01, isTestnet=True)
vault = RavencoinWallet(
    config.walletPath('vault.yaml'),
    reserve=0.01, isTestnet=True, password='123456789')
vault()
config.add('autosecure', data={
    wallet.address: vault.authPayload(
        asDict=True,
        challenge=vault.address + vault.getRaw()['publicKey'])})
wallet.autosecured()
vault.autosecured()
wallet.address
vault.address
wallet()
