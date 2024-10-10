import subprocess
import os
import json
import random
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed

global SMX_t_in, SMX_q_in, SMX_HyperPara, SMX_CapCurve, iniVol_SMX

def interpolate(x, x_array, y_array):
    if x <= x_array[0]:
        return y_array[0]
    if x >= x_array[-1]:
        return y_array[-1]
    for i in range(len(x_array) - 1):
        if x_array[i] <= x < x_array[i+1]:
            x0, x1 = x_array[i], x_array[i+1]
            y0, y1 = y_array[i], y_array[i+1]
            return y0 + (x - x0) * (y1 - y0) / (x1 - x0)
    return None  # This should never happen if x is within the range of x_array

#定义一个名为CalculateT的函数，计算达到指定净出流水量所需的时间，从main.js中改写来
def CalculateT(volTarg, tt, qq, iLastKeyP, iReservoir, dischargeMod, iPlan):
    t2 = 0
    dt = 4
    if iReservoir == 1:  # XLD reservoir
        t1 = XLD_Plan[iPlan]['t'][iLastKeyP - 1]
        i = next(i for i, t in enumerate(tt) if t >= t1)
        
        vol = 0
        for j in range(i - 1):
            vol -= (tt[j + 1] - tt[j]) * (qq[j + 1] + qq[j]) / 2
        
        q1 = interpolate(t1, tt, qq)
        vol -= (t1 - tt[i - 1]) * (q1 + qq[i - 1]) / 2
        
        for j in range(iLastKeyP - 1):
            vol += (XLD_Plan[iPlan]['t'][j + 1] - XLD_Plan[iPlan]['t'][j]) * (XLD_Plan[iPlan]['q'][j + 1] + XLD_Plan[iPlan]['q'][j]) / 2
        
        t2 = t1
        q2 = q1
        stop_flag = 0
        while stop_flag == 0:
            t2 += dt
            if t2 > tt[-1]:
                print(f"错误：t2 ({t2}) 超过了 tt 的最后一个时刻 ({tt[-1]})。")
                print(f"当前 iLastKeyP: {iLastKeyP}, iPlan: {iPlan}")
                return t2, False

            q2 = interpolate(t2, tt, qq)
            vol -= dt * (q2 + q1) / 2
            if dischargeMod == 1:         #维持上一个调控流量
                vol += dt * XLD_Plan[iPlan]['q'][iLastKeyP - 1]
                t1 = t2
                q1 = q2
                if vol * 3600 / 10**8 > volTarg:
                    stop_flag = 1
                #print('vol:', vol * 3600 / 10**8)
            else:                       #线性变化至当前调控流量
                dVol = (t2 - XLD_Plan[iPlan]['t'][iLastKeyP - 1]) * (XLD_Plan[iPlan]['q'][iLastKeyP - 1] + XLD_Plan[iPlan]['q'][iLastKeyP]) / 2
                if (vol + dVol) * 3600 / 10**8 > volTarg:
                    stop_flag = 1
                #print('vol:', (vol + dVol) * 3600 / 10**8)
    
    elif iReservoir == 2:  # SMX reservoir
        t1 = SMX_Plan[iPlan]['t'][iLastKeyP - 1]
        i = next(i for i, t in enumerate(tt) if t >= t1)
        
        tStart = SMX_Plan[iPlan]['t'][1]
        iStart = next(i for i, t in enumerate(tt) if t >= tStart)
        
        vol = 0
        qStart = interpolate(tStart, tt, qq)
        vol -= (tt[iStart] - tStart) * (qStart + qq[iStart]) / 2
        
        for j in range(iStart, i - 1):
            vol -= (tt[j + 1] - tt[j]) * (qq[j + 1] + qq[j]) / 2
        
        q1 = interpolate(t1, tt, qq)
        vol -= (t1 - tt[i - 1]) * (q1 + qq[i - 1]) / 2
        vol += (SMX_Plan[iPlan]['t'][2] - SMX_Plan[iPlan]['t'][1]) * (SMX_Plan[iPlan]['q'][2] + qStart) / 2
        
        for j in range(2, iLastKeyP - 1):
            vol += (SMX_Plan[iPlan]['t'][j + 1] - SMX_Plan[iPlan]['t'][j]) * (SMX_Plan[iPlan]['q'][j + 1] + SMX_Plan[iPlan]['q'][j]) / 2

        if iLastKeyP == 5:
            print('vol:', vol * 3600 / 10**8)
        
        t2 = t1
        q2 = q1
        stop_flag = 0
        while stop_flag == 0:
            t2 += dt
            if t2 > tt[-1]:
                print(f"错误：t2 ({t2}) 超过了 tt 的最后一个时刻 ({tt[-1]})。")
                print(f"当前 iLastKeyP: {iLastKeyP}, iPlan: {iPlan}")
                return t2, False

            q2 = interpolate(t2, tt, qq)
            vol -= dt * (q2 + q1) / 2
            vol += dt * SMX_Plan[iPlan]['q'][iLastKeyP - 1]
            t1 = t2
            q1 = q2
            if iLastKeyP == 5:
                if vol * 3600 / 10**8 < volTarg:
                    stop_flag = 1
            else:
                if vol * 3600 / 10**8 > volTarg:
                    stop_flag = 1
    
    return t2, True

