import numpy as np
from memory_manager_engine.address_manager import AddressManager


# 1) A dummy MemoryScanner-like stub
class DummyScanner:
    def read_bytes(self, address, size):
        # always “succeed” so that freeze/unfreeze/add_saved_address tests can pass
        return b'\x00' * size


def manager():
    # use a very small page_size so we can force multiple pages
    return AddressManager(scanner=DummyScanner(), page_size=2)


def generate_random_entries(
    num_entries: int,
    address_low: int = 0x0,
    address_high: int = 0xFFFFFFFF,
    value_low: int = 0,
    value_high: int = 0xFFFFFFFF,
    seed: int = None
) -> np.ndarray:
    """
    Generate a NumPy array of shape (num_entries, 2), dtype=uint64,
    where column 0 is a random address in [address_low, address_high]
    and column 1 is a random value in [value_low, value_high].

    :param num_entries: how many (address, value) rows to create
    :param address_low: minimum address (inclusive)
    :param address_high: maximum address (inclusive)
    :param value_low: minimum value (inclusive)
    :param value_high: maximum value (inclusive)
    :param seed: optional RNG seed for reproducibility
    """
    rng = np.random.default_rng(seed)
    addresses = rng.integers(address_low, address_high + 1, size=num_entries, dtype=np.uint64)
    values = rng.integers(value_low,   value_high + 1, size=num_entries, dtype=np.uint64)
    return np.vstack([addresses, values]).T


def find_match_batches(arr: np.ndarray, pattern: str) -> list[tuple[int, int]]:
    """
    Finds all indices where hex(arr[i,0]) contains `pattern`, then groups these
    match indices into batches of 100 matches each. Returns the (first_index, last_index)
    for each batch.

    Parameters:
    - arr: np.ndarray of shape (n, 2)
    - pattern: substring to search for in hex(arr[i, 0])

    Returns:
    - List of tuples (first_match_idx, last_match_idx) for each 100-match batch.
    """
    # Get all matching indices
    matches = [i for i, val in enumerate(arr[:, 0]) if pattern in hex(int(val))]
    print(len(matches))
    # Group into batches of 100 matches
    batches = []
    for start in range(0, len(matches), 100):
        batch = matches[start:start + 100]
        if batch:
            batches.append((batch[0], batch[-1]))
    return batches

def test_filter_addresses_paging(manager):
    # 2) Build dummy data: 5 rows of (address, value)
    #    Addresses: 0x1, 0x2, 0x10, 0x11, 0x21
    dummy = generate_random_entries(10000, seed=14)

    # 3) Inject it and run the filter
    manager.extend(dummy)
    # filter on the substring “0x1” in the hex-form of the address
    filter_str = "13"
    manager.filter_addresses(filter_str)

    # 4) Expect exactly four matching rows: rows 0, 2, 3, and 4
    #    But since page_size=2, we should get two pages:
    #      page 1 covers matches at indexes [0..2] → (0x1, 0x10)
    #      page 2 covers matches at indexes [3..4] → (0x11, 0x21)
    matches = find_match_batches(dummy, filter_str)
    assert manager.filter_indices == matches
    result = ['0x' + hex(address)[2:].upper() for address, val in dummy[matches[-1][0]:matches[-1][1] + 1] if filter_str in hex(address)]
    print(result)
    print(len(result))


if __name__ == '__main__':
    test_filter_addresses_paging(AddressManager(scanner=DummyScanner()))
