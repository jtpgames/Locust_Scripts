import os
from time import sleep

from mininet.clean import cleanup
from mininet.net import Containernet, Mininet
from mininet.node import OVSSwitch, RemoteController, Controller
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.topo import Topo
from mininet.log import info, error, setLogLevel

setLogLevel('info')


class SDNSwitch(OVSSwitch):
    """Custom Switch() subclass that connects to remote controller"""

    def __init__(self, name, controller: RemoteController,
                 failMode='secure', datapath='kernel',
                 inband=False, protocols=None,
                 reconnectms=1000, stp=False, batch=False, **params):
        super().__init__(name, failMode, datapath, inband, protocols, reconnectms, stp, batch, **params)

        self._controller = controller

    def start(self, controllers):
        return OVSSwitch.start(self, [self._controller])


class TeaStoreTopo(Topo):
    """
        host (Customer)
        --- switch (rounter at customer's home) --- (ISP router cust)
        --- switch(ISP router AP) --- switch (router at ARC)
        --- host (ARC)
    """

    def build(self):
        info("*** Building topology\n")

        # Add hosts and switches
        locust_runner = self.addHost('h_runner')

        # c1 = RemoteController('c1', ip='127.0.0.1', port=6633)

        customerSwitch = self.addSwitch('s1')
        ispCustomerSwitch = self.addSwitch('s2')
        ispAPSwitch = self.addSwitch('s3')
        # self.apSwitch = self.addSwitch('s4', cls=SDNSwitch, controller=c1)
        self.apSwitch = self.addSwitch('s4')

        # Add links

        # Simulate production system
        # customer has 1 Gigabit Ethernet (GbE) connection to his router
        linkopts = {'bw': 1000, 'delay': '0.45ms'}
        self.addLink(locust_runner, customerSwitch, **linkopts)

        # customer has VDSL 100 (100 MBit Download, 30 MBit Upload)
        linkopts = {'bw': 30, 'delay': '2.4ms', 'jitter': '5.2ms'}
        self.addLink(customerSwitch, ispCustomerSwitch, **linkopts)

        # ISP Interlink (10 GbE connection)
        # 1 Gigabit is the maximum bandwidth allowed by mininet
        linkopts = {'bw': 1000, 'delay': '13.3ms', 'jitter': '3.15ms'}
        self.addLink(ispCustomerSwitch, ispAPSwitch, **linkopts)

        # alarm provider sadly does NOT have SDSL, rather LACP-based Uplinks: VDSL100, VDSL50 combined
        linkopts = {'bw': 50, 'delay': '7.97ms', 'jitter': '2.9ms'}
        self.addLink(ispAPSwitch, self.apSwitch, **linkopts)

    def add_tea_store_and_start_network(self, net: Containernet):
        info('*** Adding TeaStore docker containers\n')

        setLogLevel('debug')

        ################################################################################################################
        # Containernet ignores the CMD instruction the Dockerfile
        # (see https://github.com/containernet/containernet/wiki#container-requirements),
        # so we perform every command at this point, making sure that the last command is executed as a background task
        ################################################################################################################

        # teastore-kieker-rabbitmq Dockerfile
        # CMD  /apache-tomcat-8.5.24/bin/startup.sh
        #   && echo '<% response.sendRedirect("/logs/index"); %>' > /apache-tomcat-8.5.24/webapps/ROOT/index.jsp
        #   && rabbitmq-server
        # COMMAND according to docker ps
        # docker-entrypoint.sh /bin/sh -c '/apache-tomcat-8.5.24/bin/startup.sh
        #   && echo '<% response.sendRedirect(\"/logs/index\"); %>' > /apache-tomcat-8.5.24/webapps/ROOT/index.jsp
        #   && rabbitmq-server'

        start_tomcat = "/apache-tomcat-8.5.24/bin/startup.sh"
        create_redirect = r"""echo "<% response.sendRedirect(\"/logs/index\"); %>" > /apache-tomcat-8.5.24/webapps/ROOT/index.jsp"""
        start_rabbitmq = "rabbitmq-server &"
        teastore_kieker_cmd = f"docker-entrypoint.sh /bin/sh -c '{start_tomcat} && {create_redirect} && {start_rabbitmq}'"

        #############################################
        # teastore-base Dockerfile
        # CMD java -jar /usr/local/tomcat/bin/dockermemoryconfigurator.jar ${TOMCAT_HEAP_MEM_PERCENTAGE};
        #   /usr/local/tomcat/bin/start.sh
        #   && /usr/local/tomcat/bin/catalina.sh run
        # COMMAND according to docker ps
        # /bin/sh -c 'java -jar /usr/local/tomcat/bin/dockermemoryconfigurator.jar ${TOMCAT_HEAP_MEM_PERCENTAGE};
        #   /usr/local/tomcat/bin/start.sh
        #   && /usr/local/tomcat/bin/catalina.sh run'

        dockermemoryconfigurator = "java -jar /usr/local/tomcat/bin/dockermemoryconfigurator.jar ${TOMCAT_HEAP_MEM_PERCENTAGE};"
        start_local_tomcat = "/usr/local/tomcat/bin/start.sh"
        start_catalina = "/usr/local/tomcat/bin/catalina.sh run &"
        teastore_base_cmd = f"/bin/sh -c '{dockermemoryconfigurator} {start_local_tomcat} && {start_catalina}'"

        TEASTORE_KIEKER_STATIC_IP = "10.0.0.242"
        TEASTORE_REGISTRY_STATIC_IP = "10.0.0.243"
        TEASTORE_DB_STATIC_IP = "10.0.0.244"
        TEASTORE_PERSISTENCE_STATIC_IP = "10.0.0.245"
        TEASTORE_AUTH_STATIC_IP = "10.0.0.246"
        TEASTORE_IMAGE_STATIC_IP = "10.0.0.247"
        TEASTORE_RECOMMENDER_STATIC_IP = "10.0.0.248"
        TEASTORE_WEBUI_STATIC_IP = "10.0.0.250"

        #############################################
        # Kieker
        teastore_kieker = net.addDocker(
            'kieker',
            ip=TEASTORE_KIEKER_STATIC_IP,
            # we need 8081 -> 8080, but due to a bug, we specify it the other way around here:
            port_bindings={8080: 8081, 5672: 5672, 15672: 15672},
            network_mode='bridge',
            dimage="descartesresearch/teastore-kieker-rabbitmq",
        )
        #############################################
        # Registry
        teastore_registry = net.addDocker(
            'registry',
            ip=TEASTORE_REGISTRY_STATIC_IP,
            network_mode='bridge',
            dimage="descartesresearch/teastore-registry"
        )
        #############################################
        # Db
        teastore_db = net.addDocker(
            'db',
            ip=TEASTORE_DB_STATIC_IP,
            ports=[3306],
            port_bindings={3306: 3306},
            network_mode='bridge',
            dimage="descartesresearch/teastore-db",
            cpu_quota=100000,
            cpu_period=100000
        )
        #############################################
        # Persistence
        teastore_persistence = net.addDocker(
            'persist',
            ip=TEASTORE_PERSISTENCE_STATIC_IP,
            network_mode='bridge',
            dimage="descartesresearch/teastore-persistence",
            environment={"HOST_NAME": TEASTORE_PERSISTENCE_STATIC_IP,
                         "REGISTRY_HOST": TEASTORE_REGISTRY_STATIC_IP,
                         "RABBITMQ_HOST": TEASTORE_KIEKER_STATIC_IP,
                         "DB_HOST": TEASTORE_DB_STATIC_IP,
                         "DB_PORT": "3306"
                         },
            cpu_quota=100000,
            cpu_period=100000
        )
        #############################################
        ## Auth
        teastore_auth = net.addDocker(
            'auth',
            ip=TEASTORE_AUTH_STATIC_IP,
            network_mode='bridge',
            dimage="descartesresearch/teastore-auth",
            environment={"HOST_NAME": TEASTORE_AUTH_STATIC_IP,
                         "REGISTRY_HOST": TEASTORE_REGISTRY_STATIC_IP,
                         "RABBITMQ_HOST": TEASTORE_KIEKER_STATIC_IP,
                         },
            cpu_quota=100000,
            cpu_period=100000
        )
        #############################################
        # Image
        teastore_image = net.addDocker(
            'image',
            ip=TEASTORE_IMAGE_STATIC_IP,
            network_mode='bridge',
            dimage="descartesresearch/teastore-image",
            environment={"HOST_NAME": TEASTORE_IMAGE_STATIC_IP,
                         "REGISTRY_HOST": TEASTORE_REGISTRY_STATIC_IP,
                         "RABBITMQ_HOST": TEASTORE_KIEKER_STATIC_IP
                         },
            cpu_quota=100000,
            cpu_period=100000
        )
        #############################################
        # Recommender
        teastore_recommender = net.addDocker(
            'recommend',
            ip=TEASTORE_RECOMMENDER_STATIC_IP,
            network_mode='bridge',
            dimage="descartesresearch/teastore-recommender",
            environment={"HOST_NAME": TEASTORE_RECOMMENDER_STATIC_IP,
                         "REGISTRY_HOST": TEASTORE_REGISTRY_STATIC_IP,
                         "RABBITMQ_HOST": TEASTORE_KIEKER_STATIC_IP
                         },
            cpu_quota=100000,
            cpu_period=100000
        )
        #############################################
        # Web UI
        teastore_webui = net.addDocker(
            'webui',
            ip=TEASTORE_WEBUI_STATIC_IP,
            ports=[8080],
            port_bindings={8080: 8080},
            network_mode='bridge',
            dimage="descartesresearch/teastore-webui",
            environment={"HOST_NAME": TEASTORE_WEBUI_STATIC_IP,
                         "REGISTRY_HOST": TEASTORE_REGISTRY_STATIC_IP,
                         "RABBITMQ_HOST": TEASTORE_KIEKER_STATIC_IP
                         }
        )

        setLogLevel('info')

        info('*** Linking TeaStore docker containers\n')
        # alarm provider has 2 GbE connection to his router
        # 1 Gigabit is the maximum bandwidth allowed by mininet
        linkopts = {'bw': 1000, 'delay': '0.19ms', 'jitter': '0.06ms'}
        net.addLink(self.apSwitch, teastore_kieker, **linkopts)
        net.addLink(self.apSwitch, teastore_registry, **linkopts)
        net.addLink(self.apSwitch, teastore_db, **linkopts)
        net.addLink(self.apSwitch, teastore_persistence, **linkopts)
        net.addLink(self.apSwitch, teastore_auth, **linkopts)
        net.addLink(self.apSwitch, teastore_image, **linkopts)
        net.addLink(self.apSwitch, teastore_recommender, **linkopts)
        net.addLink(self.apSwitch, teastore_webui, **linkopts)

        net.configHosts()

        info('*** Starting network\n')
        net.start()

        h_runner = net.get('h_runner')
        h_runner.cmdPrint(f"export KIEKER_HOST={teastore_kieker.IP()}:8080")

        info('*** Starting TeaStore system\n')
        teastore_kieker.cmdPrint(teastore_kieker_cmd)
        teastore_registry.cmdPrint(teastore_base_cmd)
        teastore_db.cmdPrint("docker-entrypoint.sh mysqld &")
        info('*** Waiting 10 seconds for RabbitMQ, Registry and MariaDb to start\n')
        sleep(10)
        teastore_persistence.cmdPrint(teastore_base_cmd)
        teastore_auth.cmdPrint(teastore_base_cmd)
        teastore_image.cmdPrint(teastore_base_cmd)
        teastore_recommender.cmdPrint(teastore_base_cmd)
        teastore_webui.cmdPrint(teastore_base_cmd)
        info('*** Waiting 2 minutes for TeaStore to completely start\n')
        # sleep(2*60)
        sleep(10)
        info('*** Now, you can start the load test\n')


