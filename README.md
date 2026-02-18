# Switch with MAC Learning and VLAN Support

Implementation of a **software Layer 2 switch** in Python, supporting **MAC address learning**, **VLAN isolation**, and a custom **extended VLAN ID** mechanism for unicast filtering. Developed as part of a Computer Networks course assignment.

## Overview

The switch is simulated as a Python process that receives Ethernet frames on any interface and forwards them based on a dynamically learned MAC table. VLAN support is implemented using a custom `0x8200` EtherType tag (802.1Q-like), and trunk/access port configuration is read from a per-switch config file.

## Features

- **MAC learning**: source MAC → ingress port mapping stored in a Python dictionary
- **Unicast forwarding**: known destinations are forwarded directly; unknown destinations are flooded
- **VLAN isolation**: access ports are filtered by VLAN ID; trunk ports carry tagged frames
- **Extended VLAN ID**: for unicast frames, an additional 4-bit value (sum of all MAC nibbles, mod 16) is encoded in the PCP/DEI field of the VLAN tag to further restrict forwarding
- **Flood with VLAN awareness**: broadcast/multicast frames are flooded only to ports in the same VLAN
- **Hardcoded loop prevention**: interface `rr-0-2` on Switch2 is blocked to eliminate the physical loop in the topology (STP not implemented)

## Project Structure

```
.
├── switch.py              # Main switch implementation
├── configs/
│   ├── switch0.cfg        # Per-switch port/VLAN configuration
│   ├── switch1.cfg
│   └── switch2.cfg
├── ex1.png                # Screenshot: ping between hosts + Wireshark ICMP traffic
└── ex2.png                # Screenshot: VLAN isolation demo (host0→host2 OK, host0→host1 FAIL)
```

## Configuration File Format

Each switch reads `configs/switchX.cfg`. Example:

```
<switch_priority>
<interface_name> T          # Trunk port
<interface_name> <vlan_id>  # Access port with VLAN ID
```

## Running

```bash
sudo python3 switch.py <switch_id> <interface1> <interface2> ...
```

## Implementation Details

### Task 1 — MAC Learning & Forwarding

The MAC table (`MAC_Table`) is a Python dictionary mapping source MAC addresses (`bytes`) to ingress port numbers (`int`).

On each received frame:
- The source MAC is learned: `MAC_Table[src_mac] = ingress_port`
- For **unicast** frames with a known destination → forward to the stored port
- For **unicast** with unknown destination, or **broadcast/multicast** → flood to all ports except the ingress

Unicast detection uses `is_unicast()`, which checks the least significant bit of the first MAC byte.

### Task 2 — VLAN Support

Port state is tracked via two dictionaries:
- `port{}` — maps interface name → VLAN ID (access ports), or `-1` (trunk ports)
- `trunk{}` — maps interface name → `True` if trunk, `False` if access

Key functions:

| Function | Description |
|---|---|
| `create_vlan_tag(ext_id, vlan_id)` | Builds a custom 802.1Q-like tag (EtherType `0x8200`) |
| `get_exit_id_mac(mac)` | Computes the extended ID: sum of all nibbles of a MAC address, mod 16 |
| `same_vlan(out_port, vlan, ...)` | Checks VLAN match for broadcast/multicast forwarding |
| `same_vlan_extended(out_port, vlan, exit_id, dst_mac, ...)` | Checks VLAN + extended ID for unicast forwarding |
| `send_frame(out_port, ...)` | Adds or removes VLAN tag depending on whether the egress port is trunk or access |

Forwarding logic:
- **Trunk egress**: tag is preserved if already present; otherwise a new tag is added (with the computed extended ID)
- **Access egress**: tag is stripped before sending
- **Unicast known**: verified with `same_vlan_extended()` (VLAN ID + extended ID)
- **Broadcast/unknown**: verified with `same_vlan()` (VLAN ID only)

### Task 3 — STP

Not implemented. The physical loop in the topology is eliminated by hardcoding the blocking of interface `rr-0-2` on Switch2.

## Screenshots

**ex1.png** — Successful pings between hosts on the same VLAN, with Wireshark capturing ICMP traffic and all three switches running.

**ex2.png** — VLAN isolation in action:
- `ping host0 → host2` (both on VLAN 1): **SUCCESS** (0% packet loss)
- `ping host0 → host1` (VLAN 1 → VLAN 2): **FAIL** (100% packet loss, Destination Host Unreachable)

## Author

Darius Zaharescu
