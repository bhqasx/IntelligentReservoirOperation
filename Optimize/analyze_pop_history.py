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
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')  # 使用支持交互的后端
from mpl_toolkits.mplot3d import Axes3D
import mplcursors
from scipy.spatial import ConvexHull

def load_pop_history(filename='PopHistory.json'):
    """
    读取PopHistory.json文件

    Parameters:
    filename: 文件名

    Returns:
    history_data: 包含所有代数数据的字典
    generations: 代数列表（排序后的）
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            history_data = json.load(f)

        # 获取所有代数并排序
        generations = sorted([int(gen) for gen in history_data['generations'].keys()])

        print(f"成功读取PopHistory.json文件")
        print(f"包含 {len(generations)} 代数据：第 {generations[0]} 代到第 {generations[-1]} 代")
        print(f"每代有 {len(history_data['generations'][str(generations[0])]['obj'])} 个个体")
        print(f"每个个体有 {len(history_data['generations'][str(generations[0])]['obj'][0])} 个目标函数")

        return history_data, generations

    except FileNotFoundError:
        print(f"错误：找不到文件 {filename}")
        return None, None
    except json.JSONDecodeError as e:
        print(f"错误：JSON文件格式错误 - {e}")
        return None, None
    except Exception as e:
        print(f"错误：读取文件时发生未知错误 - {e}")
        return None, None

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

def create_comparison_plots(obj_by_gen, con_by_gen, generations):
    """
    创建五个子图的对比分析

    Parameters:
    obj_by_gen: 按代数组织的numpy数组
    con_by_gen: 按代数组织的约束违反值数组
    generations: 代数列表
    """
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    # 创建5个子图 (3x2布局)
    fig, axes = plt.subplots(3, 2, figsize=(16, 20))
    fig.suptitle('NSGA-III优化过程分析', fontsize=16, fontweight='bold')

    # 获取第一代和最后一代的数据
    first_gen_data = obj_by_gen[0]  # 第一代
    last_gen_data = obj_by_gen[-1]  # 最后一代

    # 子图1：第1、2目标函数对比
    ax1 = axes[0, 0]
    sc1_1 = ax1.scatter(first_gen_data[:, 0], first_gen_data[:, 1], c='blue', alpha=0.7, label=f'第{generations[0]}代', marker='o')
    sc1_2 = ax1.scatter(last_gen_data[:, 0], last_gen_data[:, 1], c='red', alpha=0.7, label=f'第{generations[-1]}代', marker='s')
    ax1.set_xlabel('目标函数1 (-SMX QsDiff)')
    ax1.set_ylabel('目标函数2 (-XLD QsDiff)')
    ax1.set_title('目标函数1 vs 目标函数2')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 添加鼠标悬停显示个体编号
    cursor1 = mplcursors.cursor([sc1_1, sc1_2], hover=True)
    @cursor1.connect("add")
    def on_add1(sel):
        if sel.artist == sc1_1:
            sel.annotation.set_text(f'第{generations[0]}代个体 {sel.index}')
        elif sel.artist == sc1_2:
            sel.annotation.set_text(f'第{generations[-1]}代个体 {sel.index}')
    @cursor1.connect("remove")
    def on_remove1(sel):
        sel.annotation.set_visible(False)

    # 子图2：第1、3目标函数对比
    ax2 = axes[0, 1]
    sc2_1 = ax2.scatter(first_gen_data[:, 0], first_gen_data[:, 2], c='blue', alpha=0.7, label=f'第{generations[0]}代', marker='o')
    sc2_2 = ax2.scatter(last_gen_data[:, 0], last_gen_data[:, 2], c='red', alpha=0.7, label=f'第{generations[-1]}代', marker='s')
    ax2.set_xlabel('目标函数1 (-SMX QsDiff)')
    ax2.set_ylabel('目标函数3 (Flood Obj)')
    ax2.set_title('目标函数1 vs 目标函数3')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 添加鼠标悬停显示个体编号
    cursor2 = mplcursors.cursor([sc2_1, sc2_2], hover=True)
    @cursor2.connect("add")
    def on_add2(sel):
        if sel.artist == sc2_1:
            sel.annotation.set_text(f'第{generations[0]}代个体 {sel.index}')
        elif sel.artist == sc2_2:
            sel.annotation.set_text(f'第{generations[-1]}代个体 {sel.index}')
    @cursor2.connect("remove")
    def on_remove2(sel):
        sel.annotation.set_visible(False)

    # 子图3：第2、3目标函数对比
    ax3 = axes[1, 0]
    sc3_1 = ax3.scatter(first_gen_data[:, 1], first_gen_data[:, 2], c='blue', alpha=0.7, label=f'第{generations[0]}代', marker='o')
    sc3_2 = ax3.scatter(last_gen_data[:, 1], last_gen_data[:, 2], c='red', alpha=0.7, label=f'第{generations[-1]}代', marker='s')
    ax3.set_xlabel('目标函数2 (-XLD QsDiff)')
    ax3.set_ylabel('目标函数3 (Flood Obj)')
    ax3.set_title('目标函数2 vs 目标函数3')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 添加鼠标悬停显示个体编号
    cursor3 = mplcursors.cursor([sc3_1, sc3_2], hover=True)
    @cursor3.connect("add")
    def on_add3(sel):
        if sel.artist == sc3_1:
            sel.annotation.set_text(f'第{generations[0]}代个体 {sel.index}')
        elif sel.artist == sc3_2:
            sel.annotation.set_text(f'第{generations[-1]}代个体 {sel.index}')
    @cursor3.connect("remove")
    def on_remove3(sel):
        sel.annotation.set_visible(False)

    # 子图4：目标函数平均值随代数变化趋势
    ax4 = axes[1, 1]
    obj_means = calculate_objective_means(obj_by_gen)

    # 创建右侧副纵轴
    ax4_right = ax4.twinx()

    # 绘制前两个目标函数在主轴上
    colors = ['blue', 'green']
    labels = ['目标函数1 (-SMX QsDiff)', '目标函数2 (-XLD QsDiff)']
    lines_left = []
    for i in range(2):
        line, = ax4.plot(generations, obj_means[:, i], color=colors[i], linewidth=2,
                        marker='o', markersize=4, label=labels[i])
        lines_left.append(line)

    # 绘制第三个目标函数在右侧轴上
    line_right, = ax4_right.plot(generations, obj_means[:, 2], color='red', linewidth=2,
                                marker='o', markersize=4, label='目标函数3 (Flood Obj)')

    # 设置轴标签
    ax4.set_xlabel('代数')
    ax4.set_ylabel('目标函数1和2平均值')
    ax4_right.set_ylabel('目标函数3平均值')

    ax4.set_title('目标函数平均值随代数变化')
    
    # 合并图例
    lines = lines_left + [line_right]
    labels = [l.get_label() for l in lines]
    ax4.legend(lines, labels, loc='upper left')
    
    ax4.grid(True, alpha=0.3)

    # 子图5：约束违反值随代数变化趋势
    ax5 = axes[2, 0]
    con_means = np.mean(con_by_gen, axis=1)  # 计算每一代的约束违反值平均值

    # 绘制三个约束违反值
    colors = ['purple', 'orange', 'brown']
    labels = ['约束1违反值', '约束2违反值', '约束3违反值']
    for i in range(3):
        ax5.plot(generations, con_means[:, i], color=colors[i], linewidth=2,
                marker='o', markersize=4, label=labels[i])

    # 设置轴标签
    ax5.set_xlabel('代数')
    ax5.set_ylabel('约束违反值')
    ax5.set_title('约束违反值随代数变化')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 调整子图间距
    plt.tight_layout()
    plt.subplots_adjust(top=0.92, hspace=0.3, wspace=0.2)

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
               c='blue', alpha=0.7, label=f'第{generations[0]}代')
    ax.scatter(last_gen_data[:, 0], last_gen_data[:, 1], last_gen_data[:, 2], 
               c='red', alpha=0.7, label=f'第{generations[-1]}代')

    # 计算并绘制第一代的凸包表面
    hull1 = ConvexHull(first_gen_data)
    ax.plot_trisurf(first_gen_data[:, 0], first_gen_data[:, 1], first_gen_data[:, 2], 
                    triangles=hull1.simplices, color='blue', alpha=0.3)

    # 计算并绘制最后一代的凸包表面
    hull2 = ConvexHull(last_gen_data)
    ax.plot_trisurf(last_gen_data[:, 0], last_gen_data[:, 1], last_gen_data[:, 2], 
                    triangles=hull2.simplices, color='red', alpha=0.3)

    ax.set_xlabel('目标函数1 (-SMX QsDiff)')
    ax.set_ylabel('目标函数2 (-XLD QsDiff)')
    ax.set_zlabel('目标函数3 (Flood Obj)')
    ax.set_title('第1代和最后一代3D目标函数分布')
    ax.legend()

    return fig

def print_statistics(obj_by_gen, generations):
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

    print("\n优化趋势分析：")
    for i in range(3):
        improvement = obj_means[-1, i] - obj_means[0, i]
        trend = "改善" if abs(improvement) > 1e-6 else "基本稳定"
        print(f"目标函数{i+1}: {improvement:+.6f} ({trend})")

def main():
    """
    主函数
    """
    # 读取数据
    history_data, generations = load_pop_history()

    if history_data is None:
        return

    # 提取目标函数数据
    obj_by_gen = extract_objectives_by_generation(history_data, generations)

    # 提取约束违反值数据
    con_by_gen = extract_constraints_by_generation(history_data, generations)

    # 打印统计信息
    print_statistics(obj_by_gen, generations)

    # 创建可视化图表
    fig = create_comparison_plots(obj_by_gen, con_by_gen, generations)

    # 显示图表
    plt.show(block=True)

    # 创建3D可视化图表
    fig_3d = create_3d_plot(obj_by_gen, generations)

    # 显示3D图表
    plt.show(block=True)

    print("\n可视化完成！")
    print("图表说明：")
    print("1. 左上：第一代和最后一代的第1、2目标函数值对比")
    print("2. 右上：第一代和最后一代的第1、3目标函数值对比")
    print("3. 中左：第一代和最后一代的第2、3目标函数值对比")
    print("4. 中右：三个目标函数值随代数变化的平均值趋势")
    print("5. 左下：三个约束违反值随代数变化的平均值趋势")
    print("6. 新窗口：第1代和最后一代的3D目标函数分布（散点 + 凸包表面）")

if __name__ == "__main__":
    main()