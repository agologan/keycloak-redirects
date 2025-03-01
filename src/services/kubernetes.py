from .events import EventProcessor, EventType, KeycloakRealmClient
from kubernetes import client, config, watch
from utils.unwrap import unwrap


class KubernetesService:
    def __init__(self):
        config.load_kube_config()
        self.api = client.NetworkingV1Api()
        self.service = EventProcessor()

    def start(self, callback):
        assert callback != None

        ingress_list = self.api.list_ingress_for_all_namespaces()
        modified = self.service.process_k8s_ingress_list(ingress_list.items)
        callback(self.service.redirects_for_clients(modified))

        resource_version = unwrap(ingress_list.metadata).resource_version

        w = watch.Watch()
        for event in w.stream(
            self.api.list_ingress_for_all_namespaces, resource_version=resource_version
        ):
            modified = self.service.process_k8s_event(
                event["object"], EventType(event["type"])
            )
            callback(self.service.redirects_for_clients(modified))
