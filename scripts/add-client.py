#!/usr/bin/env python3

import sys
import os
import subprocess
import re
import fcntl

def run_cmd_with_input(cmd, stdin_data=None):
    """Execute command with optional stdin, return stdout stripped"""
    result = subprocess.run(
        cmd,
        input=stdin_data,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"ERROR: Command failed: {' '.join(cmd)}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout.strip()

def main():
    if len(sys.argv) != 2:
        print("Usage: add-client.py <client-name>")
        sys.exit(1)

    client_name = sys.argv[1]
    # Paths are relative to WORKDIR inside container
    config_dir = "/etc/amnezia/amneziawg/config"
    server_config = f"{config_dir}/server.conf"
    server_keys = f"{config_dir}/server.keys"
    clients_dir = f"{config_dir}/clients"
    client_dir = f"{clients_dir}/{client_name}"

    # Check if server is initialized
    if not os.path.exists(server_config):
        print("ERROR: Server not initialized!")
        print("Please start the server first.")
        sys.exit(1)

    # Check if client already exists
    if os.path.exists(client_dir):
        print(f"ERROR: Client '{client_name}' already exists!")
        sys.exit(1)

    # Lock file to prevent race conditions
    lock_file = f"{config_dir}/.add-client.lock"
    # Ensure config dir exists
    os.makedirs(config_dir, exist_ok=True)

    lock_fd = open(lock_file, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        # Create client directory
        os.makedirs(client_dir, mode=0o700, exist_ok=True)

        # Read server config
        with open(server_config, 'r') as f:
            server_conf = f.read()

        # Extract VPN network from Address line (e.g., "10.201.0.1/24" -> "10.201.0")
        address_match = re.search(r'Address\s*=\s*(\d+\.\d+\.\d+)\.\d+/\d+', server_conf)
        if not address_match:
            print("ERROR: Cannot parse VPN network from server config")
            sys.exit(1)

        vpn_network = address_match.group(1)

        # Find next available IP
        print("Finding next available IP...")
        existing_ips = re.findall(rf'AllowedIPs\s*=\s*{re.escape(vpn_network)}\.(\d+)/32', server_conf)
        if existing_ips:
            last_ip = max(int(ip) for ip in existing_ips)
            client_ip_num = max(last_ip + 1, 2)
        else:
            client_ip_num = 2

        client_ip = f"{vpn_network}.{client_ip_num}"
        print(f"Assigned IP: {client_ip}")

        # Generate keys using local awg command
        print("Generating client keys...")

        # Generate private key
        client_private = run_cmd_with_input(['awg', 'genkey'])

        # Generate public key from private (pass via stdin)
        client_public = run_cmd_with_input(
            ['awg', 'pubkey'],
            stdin_data=client_private
        )

        # Generate preshared key
        preshared = run_cmd_with_input(['awg', 'genpsk'])

        # Validate key lengths
        if len(client_private) != 44:
            print(f"ERROR: Invalid private key length: {len(client_private)}")
            sys.exit(1)
        if len(client_public) != 44:
            print(f"ERROR: Invalid public key length: {len(client_public)}")
            sys.exit(1)
        if len(preshared) != 44:
            print(f"ERROR: Invalid preshared key length: {len(preshared)}")
            sys.exit(1)

        # Save keys
        with open(f"{client_dir}/privatekey", 'w') as f:
            f.write(client_private)
        with open(f"{client_dir}/publickey", 'w') as f:
            f.write(client_public)
        with open(f"{client_dir}/presharedkey", 'w') as f:
            f.write(preshared)

        os.chmod(f"{client_dir}/privatekey", 0o600)
        os.chmod(f"{client_dir}/publickey", 0o600)
        os.chmod(f"{client_dir}/presharedkey", 0o600)

        # Get server public key
        server_public = ""
        if os.path.exists(server_keys):
            with open(server_keys, 'r') as f:
                keys_content = f.read()
            for line in keys_content.split('\n'):
                if line.strip().startswith('PUBLIC_KEY='):
                    server_public = line.split('=', 1)[1].strip()
                    break

        if not server_public or len(server_public) != 44:
            # Fallback: derive from private key in config
            private_match = re.search(r'PrivateKey\s*=\s*(\S+)', server_conf)
            if not private_match:
                print("ERROR: Cannot find server private key")
                sys.exit(1)
            server_private = private_match.group(1).strip()
            server_public = run_cmd_with_input(
                ['awg', 'pubkey'],
                stdin_data=server_private
            )

        # Get server settings from environment (inside container)
        server_ip = os.getenv('SERVER_IP', 'YOUR_SERVER_IP')
        listen_port = os.getenv('LISTEN_PORT', '51820')
        dns = os.getenv('DNS', '1.1.1.1')

        # Extract obfuscation parameters from server config
        # Default to 0 if not found, but try to parse
        obf_params = {
            'Jc': '4', 'Jmin': '50', 'Jmax': '1000',
            'S1': '0', 'S2': '0', 'S3': '0', 'S4': '0',
            'H1': '1', 'H2': '2', 'H3': '3', 'H4': '4',
            'I1': '0', 'I2': '0', 'I3': '0', 'I4': '0', 'I5': '0'
        }

        for param in obf_params.keys():
            match = re.search(rf'^\s*{param}\s*=\s*(\d+)', server_conf, re.MULTILINE)
            if match:
                obf_params[param] = match.group(1)

        # Create client config (AmneziaWG format)
        client_config = f"""[Interface]
PrivateKey = {client_private}
Address = {client_ip}/32
DNS = {dns}
MTU = 1280
Jc = {obf_params['Jc']}
Jmin = {obf_params['Jmin']}
Jmax = {obf_params['Jmax']}
S1 = {obf_params['S1']}
S2 = {obf_params['S2']}
S3 = {obf_params['S3']}
S4 = {obf_params['S4']}
H1 = {obf_params['H1']}
H2 = {obf_params['H2']}
H3 = {obf_params['H3']}
H4 = {obf_params['H4']}

[Peer]
PublicKey = {server_public}
PresharedKey = {preshared}
Endpoint = {server_ip}:{listen_port}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""

        with open(f"{client_dir}/{client_name}.conf", 'w') as f:
            f.write(client_config)

        os.chmod(f"{client_dir}/{client_name}.conf", 0o600)

        # Add peer to server config
        peer_config = f"""
[Peer]
# Client: {client_name}
PublicKey = {client_public}
PresharedKey = {preshared}
AllowedIPs = {client_ip}/32
"""
        with open(server_config, 'a') as f:
            f.write(peer_config)

        # Determine interface name (awg-quick uses config filename as interface name)
        # Config is at /etc/amnezia/amneziawg/config/server.conf, so interface is likely "server"
        # But we check INTERFACE env var too
        env_interface = os.getenv('INTERFACE', 'awg0')

        # Check which interface is actually running
        active_interface = "server" # Default fallback
        try:
            # Check if env_interface exists
            check = subprocess.run(['ip', 'link', 'show', env_interface], capture_output=True)
            if check.returncode == 0:
                active_interface = env_interface
            else:
                # Check if "server" interface exists
                check = subprocess.run(['ip', 'link', 'show', 'server'], capture_output=True)
                if check.returncode == 0:
                    active_interface = 'server'
        except Exception:
            pass

        print(f"Adding peer to running interface ({active_interface})...")
        # Create a temporary config file for the new peer only
        temp_peer_config = f"/tmp/new_peer_{client_name}.conf"
        with open(temp_peer_config, 'w') as f:
            f.write(peer_config)

        # Use addconf to append the new peer configuration
        subprocess.run(['awg', 'addconf', active_interface, temp_peer_config], check=False)
        os.remove(temp_peer_config)

        print()
        print(f"✓ Client '{client_name}' created successfully!")
        print(f"  Config: {client_dir}/{client_name}.conf")
        print(f"  IP: {client_ip}")

    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

if __name__ == "__main__":
    main()
