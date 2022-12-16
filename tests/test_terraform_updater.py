import unittest
import pytest

from pathlib import Path
from unittest.mock import patch, Mock

from terraform_updater import TerraformUpdater


class TestTerraformUpdater:
    def setup_class(self):
        self.current_path = Path(__file__).parent.absolute()
        # Default parameters
        self.tfstate_path = f"{self.current_path}/states/01_simple_vm.json"
        self.os_name = "an-openstack-vm"
        self.tf_name = "the_vm_in_terraform"
        self.tf_ports = {
            "the_vm_in_terraform_public": "Ext-Net",
            "the_vm_in_terraform_priv": "priv",
        }

        # Init with simple parameters
        self.tu = TerraformUpdater(
            os_name=self.os_name,
            tf_name=self.tf_name,
            tf_ports=self.tf_ports,
            tfstate_path=self.tfstate_path,
            init_only=True,
        )

    def test_init(self):
        assert self.tu.os_name == "an-openstack-vm"
        assert self.tu.os_search_pattern == "^an-openstack-vm$"
        assert self.tu.tf_name == "the_vm_in_terraform"

        assert self.tu.check is True

        assert self.tu.tfstate_path == self.tfstate_path
        assert self.tu.target_tfstate_path is False
        assert self.tu.tfstate == {}
        assert self.tu.resources == {}
        assert self.tu.compute_by_id == {}
        assert self.tu.port_by_id == {}

        assert self.tu.ports_order == [
            "the_vm_in_terraform_public",
            "the_vm_in_terraform_priv",
        ]
        assert self.tu.ports == {
            "Ext-Net": {
                "need_import": False,
                "imported": False,
                "port_id": False,
                "network": {},
                "port_name": "the_vm_in_terraform_public",
                "fixed_ip_v4": "",
            },
            "priv": {
                "need_import": False,
                "imported": False,
                "port_id": False,
                "network": {},
                "port_name": "the_vm_in_terraform_priv",
                "fixed_ip_v4": "",
            },
        }
        assert self.tu.ports_by_network == {
            "Ext-Net": "the_vm_in_terraform_public",
            "priv": "the_vm_in_terraform_priv",
        }
        assert self.tu.ports_by_ip == {}
        assert self.tu.os_ci == {
            "name": "",
            "server_id": "",
            "ports": {},
            "ip_addrs": {},
        }
        assert self.tu.need_update_tf_state == False
        assert self.tu.need_to_import == {}

        # Another parameters, may be more complex
        os_name = "another-openstack-vm"
        tf_name = "the_other_vm_in_terraform"
        target_tfstate_path = "/tmp/state_out.json"
        tf_ports = {
            "another_port_name_public": "Ext-Net",
        }

        # Init with new parameters
        tu = TerraformUpdater(
            os_name=os_name,
            tf_name=tf_name,
            tf_ports=tf_ports,
            tfstate_path=self.tfstate_path,
            target_tfstate_path=target_tfstate_path,
            check=False,
            init_only=True,
        )
        assert tu.os_search_pattern == "^another-openstack-vm$"
        assert tu.target_tfstate_path == "/tmp/state_out.json"
        assert tu.check is False
        assert tu.ports == {
            "Ext-Net": {
                "need_import": False,
                "imported": False,
                "port_id": False,
                "network": {},
                "port_name": "another_port_name_public",
                "fixed_ip_v4": "",
            },
        }
        assert tu.ports_by_network == {
            "Ext-Net": "another_port_name_public",
        }

    @patch("terraform_updater.os_helpers.OSHelper.__init__")
    @patch("terraform_updater.os_helpers.OSHelper.server_list")
    @patch("terraform_updater.os_helpers.OSHelper.interfaces_list")
    def test_collect_os_data(self, m_interfaces_list, m_server_list, m_init):
        m_init.return_value = None
        m_server_list.return_value = [
            {
                "name": "an-openstack-vm",
                "id": "4b450ea7-c5b4-44a5-95d7-b3266a3e1ed1",
            }
        ]
        m_interfaces_list.return_value = {
            "0f48a800-bd0d-43e8-88ae-c735f35097eb": [
                "2001:1234::abcd",
                "12.34.45.67",
            ],
            "f31d734e-5ac5-49c3-8f44-f5d933e00685": [
                "192.168.42.42",
            ],
        }

        self.tu.collect_os_data()

        assert self.tu.os_ci == {
            "name": "an-openstack-vm",
            "server_id": "4b450ea7-c5b4-44a5-95d7-b3266a3e1ed1",
            "ports": {
                "0f48a800-bd0d-43e8-88ae-c735f35097eb": [
                    "2001:1234::abcd",
                    "12.34.45.67",
                ],
                "f31d734e-5ac5-49c3-8f44-f5d933e00685": [
                    "192.168.42.42",
                ],
            },
            "ip_addrs": {
                "2001:1234::abcd": "0f48a800-bd0d-43e8-88ae-c735f35097eb",
                "12.34.45.67": "0f48a800-bd0d-43e8-88ae-c735f35097eb",
                "192.168.42.42": "f31d734e-5ac5-49c3-8f44-f5d933e00685",
            },
        }

        # Error cases
        m_server_list.return_value = [
            {
                "name": "an-openstack-vm",
                "id": "4b450ea7-c5b4-44a5-95d7-b3266a3e1ed1",
            },
            {
                "name": "an-openstack-vm",
                "id": "88f0ca96-64c5-4f9f-8bbd-af674d6a826d",
            },
        ]

        with pytest.raises(SystemExit):
            self.tu.collect_os_data()

    def test_parse_state(self):
        self.tu.parse_state()
        assert len(self.tu.tfstate) == 2
        assert self.tu.tfstate["serial"] == 5
        assert list(self.tu.resources.keys()) == [
            "openstack_compute_instance_v2",
            "openstack_networking_port_v2",
        ]
        assert list(self.tu.resources["openstack_compute_instance_v2"].keys()) == [
            "the_vm_in_terraform",
            "the_other_vm_in_terraform",
        ]
        assert list(self.tu.resources["openstack_networking_port_v2"].keys()) == [
            "the_other_vm_in_terraform_public",
            "the_vm_in_terraform_priv",
        ]

        assert self.tu.compute_by_id == {
            "4b450ea7-c5b4-44a5-95d7-b3266a3e1ed1": "the_vm_in_terraform",
            "1b4a90d8-96bb-4885-a1f7-4d07118ec7e1": "the_other_vm_in_terraform",
        }

        assert self.tu.port_by_id == {
            "62ba2fca-4d32-4301-b265-0b7f985fd3cb": "the_other_vm_in_terraform_public",
            "fd4bd4b4-7f48-4e62-bc2e-3dc68f218caa": "the_vm_in_terraform_priv",
        }

        assert self.tu.ports_by_ip == {
            "192.168.42.42": "fd4bd4b4-7f48-4e62-bc2e-3dc68f218caa",
            "12.34.45.89": "62ba2fca-4d32-4301-b265-0b7f985fd3cb",
            "2001:1234::4321": "62ba2fca-4d32-4301-b265-0b7f985fd3cb",
        }

    @patch("terraform_updater.os_helpers.OSHelper.__init__")
    @patch("terraform_updater.os_helpers.OSHelper.server_list")
    @patch("terraform_updater.os_helpers.OSHelper.interfaces_list")
    def init_data(self, m_interfaces_list, m_server_list, m_init):
        m_init.return_value = None
        m_server_list.return_value = [
            {
                "name": "an-openstack-vm",
                "id": "4b450ea7-c5b4-44a5-95d7-b3266a3e1ed1",
            }
        ]
        m_interfaces_list.return_value = {
            "0f48a800-bd0d-43e8-88ae-c735f35097eb": [
                "2001:1234::abcd",
                "12.34.45.67",
            ],
            "f31d734e-5ac5-49c3-8f44-f5d933e00685": [
                "192.168.42.42",
            ],
        }
        m_init.return_value = None
        m_server_list.return_value = [
            {
                "name": "an-openstack-vm",
                "id": "4b450ea7-c5b4-44a5-95d7-b3266a3e1ed1",
            }
        ]
        m_interfaces_list.return_value = {
            "0f48a800-bd0d-43e8-88ae-c735f35097eb": [
                "2001:1234::abcd",
                "12.34.45.67",
            ],
            "f31d734e-5ac5-49c3-8f44-f5d933e00685": [
                "192.168.42.42",
            ],
        }
        self.tu.parse_state()
        self.tu.collect_os_data()

    def test_check_and_extract_vm(self):
        self.init_data()
        self.tu.check_and_extract_vm()

        assert self.tu.need_to_import == {
            "the_vm_in_terraform_public": "0f48a800-bd0d-43e8-88ae-c735f35097eb",
        }

        with pytest.raises(SystemExit):
            self.tu.os_ci["server_id"] = "XX-XX"
            self.tu.check_and_extract_vm()

    def test_update_state(self):
        self.init_data()
        self.tu.check_and_extract_vm()
        self.tu.update_state()

        assert self.tu.tfstate["serial"] == 6
        assert (
            self.tu.tfstate["resources"][0]["instances"][0]["attributes"]["network"][1][
                "fixed_ip_v4"
            ]
            == "192.168.42.42"
        )
        assert (
            self.tu.tfstate["resources"][0]["instances"][0]["attributes"]["network"][1][
                "port"
            ]
            == "fd4bd4b4-7f48-4e62-bc2e-3dc68f218caa"
        )
