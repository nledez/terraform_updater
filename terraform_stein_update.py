#!/usr/bin/env python3
import argparse
import json
import sys

from terraform_updater import TerraformUpdater

parser = argparse.ArgumentParser(
    description='Update tfstate after stein upgrade'
)
parser.add_argument('--check',
                    action='store_true',
                    help='Do only check')
parser.add_argument('--os-name',
                    dest='os_name',
                    help='customer os_name')
parser.add_argument('--tf-name',
                    dest='tf_name',
                    help='customer tf_name')
parser.add_argument('--tf-ports',
                    dest='tf_ports',
                    help='customer tf_ports')
parser.add_argument('--source',
                    dest='tfstate_path',
                    help='tfstate source path')
parser.add_argument('--target',
                    dest='target_tfstate_path',
                    help='tfstate target path')

args = parser.parse_args()

check = args.check
os_name = args.os_name
tf_name = args.tf_name
tf_ports_string = args.tf_ports
tfstate_path = args.tfstate_path
target_tfstate_path = args.target_tfstate_path

if not os_name:
    print(f'I need a openstack name:')
    print(f'{sys.argv[0]} --os-name os_name')
    sys.exit(1)

if not tf_name:
    print(f'I need a terraform name:')
    print(f'{sys.argv[0]} --tf-name tf_name')
    sys.exit(1)

if not tf_ports_string:
    print(f'I need a terraform ports (in form "tf_port_name:openstack_network_name,another:one"):')
    print(f'{sys.argv[0]} --tf-ports tf_ports')
    sys.exit(1)

if not tfstate_path:
    print(f'I need a source tfstate path')
    print(f'{sys.argv[0]} --source tfstate_source_path')
    sys.exit(1)

if not target_tfstate_path and not check:
    print(f'I need a target tfstate path')
    print(f'{sys.argv[0]} --target tfstate_target_path')
    sys.exit(1)


tf_ports = {}
for port in tf_ports_string.split(','):
    port_name, network_name = port.split(':')
    tf_ports[port_name] = network_name

updater = TerraformUpdater(
    os_name=os_name,
    tf_name=tf_name,
    tf_ports=tf_ports,
    tfstate_path=tfstate_path,
    check=check,
    init_only=False,
)

if len(updater.need_to_import) > 0:
    for p, i in updater.need_to_import.items():
        print(f'terraform import openstack_networking_port_v2.{p} {i};')
    sys.exit(0)

if check:
    print('Now you can run me with --target')
else:
    with open(target_tfstate_path, 'w') as f:
        json.dump(updater.tfstate, f, indent=2)
        print(f'terraform state push {target_tfstate_path};')
