#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]

    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    vlan_tci = -1
    # Check for VLAN tag (0x8200 in network byte order is b'\x82\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id, vlan_tci

def create_vlan_tag(ext_id, vlan_id):
    # Use EtherType = 8200h for our custom 802.1Q-like protocol.
    # PCP and DEI bits are used to extend the original VID.
    #
    # The ext_id should be the sum of all nibbles in the MAC address of the
    # host attached to the _access_ port. Ignore the overflow in the 4-bit
    # accumulator.
    #
    # NOTE: Include these 4 extensions bits only in the check for unicast
    #       frames. For multicasts, assume that you're dealing with 802.1Q.
    return struct.pack('!H', 0x8200) + \
           struct.pack('!H', ((ext_id & 0xF) << 12) | (vlan_id & 0x0FFF))

def function_on_different_thread():
    while True:
        time.sleep(1)

def is_unicast(mac_address):
    if (mac_address[0] & 1) == 0:
        return True
    else:
        return False

def get_exit_id_mac(mac_address):
    exit_id_copy = 0
    for byte in mac_address:
        exit_id_copy = exit_id_copy + (byte >> 4)
        exit_id_copy = exit_id_copy + (byte & 0x0F)
    exit_id = exit_id_copy & 0xF
    return exit_id

def get_vlan(interface, vlan_id, vlan_tci, src_mac, trunk, port):
    interface_name = get_interface_name(interface)
    if trunk[interface_name]:
        return vlan_id
    else:
        return port[interface_name]

def get_exit_id(interface, vlan_tci, src_mac, trunk):
    interface_name = get_interface_name(interface)
    bits = vlan_tci >> 12
    if trunk[interface_name]:
        return bits & 0xF
    else:
        return get_exit_id_mac(src_mac)

def same_vlan(out_port, vlan, trunk, port):
    out_interface_name = get_interface_name(out_port)
    if trunk[out_interface_name]:
        return 1
    else:
        port_vlan = port[out_interface_name]
        if vlan == port_vlan:
            return 1
        else:
            return 0

def same_vlan_extended(out_port, vlan, exit_id, dst_mac, trunk, port):
    out_interface_name = get_interface_name(out_port)
    if trunk[out_interface_name]:
        return 1
    else:
        port_vlan = port[out_interface_name]
        if vlan != port_vlan:
            return 0
        expected_exit_id = get_exit_id_mac(dst_mac)
        if exit_id == expected_exit_id:
            return 1
        else:
            return 0

def is_trunk(out_port, trunk):
    out_interface_name = get_interface_name(out_port)
    if trunk[out_interface_name]:
        return 1
    else:
        return 0

def send_frame(out_port, data, length, vlan_id, vlan, src, trunk):
    mac = data[0:12]
    if is_trunk(out_port, trunk):
        if vlan_id == -1:
            rest = data[12:]
            tag_exit = get_exit_id_mac(src)
            vlan_tag = create_vlan_tag(tag_exit, vlan)
            frame = mac + vlan_tag + rest
            send_to_link(out_port, len(frame), frame)
        else:
            send_to_link(out_port, length, data)
    else:
        if vlan_id != -1:
            rest = data[16:]
            frame = mac + rest
            send_to_link(out_port, len(frame), frame)
        else:
            send_to_link(out_port, length, data)

def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    configs = f"configs/switch{switch_id}.cfg"
    f = open(configs, "r")
    lines = f.readlines()
    f.close()

    port = {}
    trunk = {}

    for i in range (1, len(lines)):
        sep = lines[i].split()
        
        if sep[1] == 'T':
            trunk[sep[0]] = True
            port[sep[0]] = -1
        else :
            trunk[sep[0]] = False
            port[sep[0]] = int(sep[1])

    MAC_Table = {}

    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))


    # Example of running a function on a separate thread.
    t = threading.Thread(target=function_on_different_thread)
    t.start()

    # Printing interface names
    for i in interfaces:
        print(get_interface_name(i))

    # hardcode
    block = None
    stop = 1
    if switch_id == "2":
        for i in interfaces:
            if stop == 1:
                if get_interface_name(i) == "rr-0-2":
                    block = i
                    stop = 0

    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        # hardcode
        if interface == block:
            continue

        dest_mac, src_mac, ethertype, vlan_id, vlan_tci = parse_ethernet_header(data)

        dst = dest_mac
        src = src_mac

        vlan = get_vlan(interface, vlan_id, vlan_tci, src, trunk, port)
        exit_id = get_exit_id(interface, vlan_tci, src, trunk)

        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(5, 10) + data[12:]

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')

        print("Received frame of size {} on interface {}".format(length, interface), flush=True)

        # TODO: Implement forwarding with learning

        P = interface
        
        MAC_Table[src] = P
        dest_ports = [0] * num_interfaces
        count = 0
        
        if is_unicast(dst):
            if dst in MAC_Table:
                dest_ports[0] = MAC_Table[dst]
                count = 1
            else:
                for o in interfaces:
                    if o != P:
                        dest_ports[count] = o
                        count = count + 1
        else:
            for o in interfaces:
                if o != P:
                    dest_ports[count] = o
                    count = count + 1


        # TODO: Implement VLAN support
        for i in range(count):
            out_port = dest_ports[i]
            
            # hardcode
            if out_port == block:
                continue
            
            if is_unicast(dst) and dst in MAC_Table:
                ok = same_vlan_extended(out_port, vlan, exit_id, dst, trunk, port)
            else:
                ok = same_vlan(out_port, vlan, trunk, port)
            
            if ok == 1:
                send_frame(out_port, data, length, vlan_id, vlan, src, trunk)
                time.sleep(0.5)
        # TODO: Implement STP support

        # data is of type bytes.
        # send_to_link(i, length, data)

if __name__ == "__main__":
    main()
