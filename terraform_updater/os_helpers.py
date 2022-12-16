import os

from novaclient import api_versions, client


class OSHelper:  # pragma: no cover
    def __init__(self):
        self.nova = client.Client(
            api_versions.APIVersion("2.30"),
            auth_url=os.environ.get("OS_AUTH_URL"),
            username=os.environ.get("OS_USERNAME"),
            password=os.environ.get("OS_PASSWORD"),
            project_id=os.environ.get("OS_PROJECT_ID"),
            user_domain_name=os.environ.get("OS_USER_DOMAIN_NAME"),
            project_domain_id=os.environ.get("OS_PROJECT_DOMAIN_ID"),
            region_name=os.environ.get("OS_REGION_NAME"),
        )

    def server_list(self, os_search_pattern):
        return self.nova.servers.list(
            detailed=True, search_opts={"name": os_search_pattern}
        )

    def interfaces_list(self, server_id):
        ports = {}
        interfaces = self.nova.servers.interface_list(server_id)
        for interface in interfaces:
            for subnet in interface.fixed_ips:
                if interface.id not in ports:
                    ports[interface.id] = []
                ports[interface.id].append(subnet["ip_address"])

        return ports
