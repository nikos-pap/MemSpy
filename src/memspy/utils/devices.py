from numba.cuda import CudaSupportError
from numba.cuda.cudadrv.driver import CudaAPIError
from numba.cuda.cudadrv.error import CudaDriverError
import pywintypes
import wmi
from logging import getLogger, Logger


logger: Logger = getLogger('Device Manager')


def _list_cpus() -> list[str]:
    """Return a list of CPU names on Windows via WMI."""
    cpus = []
    try:
        c = wmi.WMI()
        for cpu in c.Win32_Processor():
            cpus.append(cpu.Name.strip())
    except pywintypes.com_error as e:
        logger.error("⚠️ WMI COM error:", e)
    except wmi.x_wmi as e:
        logger.error("⚠️ WMI query error:", e)
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
        logger.error("⚠️ CUDA driver error:", e)
    except UnicodeDecodeError as e:
        logger.error("⚠️ GPU name decoding error:", e)
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
        logger.debug("No devices found.")
    else:
        text = 'Detected devices:'

        for dev in devices:
            text += f"\n  [{dev['type']} {dev['index']}] {dev['name']}"

        logger.info(text)
    return devices
