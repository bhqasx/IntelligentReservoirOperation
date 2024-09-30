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

# 读取XLD_keypoints.json和SMX_keypoints.json
try:
    xld_file = find_file("XLD_keypoints.json")
    smx_file = find_file("SMX_keypoints.json")

    with open(xld_file, 'r') as f:
        tempData = json.load(f)
        XLD_KeyP = {
            't': tempData.get('t', []),
            'q': tempData.get('q', [])
        }
        XLD_HyperPara = {
            'WlFldContr': tempData.get('WlFldContr', 0),
            'WlReg': tempData.get('WlReg', 0),
            'volWatSupply': tempData.get('volWatSupply', 0)
        }        
    
    with open(smx_file, 'r') as f:
        tempData = json.load(f)
        SMX_KeyP = {
            't': tempData.get('t', []),
            'q': tempData.get('q', [])
        }
        SMX_HyperPara = {
            'WlFldContr': tempData.get('WlFldContr', 0),
        }

    print("Successfully loaded XLD_keypoints.json and SMX_keypoints.json")
except FileNotFoundError as e:
    print(f"Error: {e}")
except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {e}")

# 读取Xiaolangdi.json和Sanmenxia.json
try:
    xld_file = find_file("Xiaolangdi.json")
    smx_file = find_file("Sanmenxia.json")

    with open(xld_file, 'r') as f:
        tempData = json.load(f)
        XLD_CapCurve = {
            'WL': tempData.get('CapCurve', {}).get('WL', []),
            'Vol': tempData.get('CapCurve', {}).get('Vol', [])
        }
except FileNotFoundError as e:
    print(f"Error: {e}")
except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {e}")

iniWL_XLD = 250.8
#在终端提示输入小浪底初始水位，并显示当前默认输入值是iniWL_XLD，如果用户输入为空，则使用默认值
iniWL_XLD = input(f"请输入小浪底初始水位: (默认值: {iniWL_XLD})")
if iniWL_XLD == '':
    iniWL_XLD = 250.8
else:
    iniWL_XLD = float(iniWL_XLD)

iniWL_SMX = 318
#在终端提示输入三门峡初始水位，并显示当前默认输入值是iniWL_SMX，如果用户输入为空，则使用默认值
iniWL_SMX = input(f"请输入三门峡初始水位: (默认值: {iniWL_SMX})")
if iniWL_SMX == '':
    iniWL_SMX = 318
else:
    iniWL_SMX = float(iniWL_SMX)

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
    XLD_Plan[i]['t'][2] = new_value + 60  



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