def CalculateRefillT(volChange, tt, qq, ttNat, qqNat, tCtrl, qCtrl):  
    qqCopy = qq.copy()
    #ttNat与qqNat是天然来流过程
    t = 0

    vol_in = 0
    # ttNat是递增的，找出其中小于tt[1]的最后一个值的下标
    i = next(i for i, t in enumerate(ttNat) if t >= tt[1]) - 1
    
    # 在ttNat[i]和ttNat[i+1]之间对qqNat插值得到tt[1]时刻的流量
    q1 = interpolate(tt[1], ttNat, qqNat)
    
    # 找出ttNat中大于tt[0]的第一个值的下标
    j = next(j for j, t in enumerate(ttNat) if t >= tt[0])
    
    # 在ttNat[j-1]和ttNat[j]之间对qqNat插值得到tt[0]时刻的流量
    q0 = interpolate(tt[0], ttNat, qqNat)
    
    # 计算从tt[0]到tt[1]的入库水量，这两时刻间的流量使用qqNat中对应时刻的流量
    vol_in = (ttNat[j] - tt[0]) * (q0 + qqNat[j]) / 2
    
    # 将ttNat[j]到ttNat[i]的入库水量累加到vol_in
    for k in range(j, i):
        vol_in += (ttNat[k + 1] - ttNat[k]) * (qqNat[k + 1] + qqNat[k]) / 2
    
    vol_in += (tt[1] - ttNat[i]) * (q1 + qqNat[i]) / 2
    
    # 在ttNat和qqNat上插值计算tt[1]时刻对应的qq[1]
    qqCopy[1] = interpolate(tt[1], ttNat, qqNat)

    # 将tt[1]到tt[6]的入库水量累加到vol_in，注意qq[6]是null，tt[5]和tt[6]相等
    for k in range(1, 5):
        vol_in += (tt[k + 1] - tt[k]) * (qqCopy[k + 1] + qqCopy[k]) / 2

    # 如果tt[6]>tCtrl最后时刻，则弹窗提示，否则将tt[6]到tCtrl最后时刻的入库水量累加到vol_in
    if tt[6] > tCtrl[-1]:
        print('三门峡最后时刻大于小浪底最大调度时刻，请重新输入')
        return None
    else:
        # tt[6]到tCtrl最后时刻的入库水量都用qqNat中对应时刻的流量
        # 先找到ttNat中大于tt[6]的第一个值的下标
        k = 0
        while ttNat[k] < tt[6]:
            k += 1
        # 在ttNat[k-1]和ttNat[k]之间对qqNat插值得到tt[6]时刻的流量
        q6 = interpolate(tt[6], ttNat, qqNat)
        # 将tt[6]到ttNat[k]间的入库水量累加到vol_in
        vol_in += (ttNat[k] - tt[6]) * (q6 + qqNat[k]) / 2
        # 找到ttNat中小于tCtrl最后时刻的最后一个值的下标
        k2 = len(ttNat) - 1
        while ttNat[k2] > tCtrl[-1]:
            k2 -= 1
        # 将ttNat[k]到ttNat[k2]的入库水量累加到vol_in
        for k in range(k, k2):
            vol_in += (ttNat[k + 1] - ttNat[k]) * (qqNat[k + 1] + qqNat[k]) / 2
        # 在ttNat[k2]和ttNat[k2+1]之间对qqNat插值得到tCtrl最后时刻的流量
        qEnd = interpolate(tCtrl[-1], ttNat, qqNat)
        # 将ttNat[k2]到tCtrl最后时刻的入库水量累加到vol_in
        vol_in += (tCtrl[-1] - ttNat[k2]) * (qEnd + qqNat[k2]) / 2

    vol_out = 0
    iPre = 8  # 也许改为len(tCtrl)-4更通用？
    for j in range(1, iPre):
        vol_out += (tCtrl[j] - tCtrl[j - 1]) * (qCtrl[j] + qCtrl[j - 1]) / 2
    
    vol_out = volChange * 10**8 / 3600 + vol_in - vol_out
    tPre = tCtrl[iPre - 1]
    qPre = qCtrl[iPre - 1]
    qCurrent = qCtrl[iPre]
    tNext = tCtrl[iPre + 2]
    qNext = (qCtrl[iPre + 2] + qCtrl[iPre + 1]) / 2
    
    # 求解vol_out = (t - tPre) * (qPre + qCurrent) / 2 + (tNext - t) * qNext
    t = (vol_out + (qCurrent + qPre) * tPre / 2 - qNext * tNext) / ((qCurrent + qPre) / 2 - qNext)

    return t

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
        XLD_t_in = tempData.get('t', [])
        XLD_q_in = tempData.get('Inflow', [])

    with open(smx_file, 'r') as f:
        tempData = json.load(f)
        SMX_CapCurve = {
            'WL': tempData.get('CapCurve', {}).get('WL', []),
            'Vol': tempData.get('CapCurve', {}).get('Vol', [])
        }
        SMX_t_in = tempData.get('t', [])
        SMX_q_in = tempData.get('Inflow', [])
