import sys

def parse_value(value_str, size):
    value = int(value_str, 16)
    return value.to_bytes(size, byteorder="big")  # change if needed

def search_rom(file_path, pattern_bytes):
    matches = []

    with open(file_path, "rb") as f:
        data = f.read()

    plen = len(pattern_bytes)

    for i in range(len(data) - plen + 1):
        if data[i:i+plen] == pattern_bytes:
            matches.append(i)

    return matches

def main():
    if len(sys.argv) < 4:
        print("Usage:")
        print("  python search_rom.py <rom> byte <hex bytes> <NONE or address>")
        print("  python search_rom.py <rom> half <0x1234> <NONE or address>")
        print("  python search_rom.py <rom> word <0x12345678> <NONE or address>")
        return

    rom_path = sys.argv[1]
    mode = sys.argv[2]
    value = sys.argv[3]
    replace_with_address_pointer = sys.argv[4]

    if mode == "byte":
        pattern_bytes = bytes.fromhex(value.replace("0x", ""))
    elif mode == "half":
        pattern_bytes = parse_value(value, 2)
    elif mode == "word":
        pattern_bytes = parse_value(value, 4)
    else:
        print("Invalid mode.")
        return

    matches = search_rom(rom_path, pattern_bytes)

    for addr in matches:
        if replace_with_address_pointer == "NONE":
            print(f".orga 0x{addr:08X} :: /*please insert your changes here*/")
        else:
            print(f".orga 0x{addr:08X} :: .word {replace_with_address_pointer}")



if __name__ == "__main__":
    main()
