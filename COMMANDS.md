# smallboi command reference

Run these commands on the Ubuntu Server host unless a section explicitly says
to use the Mac that runs Ollama.

## Discover network values

```bash
ip -br address
ip route
tailscale ip -4
tailscale status
```

Identify:

- `SERVER_LAN_IP`: smallboi's reserved IPv4 address on the home LAN.
- `LAN_INTERFACE`: the interface holding that address, such as `enp1s0`.
- `LAN_CIDR`: the trusted home subnet, such as `192.168.1.0/24`.

Create the local environment file:

```bash
cp .env.example .env
nano .env
```

## First migration

Use this once when moving from the old three-project/Caddy/CoreDNS deployment:

```bash
./scripts/migrate-compose-project
```

This removes and recreates this repository's named containers and deletes the
obsolete `homelab-proxy` network. Bind-mounted data under `/srv` is preserved.

The container portion of the migration may complete before the Tailscale
portion. If it stops with `service hosts must be tagged nodes`, do not repeat
the migration: finish the Tailscale setup below and run
`./scripts/tailscale-services-up`.

Under the DNS page, enable HTTPS and MagicDNS, and remove the obsolete
restricted nameserver for the `smallboi` domain.

## Start and stop

```bash
./scripts/up
docker compose ps
docker compose stop
docker compose down
```

`docker compose down` removes containers and project networks, but it does not
delete the bind-mounted data under `/srv`.

## Logs and health

```bash
docker compose ps
docker compose logs --tail=100 homepage
docker compose logs --tail=100 qbittorrent
docker compose logs --tail=100 torrentlab
docker compose logs --tail=100 stirling-pdf
docker compose logs --tail=100 open-webui
docker inspect --format '{{json .State.Health}}' qbittorrent | jq
docker inspect --format '{{json .State.Health}}' open-webui | jq
```

## Ollama backend on the Mac

Ollama stays bound to `127.0.0.1:11434` on the Mac. Tailscale Serve makes it
available privately to `smallboi` without exposing the unauthenticated Ollama
API on the LAN.

Run this on `madmans-macbook`, not on `smallboi`:

```bash
tailscale serve --bg --yes 11434
tailscale serve status
```

The tailnet policy must allow the tagged homelab server to reach the Mac's
Tailscale address on HTTPS. Add a grant equivalent to this under **Access
controls**, merging it into the existing `grants` array:

```json
{
  "src": ["tag:homelab"],
  "dst": ["100.102.188.29"],
  "ip": ["tcp:443"]
}
```

The Tailscale IP is stable while the Mac remains enrolled. If the Mac is
removed and re-added to the tailnet, update both the grant and this document.

Verify from `smallboi` before starting Open WebUI:

```bash
curl -fsS https://madmans-macbook.arowana-cat.ts.net/api/tags | jq -r '.models[].name'
```

The Mac must remain awake with both Ollama and Tailscale running. To remove the
private proxy later, run this on the Mac:

```bash
tailscale serve --https=443 off
```

## Tailscale Services

Before the first run, use the Tailscale admin console:

1. Under **Access controls → Definitions → Tags**, define `tag:homelab`.
2. Under **Network → Machines**, select `smallboi` → **Edit tags** and assign
   `tag:homelab`. Keep a LAN SSH session open: tagging changes the machine
   from a user-owned identity to a tagged identity and may affect Tailscale
   SSH access policies.
3. Under **Network → Services**, define `home`, `chat`, `pdf`, `qbit`, `torrent`,
   `jellyfin`, `portainer` and `cockpit`, each with endpoint `tcp:443`.

Reapply every service declaration:

```bash
./scripts/tailscale-services-up
```

Inspect the effective configuration:

```bash
tailscale serve status
tailscale serve status --json | jq
```

Expected HTTPS endpoints:

```text
https://home.arowana-cat.ts.net
https://chat.arowana-cat.ts.net
https://pdf.arowana-cat.ts.net
https://qbit.arowana-cat.ts.net
https://torrent.arowana-cat.ts.net
https://jellyfin.arowana-cat.ts.net
https://portainer.arowana-cat.ts.net
https://cockpit.arowana-cat.ts.net
```

Approve the pending host for each Service in the Tailscale admin console. Use
tailnet grants to limit these services to the intended users and devices.

On first launch, create the Open WebUI administrator account, then disable new
account registration from the admin settings unless other tailnet users need
their own accounts.

