#!/bin/bash

set -e

CONFIG_DIR="./config"
SERVER_CONFIG="${CONFIG_DIR}/server.conf"
CLIENTS_DIR="${CONFIG_DIR}/clients"

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

if [ ! -d "$CLIENT_DIR" ]; then
    echo -e "${RED}ERROR: Client '$CLIENT_NAME' not found!${NC}"
    exit 1
fi

# Get client public key
CLIENT_PUBLIC_KEY=$(cat "${CLIENT_DIR}/publickey")

echo -e "${YELLOW}Removing client: ${CLIENT_NAME}${NC}"
echo "Public key: ${CLIENT_PUBLIC_KEY}"

# Remove client section from server config (including [Peer] header)
# Find and remove the entire [Peer] block that contains this client
awk -v client="$CLIENT_NAME" '
    BEGIN { in_peer=0; skip=0; buffer="" }
    /^\[Peer\]/ {
        in_peer=1;
        skip=0;
        buffer=$0"\n"
        next
    }
    in_peer && /^# Client:/ {
        if ($0 ~ client) {
            skip=1
        }
        buffer=buffer$0"\n"
        next
    }
    in_peer && /^$/ {
        if (!skip) {
            printf "%s", buffer
        }
        in_peer=0
        skip=0
        buffer=""
        print
        next
    }
    in_peer {
        buffer=buffer$0"\n"
        next
    }
    { print }
' "$SERVER_CONFIG" > "${SERVER_CONFIG}.tmp" && mv "${SERVER_CONFIG}.tmp" "$SERVER_CONFIG"

# Remove client directory
rm -rf "$CLIENT_DIR"

echo -e "${GREEN}✓ Client '${CLIENT_NAME}' removed successfully!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "Restart the server: docker-compose restart"
echo ""
