#!/usr/bin/env python3

import os
import sys
import subprocess
import time
import signal

def run_cmd_with_input(cmd, stdin_data=None):
    """Execute command with optional stdin, return stdout stripped"""
    result = subprocess.run(
        cmd,
        input=stdin_data,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"ERROR: Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()

def run_cmd(cmd, check=True):
    """Execute shell command"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"ERROR: Command failed: {cmd}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip(), result.returncode

def log(msg):
    """Print log message"""
    print(msg, flush=True)

def main():
    interface = os.getenv('INTERFACE', 'awg0')
    config_dir = "/etc/amnezia/amneziawg/config"
    config_file = f"{config_dir}/server.conf"
    keys_file = f"{config_dir}/server.keys"

    log("========================================")
    log("  AmneziaWG Server")
    log("========================================")
    log("")

    # Create config directory
    os.makedirs(config_dir, mode=0o755, exist_ok=True)
    os.makedirs(f"{config_dir}/clients", mode=0o755, exist_ok=True)

    # Generate keys if they don't exist
    if not os.path.exists(keys_file):
        log("Generating server keys...")

        # Generate private key
        private_key = run_cmd_with_input(['awg', 'genkey'])

        # Generate public key from private (pass via stdin)
        public_key = run_cmd_with_input(['awg', 'pubkey'], stdin_data=private_key)

        with open(keys_file, 'w') as f:
            f.write(f"PRIVATE_KEY={private_key}\n")
            f.write(f"PUBLIC_KEY={public_key}\n")

        os.chmod(keys_file, 0o600)
        log(f"✓ Keys generated and saved to {keys_file}")
    else:
        log(f"✓ Using existing keys from {keys_file}")

    # Create server config if it doesn't exist
    if not os.path.exists(config_file):
        log("Creating server configuration...")

        # Load keys
        keys = {}
        with open(keys_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    keys[key] = value

        # Get environment variables
        vpn_network = os.getenv('VPN_NETWORK', '10.8.0.0/24')

        # Parse VPN network properly (e.g., "10.201.0.0/24" -> "10.201.0.1/24")
        if '/' in vpn_network:
            network_base, mask = vpn_network.split('/')
            octets = network_base.split('.')
            # Replace last octet with 1 for server IP
            server_vip = '.'.join(octets[:3] + ['1']) + '/' + mask
        else:
            log("ERROR: VPN_NETWORK must be in CIDR format (e.g., 10.8.0.0/24)")
            sys.exit(1)

        listen_port = os.getenv('LISTEN_PORT', '51820')
        ext_interface = os.getenv('EXT_INTERFACE', 'eth0')
        dns = os.getenv('DNS', '1.1.1.1')

        # Obfuscation parameters
        awg_jc = os.getenv('AWG_JC', '4')
        awg_jmin = os.getenv('AWG_JMIN', '50')
        awg_jmax = os.getenv('AWG_JMAX', '1000')
        awg_s1 = os.getenv('AWG_S1', '0')
        awg_s2 = os.getenv('AWG_S2', '0')
        awg_s3 = os.getenv('AWG_S3', '0')
        awg_s4 = os.getenv('AWG_S4', '0')
        awg_h1 = os.getenv('AWG_H1', '1')
        awg_h2 = os.getenv('AWG_H2', '2')
        awg_h3 = os.getenv('AWG_H3', '3')
        awg_h4 = os.getenv('AWG_H4', '4')
        awg_i1 = os.getenv('AWG_I1', '0')
        awg_i2 = os.getenv('AWG_I2', '0')
        awg_i3 = os.getenv('AWG_I3', '0')
        awg_i4 = os.getenv('AWG_I4', '0')
        awg_i5 = os.getenv('AWG_I5', '0')

        config_content = f"""# AmneziaWG Server Configuration
# Auto-generated on {time.strftime('%c')}

[Interface]
# Server's private key
PrivateKey = {keys['PRIVATE_KEY']}

# Server's VPN IP address
Address = {server_vip}

# UDP port for AmneziaWG
ListenPort = {listen_port}

# AmneziaWG obfuscation parameters
# WARNING: These MUST match on ALL clients!
Jc = {awg_jc}
Jmin = {awg_jmin}
Jmax = {awg_jmax}
S1 = {awg_s1}
S2 = {awg_s2}
S3 = {awg_s3}
S4 = {awg_s4}
H1 = {awg_h1}
H2 = {awg_h2}
H3 = {awg_h3}
H4 = {awg_h4}
I1 = {awg_i1}
I2 = {awg_i2}
I3 = {awg_i3}
I4 = {awg_i4}
I5 = {awg_i5}

# NAT and routing
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o {ext_interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {ext_interface} -j MASQUERADE

# DNS for clients
DNS = {dns}


### Clients (Peers)
### Managed automatically - do not edit manually

"""

        with open(config_file, 'w') as f:
            f.write(config_content)

        os.chmod(config_file, 0o600)
        log(f"✓ Server config created: {config_file}")
    else:
        log(f"✓ Using existing config: {config_file}")

    # Load keys for display
    keys = {}
    with open(keys_file, 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                keys[key] = value

    server_ip = os.getenv('SERVER_IP', 'YOUR_SERVER_IP')
    listen_port = os.getenv('LISTEN_PORT', '51820')
    vpn_network = os.getenv('VPN_NETWORK', '10.8.0.0/24')
    awg_jc = os.getenv('AWG_JC', '4')
    awg_jmin = os.getenv('AWG_JMIN', '50')
    awg_jmax = os.getenv('AWG_JMAX', '1000')

    log("")
    log("Server Configuration:")
    log(f"  Interface: {interface}")
    log(f"  Endpoint: {server_ip}:{listen_port}")
    log(f"  VPN Network: {vpn_network}")
    log(f"  Public Key: {keys.get('PUBLIC_KEY', 'N/A')}")
    log(f"  Obfuscation: Jc={awg_jc}, Jmin={awg_jmin}, Jmax={awg_jmax}")
    log("")

    # Set up IP forwarding (ignore errors in host network mode)
    log("Enabling IP forwarding...")
    run_cmd("sysctl -w net.ipv4.ip_forward=1 2>/dev/null || true", check=False)
    run_cmd("sysctl -w net.ipv6.conf.all.forwarding=1 2>/dev/null || true", check=False)

    # Load kernel modules if possible
    if os.path.exists('/lib/modules'):
        run_cmd("modprobe -q tun || true", check=False)
        run_cmd("modprobe -q wireguard || true", check=False)

    # Add MSS clamping for mobile networks (fixes MTU issues)
    log("Configuring MSS clamping for mobile network compatibility...")
    run_cmd("iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu", check=False)

    # Start AmneziaWG interface
    log(f"Starting interface {interface}...")
    stdout, rc = run_cmd(f"awg-quick up {config_file}")
    if rc != 0:
        log("ERROR: Failed to start interface")
        sys.exit(1)

    log("")
    log("✓ AmneziaWG Server started successfully!")
    log("")
    log("Interface status:")
    stdout, rc = run_cmd("awg show", check=False)
    if rc == 0 and stdout:
        log(stdout)
    else:
        log("  Interface is up")
    log("")

    # Signal handler for graceful shutdown
    def signal_handler(signum, frame):
        log("Shutting down...")
        run_cmd(f"awg-quick down {config_file}", check=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Log interface stats periodically
    log_level = os.getenv('LOG_LEVEL', 'info')
    while True:
        time.sleep(300)  # 5 minutes
        if log_level == 'debug':
            log("--- Interface Stats ---")
            stdout, _ = run_cmd(f"awg show {interface}", check=False)
            if stdout:
                log(stdout)

if __name__ == "__main__":
    main()
