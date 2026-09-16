# Homelabbing stuff

for now, just docker composes for my homelab (old laptop converting server)

## Todos
- [ ] figure out caddy
- [ ] vpn instead of cloudfare tunnel?
- [x] TUI app as a dashboard (sorta done @ [abdul-rehman-d/cockpit](https://github.com/abdul-rehman-d/cockpit))

## How it looks
![IMG_0418(1)](https://github.com/user-attachments/assets/a037afcd-e9d8-464a-a73c-2c27526b6f80)


## Apps

### jellyfin
<img width="800" height="450" alt="image" src="https://github.com/user-attachments/assets/eac0885e-275d-4dc5-8962-5076b41fd475" />

### qbittorent
<img width="800" height="450" alt="image" src="https://github.com/user-attachments/assets/8fb930ce-05a2-49fe-9fcc-d203650bff8f" />

### portainer
<img width="800" height="450" alt="image" src="https://github.com/user-attachments/assets/79057344-76e8-47e0-8826-8ee9b25617d6" />

### samba
<img width="800" height="450" alt="image" src="https://github.com/user-attachments/assets/ac127eb1-320d-497b-8a5e-8c4369b0a872" />

### cockpit
<img width="800" height="450" alt="image" src="https://github.com/user-attachments/assets/92114f35-f5c7-4bf4-80e4-f9a42bbe4800" />

### Stirling PDF

Stirling PDF is available on port `6000`. Its persistent data lives under
`/srv/stirling-pdf`. The initial login is `admin` / `stirling`; the app requires
the password to be changed on first login.

## Private service names

When connected to the tailnet, the services are also available without port
numbers:

- `http://smallboi` — dashboard
- `http://cockpit.smallboi` — Cockpit
- `http://portainer.smallboi` — Portainer
- `http://jellyfin.smallboi` — Jellyfin
- `http://qbit.smallboi` — qBittorrent
- `http://torrentlab.smallboi` — Torrent Lab
- `http://pdf.smallboi` — Stirling PDF

CoreDNS answers the `*.smallboi` records on the server's Tailscale address,
`100.119.155.32`. The tailnet must have a restricted nameserver for the
`smallboi` domain pointing to that address. All original published ports remain
available. The DNS wildcard means future one-level names only need a matching
Caddy route; CoreDNS does not need another record.

If qBittorrent rejects the proxied hostname, add `qbit.smallboi` under
**Settings → Web UI → Server domains** while leaving its CSRF and clickjacking
protections enabled.
