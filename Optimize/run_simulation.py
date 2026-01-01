import os
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
import numpy as np
from tkinter import filedialog
import time

global case
case = [None]  # 0号位置放个None

def select_directory():
    """弹出目录选择对话框让用户选择目录"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 弹出目录选择对话框
    directory = filedialog.askdirectory(
        title="选择可执行文件所在目录",
        initialdir=os.path.expanduser("~")  # 默认从用户主目录开始
    )
    
    # 如果用户取消选择，返回None
    if not directory:
        print("用户取消了目录选择")
        return None
    
    return directory

def run_simulation(argument, exe_directory, test=False):
    """运行单个模拟"""
    executable = "1D_RiverNet_OCTC.exe"
    try:
        if test:
            return f"Simulation for {argument} is skipped."
        else:
            # 正常模式：运行完整模拟
            cmd = [os.path.join(exe_directory, executable), argument]
            print(f"运行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, 
                                  cwd=exe_directory,  # 设置工作目录
                                  creationflags=subprocess.CREATE_NEW_CONSOLE,  # 创建新的控制台窗口
                                  check=True)
            return f"Process for {argument} completed successfully."
    except subprocess.TimeoutExpired:
        # 测试模式下，超时是正常的，因为我们手动终止了程序
        if test:
            return f"Title test for {argument} completed (timeout as expected)."
        else:
            return f"Timeout occurred for {argument}"
    except subprocess.CalledProcessError as e:
        return f"An error occurred for {argument}: {e}"

def evaluate_case(case_number, exe_directory):
    global case
    """评估单个case的结果，返回评估分数"""
    case_dir = os.path.join(exe_directory, f"case{case_number}")
    out_dir = os.path.join(case_dir, "Output")
    #检查out_dir下有几个格式为"Reach  x"的文件夹
    reach_dirs = [d for d in os.listdir(out_dir) if d.startswith("Reach")]
    reach_num = len(reach_dirs)
    
    #循环reach_dirs
    for i, reach_dir in enumerate(reach_dirs):
        iReach = i + 1  # 如果想从1开始编号
        # 或者 iReach = i  # 如果想从0开始编号
        
        # 确保iReach键存在
        if iReach not in case[case_number]:
            case[case_number][iReach] = {}
        
        # 检查reach_dir下有几个格式为”FlowCS  x.txt"的文件
        flowcs_files = [f for f in os.listdir(os.path.join(out_dir, reach_dir)) if f.startswith("FlowCS")]
        flowcs_num = len(flowcs_files)

        # 读取FlowCS  1.txt中的数据
        result_file = os.path.join(out_dir, reach_dir, "FlowCS  1.txt")
        if not os.path.exists(result_file):
            print(f"Result file not found for case{case_number}")
            return 0
        
        with open(result_file, 'r') as f:
            # f中除了前两行外，剩下部分是一个table，读取table中的第4列，存入case[case_number][iReach]["Qin"]
            lines = f.readlines()[2:]
            # 创建列表来存储时间、流量和含沙量
            time_values = []
            qin_values = []
            sus_values = []
            for line in lines:
                if line.strip():
                    columns = line.split()
                    if len(columns) >= 11:
                        try:
                            time_values.append(float(columns[1]))
                            qin_values.append(float(columns[3]))
                            sus_values.append(float(columns[10]))
                        except ValueError:
                            time_values.append(np.nan)
                            qin_values.append(np.nan)
                            sus_values.append(np.nan)
                            print(f"警告: 在 case{case_number} 的 FlowCS 1.txt 中遇到无效数据行，已停止解析该文件。")
                            break

            # 将列表转换为NumPy数组
            case[case_number][iReach]["Time"] = np.array(time_values)
            case[case_number][iReach]["Qin"] = np.array(qin_values)
            case[case_number][iReach]["SusIn"] = np.array(sus_values)
   
        # 读取最后一个FlowCS文件中的数据
        result_file = os.path.join(out_dir, reach_dir, "FlowCS  {}.txt".format(flowcs_num))
        if not os.path.exists(result_file):
            print(f"Result file not found for case{case_number}")
            return 0

        with open(result_file, 'r') as f:
            # f中除了前两行外，剩下部分是一个table，读取table中的第4列，存入case[case_number][iReach]["Qout"]
            lines = f.readlines()[2:]
            # 创建列表来存储流量和含沙量
            qin_values = []
            sus_values = []
            z_values = []
            for line in lines:
                if line.strip():
                    columns = line.split()
                    if len(columns) >= 11:
                        try:
                            qin_values.append(float(columns[3]))
                            sus_values.append(float(columns[10]))
                            z_values.append(float(columns[2]))
                        except ValueError:
                            qin_values.append(np.nan)
                            sus_values.append(np.nan)
                            z_values.append(np.nan)
                            print(f"警告: 在 case{case_number} 的 FlowCS {flowcs_num}.txt 中遇到无效数据行，已停止解析该文件。")
                            break

            # 将列表转换为NumPy数组
            case[case_number][iReach]["Qout"] = np.array(qin_values)
            case[case_number][iReach]["SusOut"] = np.array(sus_values)
            # 将z_values最后一个值存储
            case[case_number][iReach]["Zend_lastCS"] = z_values[-1]
        
        # 计算入库沙量
        qs_in = case[case_number][iReach]["Qin"] * case[case_number][iReach]["SusIn"]
        try:
            qs_in_integral = np.trapz(qs_in, case[case_number][iReach]["Time"])
        except Exception as e:
            print(f"警告: 在 case{case_number} 的 FlowCS {flowcs_num}.txt 中计算入库沙量时发生错误：{e}")
            return 0

        # 计算出库沙量
        qs_out = case[case_number][iReach]["Qout"] * case[case_number][iReach]["SusOut"]
        try:
            qs_out_integral = np.trapz(qs_out, case[case_number][iReach]["Time"])
        except Exception as e:
            print(f"警告: 在 case{case_number} 的 FlowCS {flowcs_num}.txt 中计算出库沙量时发生错误：{e}")
            return 0

        # 计算入库沙量和出库沙量的差值
        qs_diff = qs_out_integral - qs_in_integral
        case[case_number][iReach]["QsDiff"] = qs_diff*3600/1000  # 将单位转换为t
    # 结束河段循环

    # 读取out_dir下的ObjectiveFunctionsValue.TXT
    result_path = os.path.join(out_dir, "ObjectiveFunctionsValue.TXT")
    wait_time = 0
    while not os.path.exists(result_path) and wait_time < 10:
        time.sleep(1)
        wait_time += 1
    if not os.path.exists(result_path):
        print(f"Result file not found for case{case_number}: {result_path}")
        return 0
    with open(result_path, 'r') as f:
        lines = f.readlines()
        # 读取第2行，存入temp_id中
        temp_id = lines[1].strip()
        # 河段循环，如果iReach等于temp_id，则读取第4行，存入case[case_number][iReach]["Obj_flood"],否则存入0
        for iReach in range(1, reach_num + 1):
            if iReach == int(temp_id):
                case[case_number][iReach]["Obj_flood"] = float(lines[3].strip())
            else:
                case[case_number][iReach]["Obj_flood"] = 0

    # 检查是否模拟完成
    result_path = os.path.join(out_dir, "TimeSM.TXT")
    # 读取第一行，检查是不是"ok"
    with open(result_path, 'r') as f:
        first_line = f.readline().strip()
        if first_line != "ok":
            return 0
    return 1



def run_all_simulations(planNum, exe_directory=None, test=False):
    global case
    # 创建planNum+1个字典的列表（0号位置不用）
    case = [None] + [dict() for _ in range(planNum)]    
    """运行所有模拟"""
    # 如果没有提供exe_directory，弹出目录选择对话框
    if exe_directory is None:
        exe_directory = select_directory()
        if exe_directory is None:
            print("未选择目录，退出程序")
            return
    
    # 检查exe_directory是否存在
    if not os.path.exists(exe_directory):
        print(f"错误: 目录 {exe_directory} 不存在")
        return
    
    # 检查可执行文件是否存在
    executable = "1D_RiverNet_OCTC.exe"
    if not os.path.exists(os.path.join(exe_directory, executable)):
        print(f"错误: 可执行文件 {executable} 在目录 {exe_directory} 中未找到")
        return
    
    # 准备参数
    arguments = [f"case{i+1}" for i in range(planNum)]
    
    # 初始化状态数组
    case_status = [1] * planNum
    
    # 运行模拟
    print(f"开始运行{planNum}个模拟{'（仅测试窗口标题）' if test else ''}")
    print(f"使用目录: {exe_directory}")
    
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_simulation, arg, exe_directory, test) for arg in arguments]
        # 修改这里：去掉 as_completed，直接遍历 futures
        # 这样 i=0 时对应 case1 的 future，i=1 时对应 case2 的 future...
        # future.result() 会阻塞直到该特定任务完成
        for i, future in enumerate(futures):
            print(future.result())
            # 在每个模拟完成后评估结果
            case_number = i + 1
            
            # --- 建议修改开始：增加异常捕获和暂停 ---
            try:
                case_status[i] = evaluate_case(case_number, exe_directory)
            except Exception as e:
                print(f"Error evaluating case {case_number}: {e}")
                print(">>> 发生错误，程序已暂停。请检查报错信息和对应的 Case 文件夹。")
                input(">>> 按回车键(Enter)继续...")
                case_status[i] = 0  # 标记该 case 失败
            # --- 建议修改结束 ---

    if not test:
        print("Case evaluation results:", case_status)
    else:
        print("窗口标题测试完成")

    return case, case_status  # 返回case变量和状态

if __name__ == "__main__":
    # 当作为独立程序运行时
    import argparse
    
    parser = argparse.ArgumentParser(description='运行水库模拟')
    parser.add_argument('--planNum', type=int, help='方案数量')
    parser.add_argument('--exe_dir', type=str, help='可执行文件目录')
    parser.add_argument('--test', action='store_true', help='仅测试窗口标题')
    
    args = parser.parse_args()
    
    # 如果没有提供planNum，则提示用户输入
    if args.planNum is None:
        planNum = input("请输入方案数量(planNum): ")
        planNum = int(planNum)
    else:
        planNum = args.planNum
    
    # 运行模拟
    run_all_simulations(planNum, args.exe_dir, args.test)