# podlab
A python containerized CLI for managing UPNP and DNS for docker based homelab.

- Uses container labels via docker socket for dynamic configuration.
- Updates UPNP ports.
- Updates Digital Ocean DNS (could be made to work with others).
- Allows for easy forwarding of new homelab services to public via container labels especially when used with a proxy like traefik.