python_configured_hosts = []


def find_venv_directory():
    current_dir = os.getcwd()

    venv_dir = os.path.join(current_dir, 'venv')
    if os.path.isdir(venv_dir):
        return venv_dir

    while True:
        current_dir = os.path.dirname(current_dir)
        venv_dir = os.path.join(current_dir, 'venv')

        if os.path.isdir(venv_dir):
            return venv_dir

        folder_name = os.path.basename(current_dir)
        if folder_name == 'locust_scripts':
            # Do not search higher than the project folder
            break

    return None


def setup_python_on_host(host):
    if host in python_configured_hosts:
        return

    venv_dir = find_venv_directory()
    if venv_dir is None:
        raise RuntimeError("Could not find venv directory")

    host.cmd(f'cd {os.path.dirname(venv_dir)}')
    info("{}: Current Working Directory:\n".format(host))
    host.cmdPrint('pwd')
    host.cmd('source activate_venv.sh')
    host.cmdPrint('python --version')
    host.cmdPrint('python3 --version')
    host.cmdPrint('locust --version')

    python_configured_hosts.append(host)


def start_pox():
    # ./pox.py --verbose samples.pretty_log forwarding.l2_pairs ext.stats_per_second_collector

    pass


def start_teastore_loadtest(net: Mininet):
    h_runner = net.get('h_runner')
    webui = net.get('webui')

    setup_python_on_host(h_runner)

    cmd = f'./start_teastore_loadtest.sh --ip {webui.IP()}'
    info('*** Starting TeaStore Workload ...\n')
    info(f'{cmd}\n')

    cmd_output = h_runner.cmd("{} &> /dev/null &".format(cmd))
    info(cmd_output)


