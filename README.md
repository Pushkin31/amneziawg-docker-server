# AmneziaWG Server

Docker-based AmneziaWG server with automatic configuration and traffic obfuscation for bypassing DPI (Deep Packet Inspection).

## Features

- **🔐 Auto-initialization** - Keys and config generated automatically on first start
- **🎭 Traffic Obfuscation** - DPI bypass with configurable junk packets
- **🐳 Docker-based** - One-command deployment
- **👥 Client Management** - Simple scripts for adding/removing clients
- **🔄 Idempotent** - Safe restarts without losing configuration
- **🛡️ Secure** - PresharedKeys for quantum resistance

## Quick Start

### 1. Configure

Edit settings in `docker-compose.yml`:

```yaml
environment:
  - SERVER_IP=YOUR_PUBLIC_IP     # ← Change this!
  - LISTEN_PORT=51820
  - VPN_NETWORK=10.8.0.0/24
```

### 2. Deploy

```bash
make build    # Build image
make start    # Start server (auto-generates config)
```

### 3. Add Clients

```bash
make add-client NAME=laptop
make restart
```

### 4. Get Client Config

```bash
cat config/clients/laptop/laptop.conf
```

Send this file to your client!

## File Structure

```
.
├── docker-compose.yml      # ← Configuration (EDIT THIS!)
├── Dockerfile              # Build image
├── Makefile                # Management commands
├── config/                 # Auto-generated (in .gitignore)
│   ├── server.conf        # Server config (auto-created)
│   ├── server.keys        # Server keys (auto-created)
│   └── clients/           # Client configs
│       └── laptop/
│           └── laptop.conf
└── scripts/
    ├── entrypoint.sh      # Auto-init logic
    ├── add-client.sh      # Add client
    ├── list-clients.sh    # List clients
    └── remove-client.sh   # Remove client
```

## Configuration

### Server Settings

Edit `docker-compose.yml`:

```yaml
environment:
  # Server network settings
  - SERVER_IP=1.2.3.4              # Your server's public IP
  - LISTEN_PORT=51820              # UDP port
  - VPN_NETWORK=10.8.0.0/24       # VPN subnet
  - EXT_INTERFACE=eth0             # External interface for NAT

  # AmneziaWG obfuscation parameters
  - AWG_JC=4                       # Junk packets (1-128)
  - AWG_JMIN=50                    # Min junk size
  - AWG_JMAX=1000                  # Max junk size (max 1280)
  - AWG_S1=0                       # Handshake init garbage
  - AWG_S2=0                       # Handshake response garbage
  - AWG_H1=1                       # Header params
  - AWG_H2=2
  - AWG_H3=3
  - AWG_H4=4
```

**Important**: All clients MUST use the same obfuscation parameters!

### Obfuscation Presets

| Preset | Jc | Jmin | Jmax | Use Case |
|--------|----|----|------|----------|
| Light | 3 | 40 | 70 | Low overhead |
| **Medium** | 4 | 50 | 1000 | **Recommended** |
| Heavy | 10 | 50 | 1000 | Maximum stealth |
| None | 0 | 0 | 0 | Standard WireGuard |

## Management Commands

```bash
# Setup
make build             # Build Docker image
make start             # Start server (auto-init)

# Operations
make stop              # Stop server
make restart           # Restart server
make logs              # View logs
make status            # Show status and peers

# Clients
make clients                    # List all clients
make add-client NAME=laptop     # Add client
make remove-client NAME=laptop  # Remove client

# Maintenance
make clean             # Remove all configs (DANGEROUS!)
```

## Client Management

### Add Client

```bash
make add-client NAME=mylaptop
make restart
```

This will:
1. Generate client keys
2. Assign IP automatically (10.8.0.2, 10.8.0.3, etc.)
3. Copy obfuscation params from server
4. Create `config/clients/mylaptop/mylaptop.conf`
5. Add peer to server config

### Get Client Config

```bash
# View config
cat config/clients/mylaptop/mylaptop.conf

# Copy to clipboard (Linux)
cat config/clients/mylaptop/mylaptop.conf | xclip -selection clipboard

# Copy to clipboard (macOS)
cat config/clients/mylaptop/mylaptop.conf | pbcopy
```

Send this config to your client device.

### Remove Client

```bash
make remove-client NAME=mylaptop
make restart
```

### List Clients

```bash
make clients
```

Output:
```
Client: laptop
  IP: 10.8.0.2/32
  Public Key: abc123...

Client: phone
  IP: 10.8.0.3/32
  Public Key: def456...
```

## How It Works

### First Start

1. You run `make start`
2. `entrypoint.sh` checks if `config/server.keys` exists
3. **If not** → generates keys with `awg genkey`
4. Checks if `config/server.conf` exists
5. **If not** → creates config from `docker-compose.yml` environment
6. Starts WireGuard interface

### Subsequent Starts

