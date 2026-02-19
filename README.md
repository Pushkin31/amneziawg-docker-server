# AmneziaWG Server

Docker-based AmneziaWG server with automatic configuration and traffic obfuscation for bypassing DPI (Deep Packet Inspection).

## Features

- **🔐 Auto-initialization** - Keys and config generated automatically on first start
- **🎭 Traffic Obfuscation** - DPI bypass with configurable junk packets
- **🐳 Docker-based** - One-command deployment
- **👥 Client Management** - Python scripts with key validation and race condition protection
- **🔄 Idempotent** - Safe restarts without losing configuration
- **🛡️ Secure** - PresharedKeys for quantum resistance, proper key handling via stdin
- **🔧 MSS Clamping** - Automatic MTU optimization for mobile networks
- **⚙️ Environment-based Config** - Easy configuration using .env file
- **📱 QR Code Generation** - Direct QR code generation for mobile clients

## Quick Start

### 1. Configure

Create `.env` file with your settings:

```bash
cp .env.example .env
# Edit the values in .env
nano .env
```

Required settings:
- `SERVER_IP`: Your server's public IP address
- `LISTEN_PORT`: UDP port for WireGuard (default: 51821)
- `VPN_NETWORK`: VPN subnet (default: 10.201.0.0/24)
- `EXT_INTERFACE`: External network interface (default: eth0)

**Important**: Check your external interface name with `ip route get 8.8.8.8`

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
├── .env                    # ← Configuration (EDIT THIS!)
├── docker-compose.yml      # Docker configuration
├── Dockerfile              # Build image
├── Makefile                # Management commands
├── config/                 # Auto-generated (in .gitignore)
│   ├── server.conf        # Server config (auto-created)
│   ├── server.keys        # Server keys (auto-created)
│   └── clients/           # Client configs
│       └── laptop/
│           └── laptop.conf
└── scripts/               # Python scripts for reliability
    ├── entrypoint.py      # Auto-init logic
    ├── add-client.py      # Add client
    ├── remove-client.py   # Remove client
    ├── list-clients.py    # List clients
    └── show-qr.py         # Show QR code for mobile
```

## Configuration

### Server Settings

Create `.env` file with your settings (use `.env.example` as template):

```bash
# Copy example file
cp .env.example .env
# Edit the values in .env
nano .env
```

**.env example:**
```env
# Server network settings
SERVER_IP=your_server_ip_here
LISTEN_PORT=51821
VPN_NETWORK=10.201.0.0/24
EXT_INTERFACE=eth0

# AmneziaWG obfuscation parameters
AWG_JC=4
AWG_JMIN=40
AWG_JMAX=70
AWG_S1=0
AWG_S2=0
AWG_S3=0
AWG_S4=0
AWG_H1=1
AWG_H2=2
AWG_H3=3
AWG_H4=4
AWG_I1=1
AWG_I2=2
AWG_I3=3
AWG_I4=4
AWG_I5=5

