"""
================================================================================
  Interactive Music Architecture — OSC Bridge & Diagnostic Server
  Location: d:\CODING\InteractiveMusicArchitecture\osc_server\osc_bridge.py
================================================================================
  This script acts as a standalone OSC receiver/logger and sequencer bridge.
  It listens for OSC messages from either:
    1. Unreal Engine 5.8 (MusicalArchitectureTraceComponent via Epic's OSC Plugin)
    2. Web Prototype / any external sequencer / test client

  It forwards / maps incoming architectural raycast hits to:
    - Ableton Live (via Max for Live or standard OSC port 9000)
    - REAPER (OSC Control Surface on port 8000)
    - PureData / Max MSP

  Default listening port: 8000
  Forwarding destination: 127.0.0.1:9000
================================================================================
"""

import socket
import struct
import time
import sys

def parse_osc_string(data, offset):
    """Parse null-terminated 4-byte padded OSC string."""
    end = data.find(b'\x00', offset)
    if end == -1:
        return "", len(data)
    str_val = data[offset:end].decode('utf-8', errors='ignore')
    # Advance to next 4-byte boundary
    next_offset = (end + 4) & ~3
    return str_val, next_offset

def parse_osc_packet(data):
    """Basic parser for OSC packets."""
    try:
        address, offset = parse_osc_string(data, 0)
        if offset >= len(data) or not data[offset:offset+1].startswith(b','):
            return address, []
        
        type_tags, offset = parse_osc_string(data, offset)
        args = []
        for tag in type_tags[1:]: # skip leading comma
            if tag == 'i':
                val = struct.unpack('>i', data[offset:offset+4])[0]
                offset += 4
                args.append(val)
            elif tag == 'f':
                val = struct.unpack('>f', data[offset:offset+4])[0]
                offset += 4
                args.append(round(val, 1))
            elif tag == 's':
                s_val, offset = parse_osc_string(data, offset)
                args.append(s_val)
        return address, args
    except Exception as e:
        return "ERROR", [str(e)]

def run_server(listen_port=8000, forward_port=9000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", listen_port))
    sock.setblocking(True)
    
    forward_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("=" * 75)
    print("  INTERACTIVE MUSIC ARCHITECTURE — OSC BRIDGE READY")
    print(f"  Listening on UDP: 127.0.0.1:{listen_port}")
    print(f"  Forwarding to Ableton Live (DAW) on UDP: 127.0.0.1:{forward_port}")
    print("=" * 75)
    print("  Waiting for architectural raycast hits from UE5.8 (TP_FirstPerson)...")
    print("  Press Ctrl+C to terminate.\n")

    SCALE_DESCRIPTIONS = {
        "/arch/macro": "MAKRO ÖLÇEK (Bas Sekansları & Master Reverb)",
        "/arch/meso":  "MEZO ÖLÇEK  (Perküsyon ve Davul Sekansları)",
        "/arch/micro": "MİKRO ÖLÇEK (Harmoni, Tını, Synth Pad'ler)",
    }

    try:
        while True:
            data, addr = sock.recvfrom(4096)
            address, args = parse_osc_packet(data)
            
            timestamp = time.strftime("%H:%M:%S")
            if address in SCALE_DESCRIPTIONS and len(args) >= 4:
                obj_name, primary_cmd, secondary_cmd, dist = args[0], args[1], args[2], args[3]
                print(f"[{timestamp}] {SCALE_DESCRIPTIONS[address]}")
                print(f"           ├─ Çarpan Obje : {obj_name} (Mesafe: {dist} cm)")
                print(f"           └─ Müzikal Komut: '{primary_cmd}' / '{secondary_cmd}' -> Ableton Live (UDP:{forward_port})\n")
            else:
                print(f"[{timestamp}] OSC Received: {address:<25} Args: {args}")

            # Forward to DAW (Ableton Live)
            try:
                forward_sock.sendto(data, ("127.0.0.1", forward_port))
            except Exception:
                pass

    except KeyboardInterrupt:
        print("\n[OSC Bridge] Shutting down cleanly.")
    finally:
        sock.close()
        forward_sock.close()

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run_server(port)
