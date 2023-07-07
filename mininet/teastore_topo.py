import asyncio
import os
import re
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from signal import SIGTERM
from time import sleep
from typing import Optional, IO

import typer
from mininet.clean import cleanup
from mininet.net import Containernet, Mininet
from mininet.node import OVSSwitch, RemoteController, Controller, Host
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.topo import Topo
from mininet.log import info, error, setLogLevel, warning

setLogLevel('info')

python_configured_hosts = []
pox_process: Optional[subprocess.Popen] = None
pox_logfile: Optional[IO] = None
POX_PLUGIN_NAME = "stats_per_second_collector"

CLI_ARGS = {}

current_load_intensity_profile_index = 0

load_intensity_profiles = ["LOW", "LOW_2", "MED", "HIGH"]


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

        c1 = RemoteController('c1', ip='127.0.0.1', port=6633)
        c1.checkListening()

        customerSwitch = self.addSwitch('s1')
        ispCustomerSwitch = self.addSwitch('s2')
        ispAPSwitch = self.addSwitch('s3')
        self.apSwitch = self.addSwitch('s4', cls=SDNSwitch, controller=c1)
        # self.apSwitch = self.addSwitch('s4')

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

    def add_teastore_simulation_and_start_network(self, net: Mininet):
        info('*** Adding TeaStore Simulator host\n')

        setLogLevel('debug')

        teastore_simulator = net.addHost('h_sim')

        info('*** Linking TeaStore docker containers\n')
        # alarm provider has 2 GbE connection to his router
        # 1 Gigabit is the maximum bandwidth allowed by mininet
        linkopts = {'bw': 1000, 'delay': '0.19ms', 'jitter': '0.06ms'}
        net.addLink(self.apSwitch, teastore_simulator, **linkopts)

        net.configHosts()

        info('*** Starting network\n')
        net.start()

        simulators_dir = find_directory("Simulators")
        if simulators_dir is None:
            raise RuntimeError("Could not find Simulators directory")

        teastore_simulator.cmd(f'cd {simulators_dir}')
        print("Simulator: Current Working Directory:")
        teastore_simulator.cmdPrint('pwd')
        teastore_simulator.cmdPrint('java -jar TeaStore/Rast-Simulator-0.2.0.jar &> /dev/null &')

        setLogLevel('info')

        info('*** Waiting 3 seconds for TeaStore Simulator to completely start\n')
        sleep(3)
        info('*** Now, you can start the load test\n')

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
        start_catalina = "/usr/local/tomcat/bin/catalina.sh run > /dev/null 2>&1 &"
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
                         # "RABBITMQ_HOST": TEASTORE_KIEKER_STATIC_IP,
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
                         # "RABBITMQ_HOST": TEASTORE_KIEKER_STATIC_IP,
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
                         # "RABBITMQ_HOST": TEASTORE_KIEKER_STATIC_IP
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
                         # "RABBITMQ_HOST": TEASTORE_KIEKER_STATIC_IP
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
        info('*** Waiting 30 seconds for RabbitMQ, Registry and MariaDb to start\n')
        sleep(30)
        teastore_persistence.cmdPrint(teastore_base_cmd)
        teastore_auth.cmdPrint(teastore_base_cmd)
        teastore_image.cmdPrint(teastore_base_cmd)
        teastore_recommender.cmdPrint(teastore_base_cmd)
        teastore_webui.cmdPrint(teastore_base_cmd)
        info('*** Waiting 2 minutes for TeaStore to completely start\n')
        sleep(2*60)
        info('*** Now, you can start the load test\n')


def find_directory(directory_to_find: str):
    current_dir = os.getcwd()

    venv_dir = os.path.join(current_dir, directory_to_find)
    if os.path.isdir(venv_dir):
        return venv_dir

    while True:
        current_dir = os.path.dirname(current_dir)
        venv_dir = os.path.join(current_dir, directory_to_find)

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

    venv_dir = find_directory("venv")
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


