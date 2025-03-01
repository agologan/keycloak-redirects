from .events import KeycloakRealmClient
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from utils.unwrap import unwrap
import os


class KeycloakService:
    def __init__(self, config):
        server_url = unwrap(os.getenv("KEYCLOAK_HOST"))
        client_id = unwrap(os.getenv("KEYCLOAK_CLIENT_ID"))
        client_secret = unwrap(os.getenv("KEYCLOAK_CLIENT_SECRET"))
        self.dry_run = os.getenv("DRY_RUN", "false") == "true"

        self.apis = {}
        for realm in config["realms"]:
            self.apis[realm] = KeycloakAdmin(
                server_url=server_url,
                client_id=client_id,
                client_secret_key=client_secret,
                verify=True,
            )

        self.__cache_clients(config)

    def __cache_clients(self, config):
        self.client_map = {}
        for realm in config["realms"]:
            self.client_map[realm] = {}
            for client in self.apis[realm].get_clients():
                self.client_map[realm][client.clientId] = client.id

    def __update_client(self, api: KeycloakAdmin, client_id: str, redirects: set[str]):
        client_config = api.get_client(client_id)
        client_config["redirectUris"] = list(redirects)

        if self.dry_run:
            print(f"Updating {client_id} {redirects}")
        else:
            api.update_client(client_id, client_config)

    def update_redirects(
        self,
        redirects: dict[KeycloakRealmClient, set[str]],
    ):
        for client, redirect_list in redirects.items():
            if client.realm not in self.client_map:
                print(f"{client.realm} not in config. ignoring {client.name} update.")

            client_id = self.client_map[client.realm].get(client.name)
            if client_id:
                self.__update_client(self.apis[client.realm], client_id, redirect_list)
            else:
                print(f"{client.name} missing from cache")
