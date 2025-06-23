from .events import KeycloakRealmClient
from keycloak import KeycloakAdmin, KeycloakGetError, KeycloakOpenIDConnection
from utils.unwrap import unwrap
import os


class KeycloakService:
    def __init__(self, config):
        server_url = unwrap(os.getenv("KEYCLOAK_HOST"))
        self.realm = unwrap(os.getenv("KEYCLOAK_REALM", default="master"))
        client_id = unwrap(os.getenv("KEYCLOAK_CLIENT_ID"))
        client_secret = unwrap(os.getenv("KEYCLOAK_CLIENT_SECRET"))
        self.dry_run = os.getenv("DRY_RUN", "false") == "true"

        self.api = KeycloakAdmin(
            server_url=server_url,
            client_id=client_id,
            client_secret_key=client_secret,
            realm_name=self.realm,
            verify=True,
        )

        self.__cache_clients(config)
        self.config = config

    def change_realm(self, realm: str):
        self.api.change_current_realm(self.realm)
        self.api.connection._refresh_if_required()
        self.api.change_current_realm(realm)

    def __cache_clients(self, config):
        self.client_map = {}
        for realm in config:
            self.client_map[realm] = {}
            self.change_realm(realm)
            try:
                for client in self.api.get_clients():
                    self.client_map[realm][client["clientId"]] = client["id"]
            except KeycloakGetError as e:
                print(f"Error fetching clients for realm {realm}: {e}")
                exit(1)

    def __update_client(self, realm: str, client_id: str, redirects: set[str]):
        self.change_realm(realm)
        client_config = self.api.get_client(client_id)

        if not client_config:
            print(f"Client {client_id} not found in realm {realm}.")
            return

        client_config["redirectUris"] = list(redirects)

        if self.dry_run:
            print(f"Updating {client_id} {redirects}")
        else:
            self.api.update_client(client_id, client_config)

    def update_redirects(
        self,
        redirects: dict[KeycloakRealmClient, set[str]],
    ):
        for client, redirect_list in redirects.items():
            client_config = self.config.get(client.realm, {}).get(client.name)

            if not client_config:
                print(f"{client.realm}/{client.name} not in config. ignoring update.")
                continue

            if client_config["enabled"] != True:
                print(f"{client.realm}/{client.name} disabled. ignoring update.")
                continue

            if client_config["loopback"] == True:
                redirect_list.add("http://localhost:*")

            client_id = self.client_map[client.realm].get(client.name)
            if client_id:
                self.__update_client(client.realm, client_id, redirect_list)
            else:
                print(f"{client.name} missing from cache")
