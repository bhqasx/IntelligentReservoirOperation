#!/usr/bin/env python3
"""
PopHistory.json 数据分析和可视化工具

此脚本用于分析NSGA-III优化算法的历史数据，生成四个子图：
1. 第一代和最后一代的第1、2目标函数值对比
2. 第一代和最后一代的第1、3目标函数值对比
3. 第一代和最后一代的第2、3目标函数值对比
4. 三个目标函数值随代数变化的平均值趋势图
"""

import json
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')  # 使用支持交互的后端
from mpl_toolkits.mplot3d import Axes3D
try:
    import mplcursors
except ImportError:
    mplcursors = None

try:
    from scipy.spatial import ConvexHull
except ImportError:
    ConvexHull = None
import tkinter as tk
from tkinter import filedialog
from tkinter import simpledialog


def sanitize_path_text(value):
    if not isinstance(value, str):
        return value
    return value.translate({
        0x202A: None,
        0x202B: None,
        0x202C: None,
        0x202D: None,
        0x202E: None,
        0x2066: None,
        0x2067: None,
        0x2068: None,
        0x2069: None,
    }).strip()


def resolve_pop_history_path(filename='PopHistory.json'):
    if len(sys.argv) > 1:
        case_name = sanitize_path_text(sys.argv[1])
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        case_folder = os.path.join(repo_root, 'Cases', case_name)
        if not os.path.isdir(case_folder):
            raise FileNotFoundError(f"未找到案例目录: {case_folder}")

        target_path = os.path.join(case_folder, filename)
        print(f"使用命令行案例目录: {case_folder}")
        return target_path

    return filename

def load_pop_history(filename='PopHistory.json'):
    """
    读取PopHistory.json文件

    Parameters:
    filename: 文件名

    Returns:
    history_data: 包含所有代数数据的字典
    generations: 代数列表（排序后的）
    """
    target_path = resolve_pop_history_path(filename)
    if target_path != filename:
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)

            generations = sorted([int(gen) for gen in history_data['generations'].keys()])

            print(f"成功读取PopHistory.json文件")
            print(f"包含 {len(generations)} 代数据：第 {generations[0]} 代到第 {generations[-1]} 代")
            print(f"每代有 {len(history_data['generations'][str(generations[0])]['obj'])} 个个体")
            print(f"每个个体有 {len(history_data['generations'][str(generations[0])]['obj'][0])} 个目标函数")

            return history_data, generations, target_path
        except FileNotFoundError:
            print(f"错误：找不到文件 {target_path}")
            return None, None, None
        except json.JSONDecodeError as e:
            print(f"错误：JSON文件格式错误 - {e}")
            return None, None, None
        except Exception as e:
            print(f"错误：读取文件时发生未知错误 - {e}")
            return None, None, None

    while True:
        answer = input("PopHistory.json 是否在当前目录？(Y/N): ").strip().lower()
        if answer in ('y', ''):
            break
        if answer == 'n':
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            root.update()
            selected_dir = filedialog.askdirectory(
                parent=root,
                title='选择包含 PopHistory.json 的目录',
                initialdir=os.getcwd()
            )
            root.destroy()
            if not selected_dir:
                manual_dir = input("未选择目录，请手动输入包含 PopHistory.json 的目录: ").strip()
                if not manual_dir:
                    print("错误：未选择目录")
                    return None, None, None
                target_path = os.path.join(manual_dir, filename)
            else:
                target_path = os.path.join(selected_dir, filename)
            break
        print("请输入 Y 或 N。")

    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            history_data = json.load(f)

        # 获取所有代数并排序
        generations = sorted([int(gen) for gen in history_data['generations'].keys()])

        print(f"成功读取PopHistory.json文件")
        print(f"包含 {len(generations)} 代数据：第 {generations[0]} 代到第 {generations[-1]} 代")
        print(f"每代有 {len(history_data['generations'][str(generations[0])]['obj'])} 个个体")
        print(f"每个个体有 {len(history_data['generations'][str(generations[0])]['obj'][0])} 个目标函数")

        return history_data, generations, target_path

    except FileNotFoundError:
        print(f"错误：找不到文件 {target_path}")
        return None, None, None
    except json.JSONDecodeError as e:
        print(f"错误：JSON文件格式错误 - {e}")
        return None, None, None
    except Exception as e:
        print(f"错误：读取文件时发生未知错误 - {e}")
        return None, None, None

