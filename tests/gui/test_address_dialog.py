# tests/test_pointer_scanner_api.py
import pytest
import numpy as np

try:
    import pointer_scanner as ps_mod
except Exception as e:
    pytest.skip(f"Cannot import pointer_scanner normally: {e}", allow_module_level=True)


class FakeRegion:
    def __init__(self, rid, name, base, size):
        self.id = rid
        self.name = name
        self.base_address = base
        self.size = size
        self.data = b""
        self.pointers = []

    # used by preprocess_pointers in your code
    def pointers_filter(self, ranges):  # no-op
        pass

    def check_loops(self):  # no-op
        pass

    # called by get_pointer_map()
    def data2values(self, ranges, dtype, use_gpu, step_enable):
        # pretend we parsed two pointer candidates
        self.pointers = np.array(
            [self.base_address + 0x100, self.base_address + 0x200],
            dtype=np.uint64,
        )


class FakeMemoryScanner:
    def __init__(self, base=0x10000000):
        self._base = base
        self._regions = [
            FakeRegion(0, "helper.exe", base, 0x4000),
            FakeRegion(1, "ntdll.dll", base + 0x8000, 0x4000),
        ]

    def get_regions(self, element_size=8):
        return list(self._regions)

    def read_memory_by_region(self, region):
        region.data = b"\x00" * 64

    def get_modules(self):
        return {
            "helper.exe": self._base,
            "ntdll.dll": self._base + 0x8000,
        }


def test_pointer_scanner_flow(monkeypatch):
    # Monkeypatch the helper functions used inside pointer_scan() only.
    # We touch the module that pointer_scanner itself imported.
    pst = ps_mod.pointer_scanner_tools

    monkeypatch.setattr(pst, "preprocess_unique_transitions", lambda addresses: addresses)
    monkeypatch.setattr(pst, "build_region_graph", lambda unique_regions: {"graph": True})
    monkeypatch.setattr(pst, "dfs_regions", lambda graph, start_region, max_depth: {0, 1})
    monkeypatch.setattr(pst, "filter_addresses_by_regions", lambda addresses, regions: addresses)

    # Produce a tiny deterministic traversal:
    def dfs_indexed(addresses, target_address, max_depth, offset_range, negatives, randomness):
        # one fake chain of (addr, offset) pairs
        yield (0x10000000, [(target_address, 0x20), (target_address + 8, 0x10)])

    monkeypatch.setattr(pst, "dfs_indexed", dfs_indexed)

    scanner = FakeMemoryScanner()
    ps = ps_mod.PointerScanner(scanner=scanner)

    # Build pointer map per new API
    ps.get_pointer_map(use_gpu=False)

    # Sanity checks: regions parsed and have pointers
    assert hasattr(ps, "regions") and len(ps.regions) >= 1
    assert all(getattr(r, "pointers", None) is not None and len(r.pointers) > 0 for r in ps.regions)

    # Run pointer scan per new API (note: now needs target_address)
    target = 0x10000000 + 0x1234
    seen = 0
    for out in ps.pointer_scan(
        target_address=target,
        depth=2,
        max_offset=1024,
        negative_offsets_enabled=True,
        randomness=0.0,
    ):
        if out is None:
            break
        chain_list, score = out
        assert isinstance(chain_list, list) and chain_list, "Expected non-empty PointerChain list"
        pc = chain_list[0]
        # make_pointers_list sets .target on each PointerChain
        assert getattr(pc, "target") == target
        seen += 1

    assert seen >= 1, "Expected at least one pointer chain yielded"
