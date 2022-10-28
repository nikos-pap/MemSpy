import subprocess
import sys
from pymem.process import list_processes, process_from_id
import psutil
# def install(package):
#     subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# install('wmi')
# import wmi
 
# # Initializing the wmi constructor
# f = wmi.WMI()
 
# # Printing the header for the later columns
# print("pid   Process name")
 
# # Iterating through all the running processes
# for process in f.Win32_Process():
     
#     # Displaying the P_ID and P_Name of the process
#     print(f"{process.ProcessId:<10} {process.Name}")
l = [process_from_id(pid).szExeFile.decode('ascii') for pid in psutil.pids()]
print(l)
print(len(list(filter(lambda a: a.endswith('.exe'), l))))