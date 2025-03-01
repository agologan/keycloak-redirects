from services.keycloak import KeycloakService
from services.kubernetes import KubernetesService
import tomllib


def main():
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)

    keycloak = KeycloakService(config)
    kubernetes = KubernetesService()
    kubernetes.start(keycloak.update_redirects)


if __name__ == "__main__":
    main()
