"""GS topologies

SimpleTopo:

  host (AS) 
    --- switch (rounter at customer's home) --- (internet connection cust) 
    --- switch(internet connection AP) --- switch (router at ARC) 
  --- host (ARC)

"""

from mininet.topo import Topo
from mininet.cli import CLI

class SimpleTopo( Topo ):
    def build( self ):

        # Add hosts and switches
        alarm_system = self.addHost( 'as' )
        alarm_receiving_centre = self.addHost( 'arc' )
        
        leftSwitch = self.addSwitch( 's1' )
        ispSwitch = self.addSwitch( 's2' )
        rightSwitch = self.addSwitch( 's3' )

        # Add links

        # customer has 1 Gigabit Ethernet (GbE) connection to his router 
        linkopts = {'bw':1000, 'delay':'1ms' }
        self.addLink( alarm_system, leftSwitch )

        # customer has VDSL 100 (100 MBit Download, 40 MBit Upload) 
        linkopts = {'bw':40, 'delay':'1ms' }
        self.addLink( leftSwitch, ispSwitch )
        
        # alarm provider has SDSL 100 (100 MBit Down- /Upload)
        linkopts = {'bw':100, 'delay':'1ms' }
        self.addLink( ispSwitch, rightSwitch )

        # alarm provider has 1 GbE connection to his router
        linkopts = {'bw':1000, 'delay':'0.3ms', 'loss':16 }
        self.addLink( rightSwitch, alarm_receiving_centre )


def startars(self):
    """Starts the ARS on the ARC host"""

    net = self.mn
    start_ARS(net)


def start_ARS(net):
    """Starts the ARS on the ARC host"""

    arc = net.get('arc')
    arc.cmd('cd ../')
    print("ARC: Current Working Directory:")
    arc.cmdPrint('pwd')
    arc.cmd('alias python=venv/bin/python')
    print("ARC: Starting ARS.")
    arc.cmd('python ARS_simulation.py > mininet/ars.out &')


def LocustTest(net):
    
    start_ARS(net)
    
    # net.start()
    CLI(net)
    # net.stop()

topos = { 'simple-topo': ( lambda: SimpleTopo() ) }
tests = { 'LocustTest': LocustTest }

CLI.do_startars = startars