def install_our_pox_plugin(force: bool):
    mininet_dir = find_directory("mininet")
    if mininet_dir is None:
        raise RuntimeError("Could not find mininet directory")

    plugin_file = mininet_dir + f"/{POX_PLUGIN_NAME}.py"
    if not os.path.exists(plugin_file):
        raise RuntimeError(f"POX plugin file {plugin_file} does not exist.")

    pox_dir = find_directory("pox")
    if pox_dir is None:
        raise RuntimeError("Could not find pox directory")

    ext_pox_dir = pox_dir + "/ext"
    if not os.path.exists(ext_pox_dir):
        raise RuntimeError(f"Something seems to be wrong with the POX installation. "
                           f"The folder {ext_pox_dir} does not exist.")

    # Check if the file already exists in the destination directory
    destination_file = os.path.join(ext_pox_dir, f"{POX_PLUGIN_NAME}.py")
    if force or not os.path.exists(destination_file):
        info("*** Installing our POX plugin\n")
        # Copy the plugin_file to ext_pox_dir
        shutil.copy(plugin_file, ext_pox_dir, follow_symlinks=False)
        info("File copied successfully.\n")
    else:
        warning("File already exists at the destination.\n")


def start_pox():
    info("*** Starting POX Controller\n")

    install_our_pox_plugin(False)

    statistics_file = Path.cwd() / f"switch_flow_stats_{datetime.now().strftime('%Y-%m-%d')}.json"
    command = f'./pox.py --verbose samples.pretty_log forwarding.l2_pairs ext.{POX_PLUGIN_NAME} --file="{statistics_file}"'

    pox_dir = find_directory("pox")
    if pox_dir is None:
        raise RuntimeError("Could not find pox directory")

    global pox_process
    global pox_logfile

    output_file = os.getcwd() + "/pox_output.log"

    # Open the file in append mode ('a')
    # If the file exists, it will be opened for appending
    # If the file doesn't exist, it will be created
    pox_logfile = open(output_file, 'a')

    # Close the file immediately without making any changes
    pox_logfile.close()

    pox_logfile = open(output_file, "r+")

    pox_process = subprocess.Popen(
        command,
        cwd=pox_dir,
        shell=True,
        preexec_fn=os.setsid,
        stdout=pox_logfile,
        stderr=pox_logfile
    )

    info(f"Process: {pox_process.pid}\n")

    info("Waiting 1 second for POX Controller to start\n")
    sleep(1)


def start_teastore_loadtest(net: Mininet, load_intensity_profile):
    info('*** Starting TeaStore Workload ...\n')

    h_runner = net.get('h_runner')
    try:
        webui: Host = net.get('webui')
    except KeyError as e:
        info('WebUI not found, looking for h_sim\n')
        webui = net.get('h_sim')

    assert webui is not None

    if webui.shell is None:
        warning('Shell is None. Aborting\n')
        return

    setup_python_on_host(h_runner)

    handle_thread = threading.Thread(target=read_and_handle_locust_executor_pipe_messages, kwargs={'net': net})
    handle_thread.start()

    if CLI_ARGS["run_all_load_intensity_profiles"]:
        h_runner.cmdPrint(f"export KEEP_TEASTORE_LOGS=True")
    h_runner.cmdPrint(f"export LOAD_INTENSITY_PROFILE={load_intensity_profile}")

    cmd = f'./start_teastore_loadtest.sh --ip {webui.IP()}'
    info(f'{cmd}\n')

    cmd_output = h_runner.cmd("{} &> /dev/null &".format(cmd))
    info(cmd_output)
    info(f'*** TeaStore Workload is running now: {datetime.now().time()} ...\n')


def test_topology(net: Mininet):
    info('*** Testing topology\n')

    net.ping()
    try:
        webui: Host = net.get('webui')
    except KeyError as e:
        info('WebUI not found, looking for h_sim\n')
        webui = net.get('h_sim')

    assert webui is not None
    h_runner: Host = net.get('h_runner')

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