def export_typical_plans(history_data, generations, target_path):
    """
    从最后一代中导出典型个体的调度方案

    Parameters:
    history_data: 历史数据字典
    generations: 代数列表
    target_path: PopHistory.json 的完整路径
    """
    last_gen_key = str(generations[-1])
    last_gen_data = history_data['generations'][last_gen_key]
    last_gen_obj = np.array(last_gen_data['obj'])

    # 对最后一代目标函数做正则化：(value - max) / (min - max)
    last_gen_obj_min = np.min(last_gen_obj, axis=0)
    last_gen_obj_max = np.max(last_gen_obj, axis=0)
    last_gen_obj_range = last_gen_obj_min - last_gen_obj_max
    last_gen_obj_normalized = np.divide(
        last_gen_obj - last_gen_obj_max,
        last_gen_obj_range,
        out=np.zeros_like(last_gen_obj, dtype=float),
        where=last_gen_obj_range != 0
    )

    # 计算最终代每个个体的 Coupling Coordination Degree (CCD) 指标
    T = np.mean(last_gen_obj_normalized, axis=1)
    C = 3 * np.power(np.prod(last_gen_obj_normalized, axis=1), 1 / 3)
    CCD = np.power(T * C, 1 / 2)

    id_Min_SMX = int(np.argmin(last_gen_obj[:, 0]))
    id_Min_XLD = int(np.argmin(last_gen_obj[:, 1]))
    id_Min_flood = int(np.argmin(last_gen_obj[:, 2]))
    id_Max_CCD = int(np.argmax(CCD))

    def build_plan_entry(plan_name, individual_id):
        return {
            'PlanName': plan_name,
            'Plan_SMX': {
                't': last_gen_data['P_plans_SMX'][individual_id]['t'],
                'q': last_gen_data['P_plans_SMX'][individual_id]['q']
            },
            'Plan_XLD': {
                't': last_gen_data['P_plans_XLD'][individual_id]['t'],
                'q': last_gen_data['P_plans_XLD'][individual_id]['q']
            }
        }

    typical_plans_data = {
        'Typical_Plans': [
            build_plan_entry('Min_SMX', id_Min_SMX),
            build_plan_entry('Min_XLD', id_Min_XLD),
            build_plan_entry('Min_flood', id_Min_flood),
            build_plan_entry('Max_CCD', id_Max_CCD)
        ]
    }

    output_path = os.path.join(os.path.dirname(target_path), 'Typical_Plans.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(typical_plans_data, f, ensure_ascii=False, indent=2)

    print(f"已输出 Typical_Plans.json：{output_path}")
    print(f"最后一代目标函数1最小个体序号 id_Min_SMX = {id_Min_SMX}")
    print(f"最后一代目标函数2最小个体序号 id_Min_XLD = {id_Min_XLD}")
    print(f"最后一代目标函数3最小个体序号 id_Min_flood = {id_Min_flood}")
    print(f"最后一代CCD最大个体序号 id_Max_CCD = {id_Max_CCD}")

def extract_objectives_by_generation(history_data, generations):
    """
    提取每一代的目标函数值

    Parameters:
    history_data: 历史数据字典
    generations: 代数列表

    Returns:
    obj_by_gen: 按代数组织的numpy数组，形状为 (n_generations, n_individuals, n_objectives)
    """
    n_generations = len(generations)
    n_individuals = len(history_data['generations'][str(generations[0])]['obj'])
    n_objectives = len(history_data['generations'][str(generations[0])]['obj'][0])

    obj_by_gen = np.zeros((n_generations, n_individuals, n_objectives))

    for i, gen in enumerate(generations):
        gen_data = history_data['generations'][str(gen)]
        obj_by_gen[i] = np.array(gen_data['obj'])

    return obj_by_gen

def extract_constraints_by_generation(history_data, generations):
    """
    提取每一代的约束违反值

    Parameters:
    history_data: 历史数据字典
    generations: 代数列表

    Returns:
    con_by_gen: 按代数组织的numpy数组，形状为 (n_generations, n_individuals, n_constraints)
    """
    n_generations = len(generations)
    n_individuals = len(history_data['generations'][str(generations[0])]['ConstraintViolation'])
    n_constraints = len(history_data['generations'][str(generations[0])]['ConstraintViolation'][0])

    con_by_gen = np.zeros((n_generations, n_individuals, n_constraints))

    for i, gen in enumerate(generations):
        gen_data = history_data['generations'][str(gen)]
        con_by_gen[i] = np.array(gen_data['ConstraintViolation'])

    return con_by_gen

def calculate_objective_means(obj_by_gen):
    """
    计算每一代每个目标函数的平均值

    Parameters:
    obj_by_gen: 按代数组织的numpy数组

    Returns:
    obj_means: 形状为 (n_generations, n_objectives) 的平均值数组
    """
    return np.mean(obj_by_gen, axis=1)

def _enable_text_editing(fig, axes):
    # Allow click-to-edit for axis labels and titles
    for ax in axes:
        texts = [ax.title, ax.xaxis.label, ax.yaxis.label]
        if hasattr(ax, "zaxis"):
            texts.append(ax.zaxis.label)
        for text in texts:
            text.set_picker(True)

    def _on_pick(event):
        text = event.artist
        if not hasattr(text, "get_text"):
            return
        new_text = simpledialog.askstring("Edit Label", "Enter new text:", initialvalue=text.get_text())
        if new_text is not None:
            text.set_text(new_text)
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("pick_event", _on_pick)


def _attach_hover_cursor(artists, annotation_builder):
    if mplcursors is None:
        return

    cursor = mplcursors.cursor(artists, hover=True)

    @cursor.connect("add")
    def _on_add(sel):
        sel.annotation.set_text(annotation_builder(sel))

    @cursor.connect("remove")
    def _on_remove(sel):
        sel.annotation.set_visible(False)

def create_comparison_plots(obj_by_gen, con_by_gen, generations):
    """
    创建五个子图的对比分析

    Parameters:
    obj_by_gen: 按代数组织的numpy数组
    con_by_gen: 按代数组织的约束违反值数组
    generations: 代数列表
    """
    # Set font to Times New Roman
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['axes.unicode_minus'] = False

    # 创建5个子图 (3x2布局)
    fig, axes = plt.subplots(3, 2, figsize=(16, 20))
    fig.suptitle('NSGA-III Optimization Analysis', fontsize=16, fontweight='bold')

    # 获取第一代和最后一代的数据
    first_gen_data = obj_by_gen[0]  # 第一代
    last_gen_data = obj_by_gen[-1]  # 最后一代

    # 子图1：第1、2目标函数对比
    ax1 = axes[0, 0]
    sc1_1 = ax1.scatter(first_gen_data[:, 0], first_gen_data[:, 1], c='blue', alpha=0.7, label=f'Gen {generations[0]}', marker='o')
    sc1_2 = ax1.scatter(last_gen_data[:, 0], last_gen_data[:, 1], c='red', alpha=0.7, label=f'Gen {generations[-1]}', marker='s')
    ax1.set_xlabel('Objective 1 (-SMX QsDiff)')
    ax1.set_ylabel('Objective 2 (-XLD QsDiff)')
    ax1.set_title('Objective 1 vs Objective 2')
    ax1.legend()
    ax1.get_legend().set_draggable(True)
    ax1.grid(True, alpha=0.3)

    # 添加鼠标悬停显示个体编号
    def build_annotation1(sel):
        if sel.artist == sc1_1:
            return f'Gen {generations[0]} Individual {sel.index}'
        return f'Gen {generations[-1]} Individual {sel.index}'
    _attach_hover_cursor([sc1_1, sc1_2], build_annotation1)

    # 子图2：第1、3目标函数对比
    ax2 = axes[0, 1]
    sc2_1 = ax2.scatter(first_gen_data[:, 0], first_gen_data[:, 2], c='blue', alpha=0.7, label=f'Gen {generations[0]}', marker='o')
    sc2_2 = ax2.scatter(last_gen_data[:, 0], last_gen_data[:, 2], c='red', alpha=0.7, label=f'Gen {generations[-1]}', marker='s')
    ax2.set_xlabel('Objective 1 (-SMX QsDiff)')
    ax2.set_ylabel('Objective 3 (Flood Obj)')
    ax2.set_title('Objective 1 vs Objective 3')
    ax2.legend()
    ax2.get_legend().set_draggable(True)
    ax2.grid(True, alpha=0.3)

    # 添加鼠标悬停显示个体编号
    def build_annotation2(sel):
        if sel.artist == sc2_1:
            return f'Gen {generations[0]} Individual {sel.index}'
        return f'Gen {generations[-1]} Individual {sel.index}'
    _attach_hover_cursor([sc2_1, sc2_2], build_annotation2)

    # 子图3：第2、3目标函数对比
    ax3 = axes[1, 0]
    sc3_1 = ax3.scatter(first_gen_data[:, 1], first_gen_data[:, 2], c='blue', alpha=0.7, label=f'Gen {generations[0]}', marker='o')
    sc3_2 = ax3.scatter(last_gen_data[:, 1], last_gen_data[:, 2], c='red', alpha=0.7, label=f'Gen {generations[-1]}', marker='s')
    ax3.set_xlabel('Objective 2 (-XLD QsDiff)')
    ax3.set_ylabel('Objective 3 (Flood Obj)')
    ax3.set_title('Objective 2 vs Objective 3')
    ax3.legend()
    ax3.get_legend().set_draggable(True)
    ax3.grid(True, alpha=0.3)

    # 添加鼠标悬停显示个体编号
    def build_annotation3(sel):
        if sel.artist == sc3_1:
            return f'Gen {generations[0]} Individual {sel.index}'
        return f'Gen {generations[-1]} Individual {sel.index}'
    _attach_hover_cursor([sc3_1, sc3_2], build_annotation3)

    # 子图4：目标函数平均值随代数变化趋势
    ax4 = axes[1, 1]
    obj_means = calculate_objective_means(obj_by_gen)

    # 创建右侧副纵轴
    ax4_right = ax4.twinx()

    # 绘制前两个目标函数在主轴上
    colors = ['blue', 'green']
    labels = ['Objective 1 (-SMX QsDiff)', 'Objective 2 (-XLD QsDiff)']
    lines_left = []
    for i in range(2):
        line, = ax4.plot(generations, obj_means[:, i], color=colors[i], linewidth=2,
                        marker='o', markersize=4, label=labels[i])
        lines_left.append(line)

    # 绘制第三个目标函数在右侧轴上
    line_right, = ax4_right.plot(generations, obj_means[:, 2], color='red', linewidth=2,
                                marker='o', markersize=4, label='Objective 3 (Flood Obj)')

    # 设置轴标签
    ax4.set_xlabel('Generation')
    ax4.set_ylabel('Mean Objective 1 and 2')
    ax4_right.set_ylabel('Mean Objective 3')

    ax4.set_title('Mean Objectives over Generations')
    
    # 合并图例
    lines = lines_left + [line_right]
    labels = [l.get_label() for l in lines]
    ax4.legend(lines, labels, loc='upper left')
    ax4.get_legend().set_draggable(True)
    
    ax4.grid(True, alpha=0.3)

    # 子图5：约束违反值随代数变化趋势
    ax5 = axes[2, 0]
    con_means = np.mean(con_by_gen, axis=1)  # 计算每一代的约束违反值平均值

    # 绘制三个约束违反值
    colors = ['blue', 'orange', 'brown']
    labels = ['Constraint 1 Violation', 'Constraint 2 Violation', 'Constraint 3 Violation']
    for i in range(3):
        ax5.plot(generations, con_means[:, i], color=colors[i], linewidth=2,
                marker='o', markersize=4, label=labels[i])

    # 设置轴标签
    ax5.set_xlabel('Generation')
    ax5.set_ylabel('Constraint Violation')
    ax5.set_title('Constraint Violations over Generations')
    ax5.legend()
    ax5.get_legend().set_draggable(True)
    ax5.grid(True, alpha=0.3)

    # 调整子图间距
    plt.tight_layout()
    plt.subplots_adjust(top=0.92, hspace=0.3, wspace=0.2)

    _enable_text_editing(fig, axes.flatten())
    return fig

def create_3d_plot(obj_by_gen, generations):
    """
    创建3D散点图和凸包表面

    Parameters:
    obj_by_gen: 按代数组织的numpy数组
    generations: 代数列表
    """
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    first_gen_data = obj_by_gen[0]
    last_gen_data = obj_by_gen[-1]

    # 绘制散点
    ax.scatter(first_gen_data[:, 0], first_gen_data[:, 1], first_gen_data[:, 2], 
               c='blue', alpha=0.7, label=f'Gen {generations[0]}')
    ax.scatter(last_gen_data[:, 0], last_gen_data[:, 1], last_gen_data[:, 2], 
               c='red', alpha=0.7, label=f'Gen {generations[-1]}', marker='s')
    # ax.scatter(last_gen_data[:, 0], last_gen_data[:, 1], last_gen_data[:, 2],
    #            c='red', alpha=0.7, label=f'Gen {generations[-1]}', marker='s')

    ys_create_surf=0
    if ys_create_surf:
        if ConvexHull is None:
            print("警告：未安装 scipy，跳过 3D 凸包表面绘制。")
            ys_create_surf = 0

    if ys_create_surf:
        # 计算并绘制第一代的凸包表面
        hull1 = ConvexHull(first_gen_data)
        ax.plot_trisurf(first_gen_data[:, 0], first_gen_data[:, 1], first_gen_data[:, 2], 
                    triangles=hull1.simplices, color='blue', alpha=0.3)

        # 计算并绘制最后一代的凸包表面
        hull2 = ConvexHull(last_gen_data)
        ax.plot_trisurf(last_gen_data[:, 0], last_gen_data[:, 1], last_gen_data[:, 2], 
                        triangles=hull2.simplices, color='red', alpha=0.3)

    ax.set_xlabel('Objective 1 (-SMX QsDiff)')
    ax.set_ylabel('Objective 2 (-XLD QsDiff)')
    ax.set_zlabel('Objective 3 (Flood Obj)')
    ax.set_title('Gen 1 vs Final Gen: 3D Objective Distribution')
    legend = ax.legend()
    if legend:
        legend.set_draggable(True)

    _enable_text_editing(fig, [ax])
    return fig

def create_3d_layers(obj_by_gen, generations, history_data):
    """
    根据指定代数，将同一帕累托分层的解在3D空间用折线连起来
    """
    gen_input = input("请输入要绘制3D分层连线的代数（直接回车跳过）: ").strip()
    if not gen_input:
        print("已跳过3D分层连线绘制。")
        return
    try:
        gen = int(gen_input)
    except ValueError:
        print("输入的代数无效，已跳过绘制。")
        return
    if gen not in generations:
        print(f"代数 {gen} 不在数据范围内，已跳过绘制。")
        return

    gen_idx = generations.index(gen)
    ranks = history_data['generations'][str(gen)].get('pareto_ranks', [])
    if not ranks:
        print(f"第{gen}代缺少帕累托分层信息，无法绘制。")
        return
    if len(ranks) != len(obj_by_gen[gen_idx]):
        print(f"第{gen}代的分层数量与个体数不匹配，无法绘制。")
        return

    data = obj_by_gen[gen_idx]
    rank_to_indices = {}
    for idx, rank in enumerate(ranks):
        rank_to_indices.setdefault(rank, []).append(idx)

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    cmap = plt.cm.get_cmap('tab10', len(rank_to_indices))

    ax.scatter(data[:, 0], data[:, 1], data[:, 2],
               c='lightgray', alpha=0.5, label='Individuals')

    for line_idx, (rank, indices) in enumerate(sorted(rank_to_indices.items())):
        ordered = sorted(indices, key=lambda i: data[i, 0])
        coords = data[ordered]
        ax.plot(coords[:, 0], coords[:, 1], coords[:, 2],
                color=cmap(line_idx), linewidth=2, marker='o',
                label=f'Rank {rank}')

    ax.set_xlabel('Objective 1 (-SMX QsDiff)')
    ax.set_ylabel('Objective 2 (-XLD QsDiff)')
    ax.set_zlabel('Objective 3 (Flood Obj)')
    ax.set_title(f'Generation {gen}: Pareto Rank Connections')
    legend = ax.legend()
    if legend:
        legend.set_draggable(True)

    _enable_text_editing(fig, [ax])
    plt.show(block=True)

def plot_gene_evolution(history_data, generations):
    """
    绘制某个基因在所有代数中的演化过程

    Parameters:
    history_data: 历史数据字典
    generations: 代数列表
    """
    # 询问用户选择SMX还是XLD
    while True:
        reservoir_input = input("请选择观察哪个水库的基因？(1=SMX, 2=XLD，直接回车跳过): ").strip()
        if reservoir_input == '':
            print("已跳过基因演化图绘制。")
            return
        if reservoir_input in ('1', '2'):
            break
        print("请输入 1 或 2。")
    
    reservoir_key = 'P_plans_SMX' if reservoir_input == '1' else 'P_plans_XLD'
    reservoir_name = 'SMX' if reservoir_input == '1' else 'XLD'
    
    # 询问用户选择t序列还是q序列
    while True:
        seq_input = input("请选择观察 t 序列还是 q 序列？(t/q): ").strip().lower()
        if seq_input in ('t', 'q'):
            break
        print("请输入 t 或 q。")
    
    # 获取基因序列长度
    first_gen_data = history_data['generations'][str(generations[0])]
    sample_seq = first_gen_data[reservoir_key][0][seq_input]
    seq_length = len(sample_seq)
    
    # 询问用户选择基因索引
    while True:
        idx_input = input(f"请输入要观察的基因索引 (0 ~ {seq_length - 1}): ").strip()
        try:
            gene_idx = int(idx_input)
            if 0 <= gene_idx < seq_length:
                break
            print(f"索引超出范围，请输入 0 ~ {seq_length - 1} 之间的整数。")
        except ValueError:
            print("请输入有效的整数。")
    
    # 提取每代所有个体的指定基因值
    all_gen_values = []
    all_gen_indices = []
    
    for gen in generations:
        gen_data = history_data['generations'][str(gen)]
        plans = gen_data[reservoir_key]
        for ind_idx, plan in enumerate(plans):
            gene_value = plan[seq_input][gene_idx]
            all_gen_values.append(gene_value)
            all_gen_indices.append(gen)
    
    # 绘制散点图
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.scatter(all_gen_indices, all_gen_values, c='blue', alpha=0.3, s=10)
    
    # 计算每代的平均值并绘制折线
    gen_means = []
    for gen in generations:
        gen_data = history_data['generations'][str(gen)]
        plans = gen_data[reservoir_key]
        values = [plan[seq_input][gene_idx] for plan in plans]
        gen_means.append(np.mean(values))
    
    ax.plot(generations, gen_means, color='red', linewidth=2, marker='o', markersize=4, label='Mean')
    
    ax.set_xlabel('Generation')
    ax.set_ylabel(f'{reservoir_name} {seq_input}[{gene_idx}] Value')
    ax.set_title(f'{reservoir_name} {seq_input}[{gene_idx}] Gene Evolution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show(block=True)
    
    print(f"\n{reservoir_name} {seq_input}[{gene_idx}] 基因演化统计：")
    print(f"  第一代平均值: {gen_means[0]:.6f}")
    print(f"  最后一代平均值: {gen_means[-1]:.6f}")
    print(f"  变化量: {gen_means[-1] - gen_means[0]:+.6f}")

def print_statistics(obj_by_gen, generations, history_data):
    """
    打印统计信息

    Parameters:
    obj_by_gen: 按代数组织的numpy数组
    generations: 代数列表
    """
    print("\n" + "="*60)
    print("优化过程统计信息")
    print("="*60)

    obj_means = calculate_objective_means(obj_by_gen)

    print("第一代统计：")
    first_gen_data = obj_by_gen[0]
    for i in range(3):
        print(f"目标函数{i+1}: 均值={np.mean(first_gen_data[:, i]):.6f}, "
              f"最小值={np.min(first_gen_data[:, i]):.6f}, "
              f"最大值={np.max(first_gen_data[:, i]):.6f}")

    print(f"\n最后一代（第{generations[-1]}代）统计：")
    last_gen_data = obj_by_gen[-1]
    for i in range(3):
        print(f"目标函数{i+1}: 均值={np.mean(last_gen_data[:, i]):.6f}, "
              f"最小值={np.min(last_gen_data[:, i]):.6f}, "
              f"最大值={np.max(last_gen_data[:, i]):.6f}")

    # 查找所有代数中各目标函数最小的个体
    print("\n" + "-"*60)
    print("各目标函数全局最优个体：")
    print("-"*60)
    
    # 初始化最小值记录
    min_obj1 = {'value': np.inf, 'gen': None, 'idx': None, 'objectives': None}
    min_obj2 = {'value': np.inf, 'gen': None, 'idx': None, 'objectives': None}
    min_obj3 = {'value': np.inf, 'gen': None, 'idx': None, 'objectives': None}
    
    # 遍历所有代数和个体
    for gen_idx, gen in enumerate(generations):
        gen_data = obj_by_gen[gen_idx]
        for ind_idx in range(gen_data.shape[0]):
            objectives = gen_data[ind_idx]
            
            # 检查是否包含NaN值，跳过无效个体
            if np.any(np.isnan(objectives)):
                continue
            
            # 检查目标函数1
            if objectives[0] < min_obj1['value']:
                min_obj1['value'] = objectives[0]
                min_obj1['gen'] = gen
                min_obj1['idx'] = ind_idx
                min_obj1['objectives'] = objectives.copy()
            
            # 检查目标函数2
            if objectives[1] < min_obj2['value']:
                min_obj2['value'] = objectives[1]
                min_obj2['gen'] = gen
                min_obj2['idx'] = ind_idx
                min_obj2['objectives'] = objectives.copy()
            
            # 检查目标函数3
            if objectives[2] < min_obj3['value']:
                min_obj3['value'] = objectives[2]
                min_obj3['gen'] = gen
                min_obj3['idx'] = ind_idx
                min_obj3['objectives'] = objectives.copy()
    
    # 打印目标函数1最小的个体
    if min_obj1['gen'] is not None:
        print(f"\n目标函数1最小的个体：")
        print(f"  代数: {min_obj1['gen']}, 种群内编号: {min_obj1['idx']}")
        print(f"  目标函数值: [{min_obj1['objectives'][0]:.6f}, {min_obj1['objectives'][1]:.6f}, {min_obj1['objectives'][2]:.6f}]")
    
    # 打印目标函数2最小的个体
    if min_obj2['gen'] is not None:
        print(f"\n目标函数2最小的个体：")
        print(f"  代数: {min_obj2['gen']}, 种群内编号: {min_obj2['idx']}")
        print(f"  目标函数值: [{min_obj2['objectives'][0]:.6f}, {min_obj2['objectives'][1]:.6f}, {min_obj2['objectives'][2]:.6f}]")
    
    # 打印目标函数3最小的个体
    if min_obj3['gen'] is not None:
        print(f"\n目标函数3最小的个体：")
        print(f"  代数: {min_obj3['gen']}, 种群内编号: {min_obj3['idx']}")
        print(f"  目标函数值: [{min_obj3['objectives'][0]:.6f}, {min_obj3['objectives'][1]:.6f}, {min_obj3['objectives'][2]:.6f}]")

    print("\n优化趋势分析：")
    for i in range(3):
        improvement = obj_means[-1, i] - obj_means[0, i]
        trend = "改善" if abs(improvement) > 1e-6 else "基本稳定"
        print(f"目标函数{i+1}: {improvement:+.6f} ({trend})")

    print("\n帕累托分层变化：")
    prev_layers = None
    changes = []
    for gen in generations:
        ranks = history_data['generations'][str(gen)].get('pareto_ranks', [])
        layer_count = len(set(ranks)) if ranks else 0
        if prev_layers is None:
            prev_layers = layer_count
            continue
        if layer_count != prev_layers:
            changes.append((gen, layer_count))
            prev_layers = layer_count
    if changes:
        for gen, count in changes:
            print(f"第{gen}代：分层数量 = {count}")
    else:
        print("各代帕累托分层数量保持不变。")

def main():
    """
    主函数
    """
    # 读取数据
    history_data, generations, target_path = load_pop_history()

    if history_data is None:
        return

    # 提取目标函数数据
    obj_by_gen = extract_objectives_by_generation(history_data, generations)

    # 提取约束违反值数据
    con_by_gen = extract_constraints_by_generation(history_data, generations)

    # 打印统计信息
    print_statistics(obj_by_gen, generations, history_data)

    # 创建可视化图表
    fig = create_comparison_plots(obj_by_gen, con_by_gen, generations)

    print("\nTips for the comparison plot:")
    print(" - Click an axis title/label to edit it.")
    print(" - Drag legends with the mouse to reposition them.")

    # 显示图表
    plt.show(block=True)

    # 创建3D可视化图表
    fig_3d = create_3d_plot(obj_by_gen, generations)
    plt.show(block=True)

    create_3d_layers(obj_by_gen, generations, history_data)

    export_typical_plans(history_data, generations, target_path)

    # 绘制基因演化过程
    plot_gene_evolution(history_data, generations)

    print("\n可视化完成！")
    print("图表说明：")
    print("1. 左上：第一代和最后一代的第1、2目标函数值对比")
    print("2. 右上：第一代和最后一代的第1、3目标函数值对比")
    print("3. 中左：第一代和最后一代的第2、3目标函数值对比")
    print("4. 中右：三个目标函数值随代数变化的平均值趋势")
    print("5. 左下：三个约束违反值随代数变化的平均值趋势")
    print("6. 新窗口：第1代和最后一代的3D目标函数分布（散点 + 凸包表面）")
    print("7. 新窗口：指定代数帕累托分层连线图（可选）")
    print("8. 新窗口：基因演化过程图（可选）")

if __name__ == "__main__":
    main()