def test_topology(net: Mininet):
    info('*** Testing topology\n')

    net.ping()
    webui = net.get('webui')
    h_runner = net.get('h_runner')

    info('*** Testing TeaStore WebUI\n')
    h_runner.cmdPrint(f"curl {webui.IP()}:8080/tools.descartes.teastore.webui/status")
    h_runner.cmdPrint(f"curl {webui.IP()}:8080/tools.descartes.teastore.webui/")
    h_runner.cmdPrint(f"curl {webui.IP()}:8080/tools.descartes.teastore.webui/login")
    h_runner.cmdPrint(f"curl {webui.IP()}:8080/tools.descartes.teastore.webui/category?category=2&page=1")
    h_runner.cmdPrint(f"curl {webui.IP()}:8080/tools.descartes.teastore.webui/product?id=7")


def stop_workloads(self, args):
    """Stop all running workloads"""

    net = self.mn
    h_runner = net.get('h_runner')

    h_runner.cmd('killall locust')


try:
    teastore_topo = TeaStoreTopo()
    net = Containernet(topo=teastore_topo)
    teastore_topo.add_tea_store_and_start_network(net)

    test_topology(net)

    start_teastore_loadtest(net)

    CLI.do_stopworkloads = stop_workloads

    info('*** Running CLI\n')
    CLI(net)
    info('*** Stopping network')
    net.stop()
except Exception as e:
    error(e)
    cleanup()
    exit(-1)
