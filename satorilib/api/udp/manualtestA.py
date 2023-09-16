# control + k + shift + s
# docker run --rm -it --name satorineuron -v c:\repos\Satori\Neuron:/Satori/Neuron -v c:\repos\Satori\Lib:/Satori/Lib -v c:\repos\Satori\Wallet:/Satori/Wallet -v c:\repos\Satori\Engine:/Satori/Engine satorinet/satorineuron:v1 bash
# cd satorilib/api/udp & python
# client A:
from manager import UDPManager
from satorilib.api.udp.manager import UDPManager
m = UDPManager(streamIds=None, signature='clientASig', key='clientAKey')

# they should both connect to the rendezvous server
# then they should both connect to each other.
