import os
from evrmore.wallet import P2PKHEvrmoreAddress, CEvrmoreSecret
from evrmore import SelectParams


def _generateEntropy():
    return os.urandom(32)


def _generatePrivateKey(_entropy):
    return CEvrmoreSecret.from_secret_bytes(_entropy)


def _generateAddress(_privateKeyObj):
    return P2PKHEvrmoreAddress.from_pubkey(_privateKeyObj.pub)


def run(condition: callable):
    SelectParams('mainnet')
    while True:
        entropy = _generateEntropy()
        address = str(_generateAddress(
            _generatePrivateKey(entropy)))
        if condition(address):
            print(entropy)
            print(entropy.hex())
            print(address)


def basicCondition(address: str) -> bool:
    return address.lower().startswith("Evrmore")


def caseCondition(address: str) -> bool:
    return address.startswith("ESatori")


def caseConditionVariable(value: str) -> callable:
    def caseCondition(address: str) -> bool:
        return address.startswith(f'E{value}')
    return caseCondition


run(caseConditionVariable('Devs'))
