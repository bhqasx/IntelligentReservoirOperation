import subprocess
import os

# 定义可执行文件所在的目录和文件名
exe_directory = r"D:\一维计算结果\小浪底与下游联合\XLDDS05\1D_RiverNet_OCTC"  # 替换为你exe文件所在的目录
executable = "1D_RiverNet_OCTC.exe"
argument = "case1"     #这个文件夹放在exe_directory下，里面放入Input和Output文件夹

# 使用绝对路径运行可执行文件
try:
    result = subprocess.run([os.path.join(exe_directory, executable), argument], 
                            cwd=exe_directory,  # 设置工作目录
                            check=True)
    print("Process completed successfully.")
except subprocess.CalledProcessError as e:
    print(f"An error occurred: {e}")