#!/bin/bash

set -e

# Configuration
CONFIG_DIR="./config"
SERVER_CONFIG="${CONFIG_DIR}/server.conf"
SERVER_KEYS="${CONFIG_DIR}/server.keys"
CLIENTS_DIR="${CONFIG_DIR}/clients"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ $# -ne 1 ]; then
    echo -e "${RED}Usage: $0 <client-name>${NC}"
    echo "Example: $0 laptop"
    exit 1
fi

CLIENT_NAME="$1"
CLIENT_DIR="${CLIENTS_DIR}/${CLIENT_NAME}"

# Check if server is initialized
if [ ! -f "$SERVER_CONFIG" ]; then
    echo -e "${RED}ERROR: Server not initialized!${NC}"
    echo "Please start the server first: docker-compose up -d"
    echo "This will auto-generate the configuration."
    exit 1
fi

# Check if client already exists
if [ -d "$CLIENT_DIR" ]; then
    echo -e "${RED}ERROR: Client '$CLIENT_NAME' already exists!${NC}"
    exit 1
fi

# Create client directory
mkdir -p "$CLIENT_DIR"

# Get VPN network from server config
VPN_NETWORK=$(grep '^Address' "$SERVER_CONFIG" | awk '{print $3}' | sed 's/\.[0-9]*\/.*$//')

# Find next available IP
echo -e "${YELLOW}Finding next available IP...${NC}"
LAST_IP=$(grep -oP 'AllowedIPs = '"${VPN_NETWORK}"'\.\K[0-9]+' "$SERVER_CONFIG" 2>/dev/null | sort -n | tail -1)
if [ -z "$LAST_IP" ] || [ "$LAST_IP" -lt 2 ]; then
    CLIENT_IP="${VPN_NETWORK}.2"
else
    CLIENT_IP="${VPN_NETWORK}.$((LAST_IP + 1))"
fi

echo -e "${GREEN}Assigned IP: ${CLIENT_IP}${NC}"

# Generate keys
echo -e "${YELLOW}Generating client keys...${NC}"

CLIENT_PRIVATE_KEY=$(docker exec amneziawg-server awg genkey)
CLIENT_PUBLIC_KEY=$(printf "%s" "$CLIENT_PRIVATE_KEY" | docker exec -i amneziawg-server awg pubkey)
PRESHARED_KEY=$(docker exec amneziawg-server awg genpsk)

# Save keys
echo "$CLIENT_PRIVATE_KEY" > "${CLIENT_DIR}/privatekey"
echo "$CLIENT_PUBLIC_KEY" > "${CLIENT_DIR}/publickey"
echo "$PRESHARED_KEY" > "${CLIENT_DIR}/presharedkey"
chmod 600 "${CLIENT_DIR}"/*

# Get server public key
if [ -f "$SERVER_KEYS" ]; then
    SERVER_PUBLIC_KEY=$(grep '^PUBLIC_KEY' "$SERVER_KEYS" | cut -d'=' -f2)
else
    # Fallback: derive from private key in config
    SERVER_PRIVATE_KEY=$(grep '^PrivateKey' "$SERVER_CONFIG" | awk '{print $3}')
    SERVER_PUBLIC_KEY=$(printf "%s" "$SERVER_PRIVATE_KEY" | docker exec -i amneziawg-server awg pubkey)
fi

# Read server settings from docker-compose environment or use defaults
SERVER_ENDPOINT=$(docker exec amneziawg-server printenv SERVER_IP || echo "YOUR_SERVER_IP")
LISTEN_PORT=$(docker exec amneziawg-server printenv LISTEN_PORT || echo "51820")
DNS=$(docker exec amneziawg-server printenv DNS || echo "1.1.1.1")

# Read AmneziaWG parameters from server config
JC=$(grep '^Jc' "$SERVER_CONFIG" | awk '{print $3}' || echo "4")
JMIN=$(grep '^Jmin' "$SERVER_CONFIG" | awk '{print $3}' || echo "50")
JMAX=$(grep '^Jmax' "$SERVER_CONFIG" | awk '{print $3}' || echo "1000")
S1=$(grep '^S1' "$SERVER_CONFIG" | awk '{print $3}' || echo "0")
S2=$(grep '^S2' "$SERVER_CONFIG" | awk '{print $3}' || echo "0")
H1=$(grep '^H1' "$SERVER_CONFIG" | awk '{print $3}' || echo "1")
H2=$(grep '^H2' "$SERVER_CONFIG" | awk '{print $3}' || echo "2")
H3=$(grep '^H3' "$SERVER_CONFIG" | awk '{print $3}' || echo "3")
H4=$(grep '^H4' "$SERVER_CONFIG" | awk '{print $3}' || echo "4")

# Create client config
cat > "${CLIENT_DIR}/${CLIENT_NAME}.conf" <<EOF
[Interface]
PrivateKey = ${CLIENT_PRIVATE_KEY}
Address = ${CLIENT_IP}/32
DNS = ${DNS}

# AmneziaWG obfuscation parameters (must match server!)
Jc = ${JC}
Jmin = ${JMIN}
Jmax = ${JMAX}
S1 = ${S1}
S2 = ${S2}
H1 = ${H1}
H2 = ${H2}
H3 = ${H3}
H4 = ${H4}

[Peer]
PublicKey = ${SERVER_PUBLIC_KEY}
PresharedKey = ${PRESHARED_KEY}
Endpoint = ${SERVER_ENDPOINT}:${LISTEN_PORT}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
EOF

# Add peer to server config
cat >> "$SERVER_CONFIG" <<EOF

[Peer]
# Client: ${CLIENT_NAME}
PublicKey = ${CLIENT_PUBLIC_KEY}
PresharedKey = ${PRESHARED_KEY}
AllowedIPs = ${CLIENT_IP}/32
EOF

echo ""
echo -e "${GREEN}✓ Client '${CLIENT_NAME}' created successfully!${NC}"
echo ""
echo -e "${YELLOW}Client configuration:${NC}"
echo "  - Config file: ${CLIENT_DIR}/${CLIENT_NAME}.conf"
echo "  - IP address: ${CLIENT_IP}"
echo "  - Public key: ${CLIENT_PUBLIC_KEY}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Restart the server: docker-compose restart"
echo "2. Send the config to client: ${CLIENT_DIR}/${CLIENT_NAME}.conf"
echo ""
