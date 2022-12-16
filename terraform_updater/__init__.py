import json
import sys

from .os_helpers import OSHelper


class TerraformUpdater:
    def __init__(
        self,
        os_name,
        tf_name,
        tf_ports,
        tfstate_path,
        target_tfstate_path=False,
        check=True,
        init_only=True,
    ):
        self.os_name = os_name
        self.os_search_pattern = f"^{os_name}$"
        self.tf_name = tf_name

        self.check = check

        self.tfstate_path = tfstate_path
        self.target_tfstate_path = target_tfstate_path
        self.ressource_filter = [
            "openstack_compute_instance_v2",
            "openstack_networking_port_v2",
        ]
        self.resources = {}
        self.compute_by_id = {}
        self.port_by_id = {}

        self.tfstate = {}
        self.ports = {}
        self.ports_by_network = {}
        self.ports_order = []
        for port_name, network_name in tf_ports.items():
            self.ports_order.append(port_name)
            self.ports[network_name] = {
                "need_import": False,
                "imported": False,
                "port_id": False,
                "network": {},
                "port_name": port_name,
                "fixed_ip_v4": "",
            }
            self.ports_by_network[network_name] = port_name

        self.ports_by_ip = {}
        self.os_ci = {
            "name": "",
            "server_id": "",
            "ports": {},
            "ip_addrs": {},
        }
        self.need_update_tf_state = False
        self.need_to_import = {}
        self.os_client = False
        if not init_only:  # pragma: no cover
            self.collect_os_data()
            self.parse_state()

    def collect_os_data(self):
        if self.os_client is False:
            self.os_client = OSHelper()

        servers = self.os_client.server_list(self.os_search_pattern)

        if len(servers) != 1:
            print(f"Wrong server count for {self.os_name}: {len(servers)}")
            sys.exit(1)

        self.os_ci["name"] = servers[0]["name"]
        self.os_ci["server_id"] = servers[0]["id"]

        interfaces = self.os_client.interfaces_list(self.os_ci["server_id"])
        self.os_ci["ports"] = interfaces
        for port_id in interfaces:
            for ip_addr in interfaces[port_id]:
                self.os_ci["ip_addrs"][ip_addr] = port_id

    def parse_state(self):
        with open(self.tfstate_path, "r") as f:
            self.tfstate = json.load(f)
        for res in self.tfstate["resources"]:
            res_type = res.get("type")

            if res_type == "openstack_compute_instance_v2":
                res_name = res.get("name")
                res_id = res["instances"][0]["attributes"]["id"]
                self.compute_by_id[res_id] = res_name

            if res_type == "openstack_networking_port_v2":
                res_name = res.get("name")
                res_id = res["instances"][0]["attributes"]["id"]
                self.port_by_id[res_id] = res_name
                for instance in res["instances"]:
                    for ip in instance["attributes"]["all_fixed_ips"]:
                        self.ports_by_ip[ip] = instance["attributes"]["id"]

            if res_type not in self.ressource_filter:
                continue
            if res_type not in self.resources:
                self.resources[res_type] = {}
            self.resources[res_type][res.get("name")] = res

    def get_server_ressource(self, tf_name):
        return self.resources["openstack_compute_instance_v2"][tf_name]

    def get_server_id(self, tf_name):
        res = self.get_server_ressource(tf_name)
        return res["instances"][0]["attributes"]["id"]

    def get_server_network(self, tf_name):
        res = self.get_server_ressource(tf_name)
        return res["instances"][0]["attributes"]["network"]

    def check_and_extract_vm(self):
        if self.os_ci["server_id"] != self.get_server_id(self.tf_name):
            sys.exit(0)

        for i, network in enumerate(self.get_server_network(self.tf_name)):
            if network["port"] == "":
                if network["fixed_ip_v4"] not in self.ports_by_ip:
                    self.need_to_import[self.ports_order[i]] = self.os_ci["ip_addrs"][
                        network["fixed_ip_v4"]
                    ]

    def update_state(self):
        self.tfstate["serial"] += 1

        new_ressources = []

        for res in self.tfstate["resources"]:
            res_name = res.get("name")
            if res_name == self.tf_name:
                for i, network in enumerate(
                    res["instances"][0]["attributes"]["network"]
                ):
                    current_ip = network["fixed_ip_v4"]
                    if current_ip in self.ports_by_ip:
                        res["instances"][0]["attributes"]["network"][i][
                            "port"
                        ] = self.ports_by_ip[current_ip]
            new_ressources.append(res)

        self.tfstate["resources"] = new_ressources