except FileNotFoundError as e:
    print(f"Error: {e}")
except json.JSONDecodeError as e:
    print(f"Error decoding JSON: {e}")

def generate_from_SMX(i, xld_plan, smx_plan):
    global SMX_t_in, SMX_q_in, SMX_HyperPara, SMX_CapCurve, iniVol_SMX
    
    # 随机生成三门峡的起涨时刻
    #smx_plan['t'][1] = random.uniform(xld_plan['t'][3]-12, SMX_t_in[-1])
    smx_plan['t'][1] = random.uniform(xld_plan['t'][3]-36, xld_plan['t'][3]+72)
    
    # 计算三门峡水库达到泄空流量的时刻
    q1 = interpolate(smx_plan['t'][1], SMX_t_in, SMX_q_in)
    q2 = smx_plan['q'][2]
    qIncrRate = 134.8
    smx_plan['t'][2] = smx_plan['t'][1] + (q2 - q1) / qIncrRate
    # 如果该时刻大于SMX_t_in的最后一个时刻，则返回
    if smx_plan['t'][2] > SMX_t_in[-1]:
        return xld_plan, smx_plan, False

    # 更新XLD_Plan
    xld_plan['t'][5] = smx_plan['t'][2]
    
    # 随机生成对接三门峡流量时的控制流量
    xld_plan['q'][5] = random.uniform(smx_plan['q'][2], xld_plan['q'][2])
    xld_plan['q'][6] = xld_plan['q'][5]
    
    # 随机生成三门峡水库泄空冲刷的结束时刻
    minWL_SMX = 304.8  # 2020年三门峡水库最低水位是288.85米
    # 如果minWL_SMX小于SMX_CapCurve['WL']的第一个值，则提示并暂停
    if minWL_SMX < SMX_CapCurve['WL'][0]:
        print(f"Error: minWL_SMX ({minWL_SMX}) is less than the first value of SMX_CapCurve['WL'] ({SMX_CapCurve['WL'][0]})")
        #暂停
        input("Press Enter to continue...")
        
    WL_EndFlush = random.uniform(minWL_SMX, SMX_HyperPara['WlFldContr'])
    vol_EndFlush = interpolate(WL_EndFlush, SMX_CapCurve['WL'], SMX_CapCurve['Vol'])
    netOutflowVol = iniVol_SMX - vol_EndFlush
    smx_plan['t'][3], flag= CalculateT(netOutflowVol, SMX_t_in, SMX_q_in, 3, 2, 1, i)
    if flag == False:
        return xld_plan, smx_plan, False
    # 如果该时刻大于SMX_t_in的最后一个时刻，则返回
    if smx_plan['t'][3] > SMX_t_in[-1]:
        return xld_plan, smx_plan, False
    xld_plan['t'][6] = smx_plan['t'][3]
    xld_plan['t'][7] = xld_plan['t'][6]

    # 计算三门峡开始回蓄时刻
    smx_plan['t'][4] = smx_plan['t'][3] + 6
    if smx_plan['t'][4] > SMX_t_in[-1]:
        return xld_plan, smx_plan, False
    
    # 计算三门峡水库回蓄结束时刻
    vol_FldContr_SMX = interpolate(SMX_HyperPara['WlFldContr'], SMX_CapCurve['WL'], SMX_CapCurve['Vol'])
    netOutflowVol = iniVol_SMX - vol_FldContr_SMX
    smx_plan['t'][5], flag = CalculateT(netOutflowVol, SMX_t_in, SMX_q_in, 5, 2, 1, i)
    if flag == False:
        return xld_plan, smx_plan, False
    smx_plan['t'][6] = smx_plan['t'][5]
    
    # 结束时刻暂时采用交互式方案生成器输入值，下面计算小浪底开始回蓄时刻
    vol_210 = interpolate(210, XLD_CapCurve['WL'], XLD_CapCurve['Vol'])
    netOutflowVol = iniVol_XLD - (vol_210 + XLD_HyperPara['volWatSupply'])
    xld_plan['t'][8] = CalculateRefillT(netOutflowVol, smx_plan['t'], smx_plan['q'], SMX_t_in, SMX_q_in, xld_plan['t'], xld_plan['q'])
    # 如果该时刻大于xld_plan的最后时刻，或小于xld_plan['t'][7],则返回false
    if xld_plan['t'][8] > xld_plan['t'][-1] or xld_plan['t'][8] < xld_plan['t'][7]:
        return xld_plan, smx_plan, False
    xld_plan['t'][9] = xld_plan['t'][8]

    return xld_plan, smx_plan, True



