from .events import EventProcessor, EventType, KeycloakRealmClient
from kubernetes import client, config, watch
from kubernetes.client.exceptions import ApiException
from utils.unwrap import unwrap
import urllib3


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

        while True:
            try:
                w = watch.Watch()
                for event in w.stream(
                    self.api.list_ingress_for_all_namespaces,
                    resource_version=resource_version,
                ):
                    modified = self.service.process_k8s_event(
                        event["object"], EventType(event["type"])
                    )
                    callback(self.service.redirects_for_clients(modified))
            except ApiException as err:
                if err.status == 410:
                    print(
                        "ERROR: The requested resource version is no longer available."
                    )
                    resource_version = None
                else:
                    raise

            except urllib3.exceptions.ProtocolError:
                print("Lost connection to the k8s API server. Reconnecting...")
