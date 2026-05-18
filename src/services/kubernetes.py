from .events import EventProcessor, EventType
from kubernetes import client, config, watch
from kubernetes.client.api_client import ApiClient
import ssl
from kubernetes.client.exceptions import ApiException
from kubernetes.config.config_exception import ConfigException
from utils.unwrap import unwrap
import urllib3


class KubernetesService:
    def __init__(self):
        try:
            config.load_incluster_config()
        except ConfigException:
            config.load_kube_config()



        self.api = client.NetworkingV1Api(api_client=self.patched_api_client())
        self.service = EventProcessor()

    def patched_api_client(self):
        api_client = ApiClient()

        # @see https://github.com/kubernetes-client/python/issues/2394#issuecomment-3460128887
        # disable VERIFY_X509_STRICT when using urllib3 v2.4.0 with Python 3.13 on EKS
        ctx = ssl.create_default_context()
        ctx.verify_flags = ctx.verify_flags & ~ssl.VERIFY_X509_STRICT

        api_client.rest_client.pool_manager = urllib3.PoolManager(
            num_pools=4,
            ssl_context=ctx,
            **api_client.rest_client.pool_manager.connection_pool_kw,
        )

        return api_client

    def start(self, callback):
        assert callback is not None
        resource_version = None

        while True:
            try:
                if resource_version is None:
                    ingress_list = self.api.list_ingress_for_all_namespaces()
                    modified = self.service.process_k8s_ingress_list(ingress_list.items)
                    callback(self.service.redirects_for_clients(modified))

                    resource_version = unwrap(ingress_list.metadata).resource_version

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
