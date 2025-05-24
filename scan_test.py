from scanner_engine.process_reader import MemoryScanner

if __name__ == "__main__":
    scanner = MemoryScanner(pid=18648, enable_debug=False)
    addresses = scanner.scan_value((12321).to_bytes(4, byteorder='little'))  # Example value
    ads = [address[0] for address in addresses]
    print(len(ads))
    print(scanner.read_bytes(0x15130a2b1cc, 4))
    scanner.write_bytes(0x15130a2b1cc, (12321).to_bytes(4, byteorder='little'))
    print(scanner.read_bytes(0x15130a2b1cc, 4))
    scanner.close()