import os
from evrmore.wallet import P2PKHEvrmoreAddress, CEvrmoreSecret
from evrmore import SelectParams


def _generateEntropy():
    return os.urandom(32)


def _generatePrivateKey(_entropy):
    return CEvrmoreSecret.from_secret_bytes(_entropy)


def _generateAddress(_privateKeyObj):
    return P2PKHEvrmoreAddress.from_pubkey(_privateKeyObj.pub)


def run():
    SelectParams('mainnet')
    while True:
        entropy = _generateEntropy()
        address = str(_generateAddress(
            _generatePrivateKey(entropy)))
        if address.lower().startswith("evrmore"):
            print(address, entropy)
            print(entropy.hex())
            return address


# run()
