from enum import StrEnum
from kubernetes.client import V1Ingress
from typing import NamedTuple
from utils.unwrap import unwrap


class Annotations(StrEnum):
    REALM = "meta.keycloak.org/realm"
    CLIENT = "meta.keycloak.org/client"
    REDIRECT_URI = "meta.keycloak.org/redirect-uri"


class EventType(StrEnum):
    ADDED = "ADDED"
    DELETED = "DELETED"
    MODIFIED = "MODIFIED"
    ERROR = "ERROR"
    BOOKMARK = "BOOKMARK"


class NamespacedIngress(NamedTuple):
    namespace: str
    name: str


class KeycloakRealmClient(NamedTuple):
    realm: str
    name: str


class KeycloakRealmClientRedirect(NamedTuple):
    realm: str
    name: str
    uri: str

    def client(self):
        return KeycloakRealmClient(self.realm, self.name)


class EventProcessor:
    redirects: dict[KeycloakRealmClient, set[str]] = {}
    ingresses: dict[NamespacedIngress, KeycloakRealmClientRedirect] = {}

    def add_redirect(
        self, redirect: KeycloakRealmClientRedirect, ingress: NamespacedIngress
    ):
        client = redirect.client()
        if client not in self.redirects:
            self.redirects[client] = set()
        self.redirects[client].add(redirect.uri)
        self.ingresses[ingress] = redirect

    def remove_redirect(
        self, ingress: NamespacedIngress
    ) -> KeycloakRealmClientRedirect:
        old_redirect = self.ingresses[ingress]
        # side-effect: leaves an empty set
        self.redirects[old_redirect.client()].remove(old_redirect.uri)
        del self.ingresses[ingress]
        return old_redirect

    def process_event(
        self,
        ingress: NamespacedIngress,
        redirect: KeycloakRealmClientRedirect | None,
        event: EventType,
    ) -> set[KeycloakRealmClient]:
        if event == EventType.MODIFIED:
            if ingress in self.ingresses:
                if not redirect:
                    old_redirect = self.remove_redirect(ingress)
                    return {old_redirect.client()}
                else:
                    old_redirect = self.ingresses[ingress]
                    if old_redirect != redirect:
                        self.remove_redirect(ingress)
                        self.add_redirect(redirect, ingress)
                        if old_redirect.client() != redirect.client():
                            return {old_redirect.client(), redirect.client()}
                        else:
                            return {old_redirect.client()}
                    else:
                        pass

            elif redirect:
                self.add_redirect(redirect, ingress)
                return {redirect.client()}
            else:
                pass
        elif event == EventType.ADDED:
            if redirect:
                self.add_redirect(redirect, ingress)
                return {redirect.client()}
            else:
                pass
        elif event == EventType.DELETED:
            if ingress in self.ingresses:
                old_redirect = self.remove_redirect(ingress)
                return {old_redirect.client()}
            else:
                pass
        return set()

    def process_k8s_ingress_list(self, ingress_list: list[V1Ingress]):
        modified = set()
        for ingress in ingress_list:
            modified.update(self.process_k8s_event(ingress, EventType.ADDED))
        return modified

    def process_k8s_event(
        self, ingress: V1Ingress, event: EventType
    ) -> set[KeycloakRealmClient]:
        metadata = unwrap(ingress.metadata)

        new_ingress = NamespacedIngress(
            unwrap(metadata.namespace), unwrap(metadata.name)
        )
        new_redirect: KeycloakRealmClientRedirect | None = None

        if metadata.annotations:
            realm = metadata.annotations.get(Annotations.REALM)
            client = metadata.annotations.get(Annotations.CLIENT)
            redirect_uri = metadata.annotations.get(Annotations.REDIRECT_URI)

            if realm and client and redirect_uri:
                new_redirect = KeycloakRealmClientRedirect(realm, client, redirect_uri)

        return self.process_event(new_ingress, new_redirect, event)

    def redirects_for_clients(
        self, clients: set[KeycloakRealmClient]
    ) -> dict[KeycloakRealmClient, set[str]]:
        result: dict[KeycloakRealmClient, set[str]] = {}
        for client in clients:
            result[client] = self.redirects[client]
        return result
