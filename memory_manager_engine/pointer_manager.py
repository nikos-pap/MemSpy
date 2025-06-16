import pickle
import numpy as np
from scanner_engine.process_reader import MemoryScanner


class PointerManager:
    def __init__(self, chains, memory_scanner: MemoryScanner):
        self.chains = chains
        self.memory_scanner = memory_scanner

    def __str__(self, n: int = 100):
        output = ""
        for i in range(min(len(self.chains),n)):
            pointer = self.chains[i]
            output += f'{pointer.module_name} + {hex(pointer.offsets[0])}, {[hex(p) for p in pointer.offsets[1:]]}, {pointer.value}\n'
        return output

    def update(self, size: int = 4):
        for pointer in self.chains:
            addr = pointer.start
            for offset in pointer.offsets[:-1]:
                data = self.memory_scanner.read_bytes(addr + offset, 8)
                if data is None:
                    pointer.value = None
                    break
                addr = int(np.frombuffer(data, dtype='<u8')[0])
            value = self.memory_scanner.read_bytes(addr + pointer.offsets[-1], size)
            if value is None:
                pointer.value = None
            pointer.value = int(np.frombuffer(value, dtype=f'<u{size}')[0])

    def filter(self, value: bytes):
        self.chains = [pointer for pointer in self.chains if pointer.value == value]

    def save_chains(self, name: str):
        with open(name, 'wb') as f:
            pickle.dump(self.chains, f)

    def load_chains(self, name: str):
        with open(name, 'rb') as f:
            self.chains = pickle.load(f)
        modules = self.memory_scanner.get_modules()
        for pointer in self.chains:
            pointer.start = modules[pointer.module_name]