# Container settings
LOG_LEVEL=info
INTERFACE=awg0
DNS=1.1.1.1
```

**Important**: All clients MUST use the same obfuscation parameters!

### Obfuscation Parameters

AmneziaWG supports advanced obfuscation parameters:
- `AWG_JC`: Junk packets count (1-128)
- `AWG_JMIN/JMAX`: Min/max junk packet sizes
- `AWG_S1-S4`: Handshake garbage parameters
- `AWG_H1-H4`: Header parameters
- `AWG_I1-I5`: Additional header parameters

### Obfuscation Presets

| Preset | Jc | Jmin | Jmax | S1-S4 | H1-H4 | I1-I5 | Use Case |
|--------|----|----|------|-------|-------|-------|----------|
| Light | 4 | 40 | 70 | 0 | 1,2,3,4 | 1,2,3,4,5 | Low overhead, good for mobile |
| **Medium** | 4 | 50 | 1000 | 0 | 1,2,3,4 | 1,2,3,4,5 | **Recommended** |
| Heavy | 10 | 50 | 1000 | 0 | 1,2,3,4 | 1,2,3,4,5 | Maximum stealth |
| None | 0 | 0 | 0 | 0 | 0 | 0 | Standard WireGuard |

### Network Configuration

- **LISTEN_PORT**: Default 51821 (changed from 12235 to avoid conflicts)
- **VPN_NETWORK**: Default 10.201.0.0/24
- **EXT_INTERFACE**: Usually eth0 (check with `ip route get 8.8.8.8`)
- **DNS**: DNS for clients (default: 1.1.1.1)

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
make show-qr NAME=laptop        # Show QR code for mobile

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
1. Generate client keys (validated to 44 chars, passed via stdin)
2. Assign IP automatically (10.8.0.2, 10.8.0.3, etc.)
3. Copy obfuscation params from server
4. Set MTU to 1280 for better compatibility
5. Create `config/clients/mylaptop/mylaptop.conf`
6. Add peer to server config
7. Automatically restart server to apply changes

### Get Client Config

**Option 1: Show QR Code (for mobile)**

```bash
make show-qr NAME=mylaptop
```

Scan the QR code with your phone's camera using AmneziaWG mobile app.

**Option 2: Get config file (for desktop)**

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
2. `entrypoint.py` checks if `config/server.keys` exists
3. **If not** → generates keys with `awg genkey` (via stdin, validated to 44 chars)
4. Checks if `config/server.conf` exists
5. **If not** → creates config from `docker-compose.yml` environment
6. Starts WireGuard interface

### Subsequent Starts

1. `entrypoint.py` finds existing `config/server.keys` → **skips generation**
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

Open UDP port on firewall (default 51821):

```bash
# UFW
sudo ufw allow 51821/udp

# iptables
sudo iptables -A INPUT -p udp --dport 51821 -j ACCEPT

# Check if port is listening
sudo ss -ulpn | grep 51821
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

```env
# .env
LOG_LEVEL=debug
```

Then:
```bash
make restart && make logs
```

### MSS Clamping

The server automatically applies MSS clamping for better mobile network compatibility:

```bash
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
```

This fixes MTU issues on mobile networks and improves connection stability.

### Additional Obfuscation Parameters

AmneziaWG supports extended obfuscation parameters:
- `AWG_S3`, `AWG_S4`: Additional handshake garbage
- `AWG_I1-I5`: Extended header parameters

These are automatically applied to both server and client configurations.

### Custom DNS

```yaml
environment:
  - DNS=9.9.9.9  # Quad9
  # or
  - DNS=8.8.8.8  # Google
```

### MTU Settings

Client configs are automatically generated with `MTU = 1280` for better compatibility with various networks and to avoid fragmentation issues with AmneziaWG's obfuscation overhead.

If you experience connectivity issues, you can adjust MTU in client configs:
```ini
# Lower MTU for problematic networks
MTU = 1200

# Or higher for fast networks without fragmentation
MTU = 1420
```

**Note**: Server MTU is managed automatically by the kernel.

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

## QR Codes for Mobile Clients

The server includes QR code generation for easy mobile setup:

```bash
# Show QR code in terminal
make show-qr NAME=mylaptop
```

The script uses Python qrcode library (pre-installed in Docker) to generate ASCII QR codes directly in your terminal.

Simply scan the QR code with AmneziaWG mobile app to import the configuration.

## Security Notes

1. **Keep `config/` secure** - Contains private keys
2. **Don't commit `config/`** - Already in `.gitignore`
3. **Use strong obfuscation** in censored regions
4. **Regular updates**: `git pull && make build && make restart`
5. **Firewall**: Only open necessary ports
6. **Key validation** - All keys are validated to be exactly 44 characters
7. **Environment security** - Keep `.env` file secure with sensitive configuration
8. **Userspace implementation** - Uses `WG_I_PREFER_BUGGY_USERSPACE_TO_POLISHED_KERNEL=1` for compatibility

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