iniWL_XLD = 250.8
#在终端提示输入小浪底初始水位，并显示当前默认输入值是iniWL_XLD，如果用户输入为空，则使用默认值
iniWL_XLD = input(f"请输入小浪底初始水位: (默认值: {iniWL_XLD})")
if iniWL_XLD == '':
    iniWL_XLD = 250.8
else:
    iniWL_XLD = float(iniWL_XLD)
xx = XLD_CapCurve['WL']
yy = XLD_CapCurve['Vol']
iniVol_XLD = interpolate(iniWL_XLD, xx, yy)

iniWL_SMX = 318
#在终端提示输入三门峡初始水位，并显示当前默认输入值是iniWL_SMX，如果用户输入为空，则使用默认值
iniWL_SMX = input(f"请输入三门峡初始水位: (默认值: {iniWL_SMX})")
if iniWL_SMX == '':
    iniWL_SMX = 318
else:
    iniWL_SMX = float(iniWL_SMX)
xx = SMX_CapCurve['WL']
yy = SMX_CapCurve['Vol']
iniVol_SMX = interpolate(iniWL_SMX, xx, yy)

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
    #计算达到小浪底汛限水位的时间
    Vol_FldContr = interpolate(XLD_HyperPara['WlFldContr'], XLD_CapCurve['WL'], XLD_CapCurve['Vol'])
    netOutflowVol = iniVol_XLD - Vol_FldContr
    XLD_Plan[i]['t'][3], flag = CalculateT(netOutflowVol, XLD_t_in, XLD_q_in, 3, 1, 1, i)
    #计算达到小浪底对接水位的时间
    Vol_StartReg = interpolate(XLD_HyperPara['WlReg'], XLD_CapCurve['WL'], XLD_CapCurve['Vol'])
    netOutflowVol = iniVol_XLD - Vol_StartReg
    XLD_Plan[i]['t'][4], flag = CalculateT(netOutflowVol, XLD_t_in, XLD_q_in, 4, 1, 2, i)
    #三门峡t2之后的生成过程
    attempts = 0
    max_attempts = 100  # 设置最大尝试次数，以防无限循环
    while True:
        XLD_Plan[i], SMX_Plan[i], flag = generate_from_SMX(i, XLD_Plan[i], SMX_Plan[i])
        if flag:
            break
        attempts += 1
        if attempts >= max_attempts:
            print(f"Plan {i}: Failed to generate SMX plan after {max_attempts} attempts")
            break

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