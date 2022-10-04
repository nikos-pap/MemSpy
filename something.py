from ctypes import *
import ctypes
import psutil
import time
import win32api
import win32process

def get_client_pid(process_name):
    pid = None
    for proc in psutil.process_iter():
        if proc.name() == process_name:
            pid = int(proc.pid)
            print("Found, PID = ", pid)
            break
    return pid

pid = get_client_pid("BleachBraveSouls.exe")

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

process = windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ,False,pid)
process2 = windll.kernel32.OpenProcess(0x0020 | 0x0008, False, pid)

readprocess = windll.kernel32.ReadProcessMemory
writeprocess = windll.kernel32.WriteProcessMemory

rdbuf = ctypes.c_uint()
bytread = ctypes.c_size_t()

addread = 0x000001B79C9E28A8

PROCESS_ALL_ACCESS = 0x1F0FFF
processHandle = win32api.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
module_addresses = [hex(module) for module in win32process.EnumProcessModules(processHandle)]
base = module_addresses[0]
#print((module_addresses))
readprocess(process, ctypes.c_void_p(addread), ctypes.byref(rdbuf), ctypes.sizeof(rdbuf),ctypes.byref(bytread))
print(rdbuf.value)
data = ctypes.c_uint(1000)
print(data.value)
print(writeprocess(process2, ctypes.c_void_p(addread), ctypes.byref(data), ctypes.sizeof(data), None))
readprocess(process, ctypes.c_void_p(addread), ctypes.byref(rdbuf), ctypes.sizeof(rdbuf),ctypes.byref(bytread))
print(rdbuf.value)
# print(hex(base))
# addr = base
print(win32process.GetProcessMemoryInfo(processHandle))#['WorkingSetSize'])
# scan_value = 1106
# while addr < 0x81adb1acc308 + 1:
#     try:
#         if readprocess(process, ctypes.c_void_p(addr), ctypes.byref(rdbuf), ctypes.sizeof(rdbuf),ctypes.byref(bytread)):
#             #print(addr, end=' ')
#             if rdbuf.value == scan_value:
#                 print(hex(addr),rdbuf.value)
#     except Exception as e:
#         print("ERROR", e)
#     addr += 4
# for addr in range(base, base + 100000):
#     try:
#         if readprocess(process, ctypes.c_void_p(addr), ctypes.byref(rdbuf), ctypes.sizeof(rdbuf),ctypes.byref(bytread)):
#             print(hex(addr),rdbuf.value)
#     except Exception as e:
#         print("ERROR", e)