## UFW firewall

Keep the current SSH session open while changing firewall rules. Open a second
terminal and confirm that a new SSH connection works before closing the first.

Set values matching the output from `ip route` and `ip -br address`:

```bash
LAN_INTERFACE=enp1s0
LAN_CIDR=192.168.1.0/24
SSH_PORT=22
```

Review existing rules first:

```bash
sudo ufw status numbered
sudo ufw status verbose
```

Set restrictive defaults, allow tailnet traffic, then allow SSH from the LAN:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow in on tailscale0 comment 'Tailscale'
sudo ufw allow in on "$LAN_INTERFACE" from "$LAN_CIDR" to any port "$SSH_PORT" proto tcp comment 'SSH from LAN'
```

Allow the direct LAN web fallbacks:

```bash
sudo ufw allow in on "$LAN_INTERFACE" from "$LAN_CIDR" to any port 3000 proto tcp comment 'Homepage from LAN'
sudo ufw allow in on "$LAN_INTERFACE" from "$LAN_CIDR" to any port 4000 proto tcp comment 'qBit from LAN'
sudo ufw allow in on "$LAN_INTERFACE" from "$LAN_CIDR" to any port 5000 proto tcp comment 'Torrent Lab from LAN'
sudo ufw allow in on "$LAN_INTERFACE" from "$LAN_CIDR" to any port 6000 proto tcp comment 'Stirling PDF from LAN'
sudo ufw allow in on "$LAN_INTERFACE" from "$LAN_CIDR" to any port 7000 proto tcp comment 'Open WebUI from LAN'
sudo ufw allow in on "$LAN_INTERFACE" from "$LAN_CIDR" to any port 8096 proto tcp comment 'Jellyfin from LAN'
sudo ufw allow in on "$LAN_INTERFACE" from "$LAN_CIDR" to any port 9000 proto tcp comment 'Portainer from LAN'
sudo ufw allow in on "$LAN_INTERFACE" from "$LAN_CIDR" to any port 9090 proto tcp comment 'Cockpit from LAN'
```

Optionally allow Tailscale's default UDP port to improve direct peer-to-peer
connections. Tailscale still works through DERP relays without this rule:

```bash
sudo ufw allow 41641/udp comment 'Tailscale direct connections'
```

Enable and verify UFW:

```bash
sudo ufw enable
sudo ufw reload
sudo ufw status verbose
```

Important: Docker implements published ports before normal UFW input rules, so
UFW alone must not be treated as the security boundary for container ports.
The Compose files bind web ports specifically to `SERVER_LAN_IP`, and the
router must not forward them. On a multi-interface or routed/VLAN network, add
source restrictions in Docker's `DOCKER-USER` chain as well.

To disable UFW during recovery from the local console:

```bash
sudo ufw disable
```

## Restrict Cockpit listeners

Cockpit is a host service rather than a Docker container. To make it listen
only on loopback and the server's LAN address:

```bash
sudo systemctl edit cockpit.socket
```

Enter the following, replacing `192.168.1.123` with `SERVER_LAN_IP`:

```ini
[Socket]
ListenStream=
ListenStream=127.0.0.1:9090
ListenStream=192.168.1.123:9090
```

Then apply and verify:

```bash
sudo systemctl daemon-reload
sudo systemctl restart cockpit.socket
sudo ss -lntp | grep ':9090'
curl -kI https://127.0.0.1:9090
```

## Verify listening ports

```bash
sudo ss -lntup
curl -fsSI http://127.0.0.1:3000
curl -fsSI http://127.0.0.1:6000
curl -fsSI http://127.0.0.1:7000
curl -kfsSI https://127.0.0.1:9090
```

From another LAN device, test `http://SERVER_LAN_IP:PORT`. From a device with
Tailscale connected, test the corresponding `https://*.arowana-cat.ts.net`
address.

## qBittorrent hostname validation

If qBittorrent returns `Unauthorized` through Tailscale, open its Web UI over
the LAN and add this value under **Settings -> Web UI -> Server domains**:

```text
qbit.arowana-cat.ts.net
```

Keep CSRF and clickjacking protection enabled.

## Pull reviewed image updates

Review release notes and any Renovate proposal before updating:

```bash
docker compose pull
docker compose up -d
```

After the updated services have been tested and the rollback images are no
longer needed, remove dangling images deliberately with `docker image prune`.
Do not use unattended Watchtower updates on this server.