def read_from_pipe_until_finish(pipe_path):
    pipe_fd = os.open(pipe_path, os.O_RDONLY)
    while True:
        line = os.read(pipe_fd, 1024)
        if not line:
            break
        line = line.decode()
        info(f"*** Received: {line}\n")

        if line == "FIN":
            break

    info(f"*** Named Pipe closed \n")
    os.close(pipe_fd)


def read_and_handle_locust_executor_pipe_messages(**kwargs):
    net: Mininet = kwargs.get('net')

    pipe_name = "/tmp/locust_executor_pipe"
    if not os.path.exists(pipe_name):
        os.mkfifo(pipe_name)

    read_from_pipe_until_finish(pipe_name)

    if CLI_ARGS["run_all_load_intensity_profiles"]:
        global current_load_intensity_profile_index
        current_load_intensity_profile_index += 1
        if current_load_intensity_profile_index < len(load_intensity_profiles):
            info('*** Starting next load test in 30 seconds\n')
            sleep(30)
            start_teastore_loadtest(net, load_intensity_profiles[current_load_intensity_profile_index])
            return

    info('*** All load intensity profiles have been executed\n')
    info('******* Remember to download the logfiles before exiting mininet *******\n')

    if CLI_ARGS["use_simulation"]:
        info('*** You can find the teastore_simulation.log file in the Simulators folder\n')
    else:
        info('*** Navigate to http://localhost:8081/logs/index to download them\n')


def main(
        use_simulation: bool = typer.Option(False, "--use-simulation", "-s"),
        run_all_load_intensity_profiles: bool = typer.Option(False, "--run_all_load_intensity_profiles", "-a")
):
    global CLI_ARGS
    CLI_ARGS = {"use_simulation": use_simulation, "run_all_load_intensity_profiles": run_all_load_intensity_profiles}

    try:
        start_pox()

        teastore_topo = TeaStoreTopo()
        net = Containernet(
            topo=teastore_topo,
            # link=TCLink,
            autoSetMacs=True
        )
        if use_simulation:
            teastore_topo.add_teastore_simulation_and_start_network(net)
        else:
            teastore_topo.add_tea_store_and_start_network(net)

        test_topology(net)

        global current_load_intensity_profile_index
        if run_all_load_intensity_profiles:
            current_load_intensity_profile_index = 0

        start_teastore_loadtest(net, load_intensity_profiles[current_load_intensity_profile_index])

        CLI.do_stopworkloads = stop_workloads

        info('*** Running CLI\n')
        CLI(net)
        info('*** Stopping network\n')
        net.stop()
    except Exception as e:
        error(e)
        cleanup()
        exit(-1)
    finally:
        # Terminate the pox subprocess and its children
        if pox_process is not None:
            os.killpg(os.getpgid(pox_process.pid), SIGTERM)
            pox_process.terminate()
            sleep(2)
        if pox_logfile is not None:
            def remove_ansi_colors(text):
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                return ansi_escape.sub('', text)

            while True:
                try:
                    # Wait for any child process in the process group
                    pid, status = os.waitpid(-os.getpgid(pox_process.pid), 0)

                    # Check if all processes have finished
                    if pid == 0:
                        break

                    # Process the exit status or perform any desired actions
                    print(pid, status)

                except ChildProcessError:
                    # No more child processes in the process group
                    break
                except ProcessLookupError:
                    break

            pox_logfile.flush()

            # Reset the file pointer to the beginning of the file
            pox_logfile.seek(0)

            # Read the log file
            log_content = pox_logfile.read()

            # Remove ANSI color sequences
            clean_log_content = remove_ansi_colors(log_content)

            # Reset the file pointer to the beginning of the file
            pox_logfile.seek(0)

            # Truncate the file to remove its current content
            pox_logfile.truncate()

            pox_logfile.write(clean_log_content)

            pox_logfile.close()


if __name__ == "__main__":
    typer.run(main)
