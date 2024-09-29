import subprocess
import os
import json
import random
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed

# 读取文件XLD_keypoints.json和SMX_keypoints.json，如果这两个文件不在当前目录下，则从上一级目录中寻找
# 找到后，将数据分别存入XLD_KeyP和SMX_KeyP
def find_file(filename):
    # Check current directory
    if os.path.isfile(filename):
        return filename
    # Check parent directory
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parent_file = os.path.join(parent_dir, filename)
    if os.path.isfile(parent_file):
        return parent_file
    raise FileNotFoundError(f"Could not find {filename} in current or parent directory")

try:
    xld_file = find_file("XLD_keypoints.json")
    smx_file = find_file("SMX_keypoints.json")

    with open(xld_file, 'r') as f:
        tempData = json.load(f)
        XLD_KeyP = {
            't': tempData.get('t', []),
            'q': tempData.get('q', [])
        }        
    
    with open(smx_file, 'r') as f:
        tempData = json.load(f)
        SMX_KeyP = {
            't': tempData.get('t', []),
            'q': tempData.get('q', [])
        }

    print("Successfully loaded XLD_keypoints.json and SMX_keypoints.json")
except FileNotFoundError as e:
    print(f"Error: {e}")
except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {e}")

# 设置方案数量
planNum = 8
# 用一个数据结构存储XLD的planNum个方案，其中每个方案都有t和q两个数组，且数组长度与XLD_KeyP中的t数组长度相同
XLD_Plan = []
for i in range(planNum):
    XLD_Plan.append({
        't': copy.deepcopy(XLD_KeyP['t']),
        'q': copy.deepcopy(XLD_KeyP['q'])
    })

# 用一个数据结构存储SMX的planNum个方案，其中每个方案都有t和q两个数组，且数组长度与SMX_KeyP中的t数组长度相同
SMX_Plan = []
for i in range(planNum):
    SMX_Plan.append({
        't': copy.deepcopy(SMX_KeyP['t']),
        'q': copy.deepcopy(SMX_KeyP['q'])
    })


# 设置最迟开始时间
t2_lim = 200

for i in range(planNum):
    new_value = random.uniform(XLD_KeyP['t'][0], t2_lim)
    print(f"Plan {i}: Random value = {new_value}, Lower bound = {XLD_KeyP['t'][0]}, Upper bound = {t2_lim}")
    XLD_Plan[i]['t'][1] = new_value


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