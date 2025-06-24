# Keycloak redirect controller

Kubernetes controller that automatically manages the list of allowed redirect URIs for Keycloak clients based on annotations found in Kubernetes Ingress resources. This ensures that your Keycloak clients' redirect URIs are always in sync with your deployed applications, improving security and reducing manual configuration.

## How It Works

1. The controller scans all Ingress resources for specific annotations:
    - `meta.keycloak.org/realm`
    - `meta.keycloak.org/client`
    - `meta.keycloak.org/redirect-uri`
2. When an Ingress is added, modified, or deleted, the controller updates the corresponding Keycloak client's allowed redirect URIs.
3. Configuration is provided via a TOML file (mounted as a ConfigMap) and environment variables.

Keycloak client requires `client authentication` and `service account roles` enabled.

The client requires `manage-clients` role for the targeted realm(s).

Example config.toml:

```toml
[realm1.client1]
enabled = true
loopback = true
[realm2.client1]
enabled = true
loopback = false
```

Note: Some managed clients may require `web origins` set to `+` (permit all valid redirect URIs) to avoid CORS issues.
