#!/usr/bin/env python3
"""
测试PopHistory分析脚本
"""

import json
import numpy as np
import os

def create_test_pop_history():
    """创建一个测试用的PopHistory.json文件"""
    # 模拟15个个体，3个目标函数，10代数据
    n_individuals = 15
    n_objectives = 3
    n_generations = 10

    history_data = {'generations': {}}

    for gen in range(1, n_generations + 1):
        # 生成随机目标函数值
        obj_values = []
        for i in range(n_individuals):
            # 第一代数据范围较大，最后几代数据更集中（模拟优化效果）
            if gen == 1:
                obj = [
                    np.random.uniform(-100, 100),  # 目标1
                    np.random.uniform(-50, 50),    # 目标2
                    np.random.uniform(0, 200)      # 目标3
                ]
            else:
                # 随着代数增加，目标函数值逐渐改善
                improvement_factor = 1.0 / gen
                obj = [
                    np.random.uniform(-50 * improvement_factor, 50 * improvement_factor),
                    np.random.uniform(-25 * improvement_factor, 25 * improvement_factor),
                    np.random.uniform(0, 100 * improvement_factor)
                ]
            obj_values.append(obj)

        generation_data = {
            'P_plans_SMX': [{'t': [1, 2, 3], 'q': [10, 20, 30]} for _ in range(n_individuals)],
            'P_plans_XLD': [{'t': [1, 2, 3], 'q': [15, 25, 35]} for _ in range(n_individuals)],
            'obj': obj_values,
            'ConstraintViolation': [[0.1, 0.2, 0.0] for _ in range(n_individuals)]
        }

        history_data['generations'][str(gen)] = generation_data

    # 保存测试文件
    with open('PopHistory_test.json', 'w') as f:
        json.dump(history_data, f, indent=2)

    print("测试文件 PopHistory_test.json 已创建")
    print(f"包含 {n_generations} 代数据，每代 {n_individuals} 个个体，每个个体 {n_objectives} 个目标函数")

if __name__ == "__main__":
    create_test_pop_history()