import subprocess
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# 定义可执行文件所在的目录和文件名
exe_directory = r"E:\一维计算结果\小浪底与下游联合\XLDDS06\1D_RiverNet_OCTC"  # 替换为你exe文件所在的目录
executable = "1D_RiverNet_OCTC.exe"
arguments = ["case1", "case2"]     #这个或这些文件夹放在exe_directory下，里面放入Input和Output文件夹

def run_simulation(argument):
    try:
        result = subprocess.run([os.path.join(exe_directory, executable), argument], 
                                cwd=exe_directory,  # 设置工作目录
                                check=True)
        return f"Process for {argument} completed successfully."
    except subprocess.CalledProcessError as e:
        return f"An error occurred for {argument}: {e}"

# 使用线程池并行运行多个子进程
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(run_simulation, arg) for arg in arguments]
    for future in as_completed(futures):
        print(future.result())