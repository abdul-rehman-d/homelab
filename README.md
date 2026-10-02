# smallboi homelab

Docker Compose configuration for the Ubuntu Server homelab running on
`smallboi`. Applications are private to the home LAN and the
`arowana-cat.ts.net` tailnet.

## Access

Tailscale Services are the preferred way to open the applications. Tailscale
provides private routing, DNS and browser-trusted HTTPS certificates.

| Application | Tailnet URL | LAN fallback |
| --- | --- | --- |
| Homepage | `https://home.arowana-cat.ts.net` | `http://SERVER_LAN_IP:3000` |
| Stirling PDF | `https://pdf.arowana-cat.ts.net` | `http://SERVER_LAN_IP:6000` |
| qBittorrent | `https://qbit.arowana-cat.ts.net` | `http://SERVER_LAN_IP:4000` |
| Torrent Lab | `https://torrent.arowana-cat.ts.net` | `http://SERVER_LAN_IP:5000` |
| Jellyfin | `https://jellyfin.arowana-cat.ts.net` | `http://SERVER_LAN_IP:8096` |
| Portainer | `https://portainer.arowana-cat.ts.net` | `http://SERVER_LAN_IP:9000` |
| Cockpit | `https://cockpit.arowana-cat.ts.net` | `https://SERVER_LAN_IP:9090` |

Replace `SERVER_LAN_IP` with the value configured in `.env`.

The web applications are mounted at `/` on separate service names. This avoids
the broken assets, redirects, cookies and WebSockets that some applications
experience when hosted under URL paths such as `/qbit`.

## First deployment after this migration

The repository previously started three independent Compose projects. Run the
one-time migration so those containers are recreated under the root Compose
project:

```bash
cp .env.example .env
# Edit .env and set smallboi's reserved LAN address.

./scripts/migrate-compose-project
```

The migration removes and recreates this repository's named containers and
deletes the obsolete `homelab-proxy` network. It does not remove the bind
mounted application data under `/srv`.

Before Tailscale Services can be advertised, define `tag:homelab` under
**Access controls → Definitions → Tags** and assign it to `smallboi` under
**Network → Machines → Edit tags**. A Service host must be tagged; tagging replaces the machine's
user-based Tailscale identity. Keep a LAN SSH session available while making
this change. Under **Network → Services**, define `home`, `pdf`, `qbit`, `torrent`,
`jellyfin`, `portainer` and `cockpit`, each with endpoint `tcp:443`. Then run
`./scripts/tailscale-services-up` and approve the pending host for each
Service. HTTPS must be enabled under the tailnet DNS settings.

Remove the old restricted nameserver for the `smallboi` split-DNS domain. It is
no longer used. Leave MagicDNS enabled.

## Normal operation

Start or reconcile everything:

```bash
./scripts/up
```

The root `compose.yaml` includes the infra, media and tools Compose files. The
startup script brings up the containers, then idempotently reapplies the
Tailscale Service declarations.

See [COMMANDS.md](COMMANDS.md) for firewall setup, status checks, logs,
upgrades and troubleshooting.

## Layout

```text
compose.yaml                     Root Compose include file
infra/compose.yaml               Homepage and Portainer
media/docker-compose.yaml        Jellyfin, qBittorrent and Torrent Lab
tools/compose.yaml               Stirling PDF
homepage/                        Version-controlled Homepage configuration
scripts/up                       Normal startup/reconciliation
scripts/tailscale-services-up    Tailscale Service declarations
scripts/migrate-compose-project  One-time migration from the old projects
COMMANDS.md                      Server operations and firewall commands
```

## Exposure model

Each container web port is bound twice:

- `127.0.0.1` for the local Tailscale Serve proxy.
- `SERVER_LAN_IP` for intentional direct access from the home LAN.

Nothing listens on every host address except qBittorrent's TCP/UDP `6881` peer
port. Do not forward any management or web ports on the router. If BitTorrent
inbound connectivity is desired, forward only `6881`.

Portainer retains access to `/var/run/docker.sock`, which is effectively root
access to the server. Homepage deliberately uses static links and does not
receive the Docker socket.

## Persistent data

Application data remains outside the repository:

```text
/srv/portainer/data
/srv/jellyfin/config
/srv/jellyfin/cache
/srv/qbittorrent/config
/srv/torrentlab/config
/srv/stirling-pdf
/srv/nutshell
```

Jellyfin, qBittorrent and Torrent Lab mount `/srv/nutshell/media` writable so
media can be deleted from Jellyfin.

## Image updates

Public images use explicit application versions. Torrent Lab does not publish
version tags, so its `latest` label is locked to an OCI digest. `renovate.json`
groups container update proposals for deliberate review; updates are never
automerged.
