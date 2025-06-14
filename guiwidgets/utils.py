from numba.cuda import CudaSupportError
from numba.cuda.cudadrv.driver import CudaAPIError
from numba.cuda.cudadrv.error import CudaDriverError
import pywintypes
import wmi
from enum import Enum, auto


def _list_cpus() -> list[str]:
    """Return a list of CPU names on Windows via WMI."""
    cpus = []
    try:
        c = wmi.WMI()
        for cpu in c.Win32_Processor():
            cpus.append(cpu.Name.strip())
    except pywintypes.com_error as e:
        print("⚠️ WMI COM error:", e)
    except wmi.x_wmi as e:
        print("⚠️ WMI query error:", e)
    return cpus


def _list_gpus() -> list[str]:
    """Return a list of CUDA-capable GPU names via Numba."""
    gpu_list = []
    try:
        from numba import cuda
        if cuda.is_available():
            for dev in cuda.gpus:
                # .name is a bytestring, decode to UTF-8
                gpu_list.append(dev.name.decode('utf-8'))
    except (CudaSupportError, CudaDriverError, CudaAPIError) as e:
        print("⚠️ CUDA driver error:", e)
    except UnicodeDecodeError as e:
        print("⚠️ GPU name decoding error:", e)
    return gpu_list


def list_devices() -> list[dict[str, str | int]]:
    devices = []
    # CPUs
    cpus = _list_cpus()
    for idx, name in enumerate(cpus, start=1):
        devices.append({
            'type': 'CPU',
            'index': idx,
            'name': name
        })

    # GPUs
    gpus = _list_gpus()
    for idx, name in enumerate(gpus, start=1):
        devices.append({
            'type': 'GPU',
            'index': idx,
            'name': name
        })

    # Print summary
    if not devices:
        print("No devices found.")
    else:
        print("[Device Handler] Detected devices:")
        for dev in devices:
            print(f"  [{dev['type']} {dev['index']}] {dev['name']}")
    return devices


class SavedTreeTypes(Enum):
    POINTER = auto()
    GROUP = auto()
    ADDRESS = auto()