1. `entrypoint.sh` finds existing `config/server.keys` → **skips generation**
2. Finds existing `config/server.conf` → **skips creation**
3. Uses existing config
4. **Keys and peers preserved!**

This means:
- ✅ Safe to restart
- ✅ Keys never change
- ✅ Clients stay connected
- ✅ Configuration persists

## Networking

### Port Forwarding

Open UDP port on firewall:

```bash
# UFW
sudo ufw allow 51820/udp

# iptables
sudo iptables -A INPUT -p udp --dport 51820 -j ACCEPT

# Check if port is listening
sudo ss -ulpn | grep 51820
```

### NAT Configuration

If your external interface is not `eth0`:

```bash
# Find your interface
ip route | grep default

# Update docker-compose.yml
- EXT_INTERFACE=ens3  # or whatever your interface is
```

## Troubleshooting

### Server doesn't start

**Check logs:**
```bash
make logs
```

**Common issues:**
- Missing `/dev/net/tun` → Add to docker-compose (already included)
- Port in use → Change `LISTEN_PORT`
- Wrong interface → Check `EXT_INTERFACE`

### Clients can't connect

**1. Verify obfuscation params match:**
```bash
grep -E "^(Jc|Jmin|Jmax)" config/server.conf
grep -E "^(Jc|Jmin|Jmax)" config/clients/laptop/laptop.conf
```

**2. Check server endpoint:**
```bash
grep Endpoint config/clients/laptop/laptop.conf
# Should show: Endpoint = YOUR_SERVER_IP:51820
```

**3. Verify firewall:**
```bash
sudo ss -ulpn | grep 51820
```

### No internet on client

**1. Check IP forwarding:**
```bash
docker exec amneziawg-server sysctl net.ipv4.ip_forward
# Should return: net.ipv4.ip_forward = 1
```

**2. Verify NAT:**
```bash
docker exec amneziawg-server iptables -t nat -L POSTROUTING
```

**3. Check AllowedIPs in client config:**
```bash
grep AllowedIPs config/clients/laptop/laptop.conf
# Should be: AllowedIPs = 0.0.0.0/0, ::/0
```

### Config not updating after changing docker-compose.yml

**Reason**: Config already exists, won't be overwritten

**Solution**:
```bash
# Option 1: Recreate config
rm config/server.conf
make restart

# Option 2: Edit manually
nano config/server.conf
make restart
```

### Keys lost after restart

**This should NEVER happen!**

Keys are stored in `./config` which is mounted as a volume.

**If it happens anyway:**
```bash
# Restore from backup
tar xzf backup.tar.gz

# Or check if volume still exists
docker volume ls
docker inspect amneziawg-server
```

## Advanced

### Debug Mode

Enable verbose logging:

```yaml
# docker-compose.yml
environment:
  - LOG_LEVEL=debug  # ← Change this
```

Then:
```bash
make restart && make logs
```

### Custom DNS

```yaml
environment:
  - DNS=9.9.9.9  # Quad9
  # or
  - DNS=8.8.8.8  # Google
```

### IPv6 Support

**In `docker-compose.yml`:**
```yaml
environment:
  - VPN_NETWORK=10.8.0.0/24,fd00::/64
```

**Then edit** `config/server.conf`:
```ini
Address = 10.8.0.1/24, fd00::1/64
```

**Client configs will need:**
```ini
AllowedIPs = 0.0.0.0/0, ::/0
```

### Split Tunnel

To route only specific traffic through VPN:

**Edit client config:**
```ini
# Only route 10.0.0.0/8 through VPN
AllowedIPs = 10.0.0.0/8
```

### Backup

```bash
# Backup config
tar czf amneziawg-backup-$(date +%Y%m%d).tar.gz config/

# Restore
tar xzf amneziawg-backup-20250103.tar.gz
make start
```

### Migration

**Old server:**
```bash
tar czf config-backup.tar.gz config/
scp config-backup.tar.gz newserver:/opt/gitrepo/amneziaWG-server/
```

**New server:**
```bash
tar xzf config-backup.tar.gz
make build && make start
```

## Security Notes

1. **Keep `config/` secure** - Contains private keys
2. **Don't commit `config/`** - Already in `.gitignore`
3. **Use strong obfuscation** in censored regions
4. **Regular updates**: `git pull && make build && make restart`
5. **Firewall**: Only open necessary ports

## Requirements

- Docker 20.10+
- Docker Compose 1.29+
- Linux kernel with TUN/TAP support
- Public IP or port forwarding
- UDP port accessible from internet

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## Testing

See [TESTING.md](TESTING.md) for test results.

## References

- [AmneziaVPN Official](https://amnezia.org/)
- [amneziawg-go](https://github.com/amnezia-vpn/amneziawg-go)
- [WireGuard](https://www.wireguard.com/)

## License

This project follows the licensing of amneziawg-go and WireGuard.
