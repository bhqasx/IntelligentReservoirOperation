import numpy as np
import random
import copy
import os

def calculate_asf(F, weight, ideal_point):
    """计算Achievement Scalarizing Function (ASF)"""
    return np.max((F - ideal_point) / weight)

def find_extreme_points(obj, ideal_point):
    """找到极值点用于构造超平面"""
    n_obj = obj.shape[1]
    extreme_points = np.zeros((n_obj, n_obj))
    
    for i in range(n_obj):
        # 创建权重向量，第i个目标权重很小，其他很大
        weight = np.full(n_obj, 1e-6)
        weight[i] = 1.0
        
        # 找到ASF最小的解
        asf_values = np.array([calculate_asf(obj[j], weight, ideal_point) for j in range(len(obj))])
        min_idx = np.argmin(asf_values)
        extreme_points[i] = obj[min_idx]
    
    return extreme_points

def calculate_intercepts(extreme_points, ideal_point, nadir_point):
    """计算超平面截距"""
    try:
        # 构造线性方程组 A * intercepts = 1
        # 其中A是(extreme_points - ideal_point)
        A = extreme_points - ideal_point
        b = np.ones(len(extreme_points))
        
        # 求解线性方程组，得到截距的倒数
        intercept_reciprocals = np.linalg.solve(A, b)
        
        # 计算真正的截距
        intercepts = 1.0 / intercept_reciprocals
        
        # 如果截距为负或接近0，使用nadir点
        for i in range(len(intercepts)):
            if intercepts[i] <= 1e-6:
                intercepts[i] = nadir_point[i] - ideal_point[i]
                
        return intercepts
    except np.linalg.LinAlgError:
        # 如果矩阵奇异，使用nadir点作为截距
        return nadir_point - ideal_point

def normalize_objectives(obj, ideal_point, nadir_point, verbose=True):
    """
    NSGA-III标准化过程
    
    Parameters:
    obj: 目标函数值矩阵 (n_solutions x n_objectives)
    ideal_point: 理想点
    nadir_point: nadir点
    verbose: 是否打印详细信息
    
    Returns:
    obj_normalized: 标准化后的目标函数值
    extreme_points: 极值点
    intercepts: 截距
    """
    
    # 计算极值点
    extreme_points = find_extreme_points(obj, ideal_point)
    if verbose:
        print("极值点:")
        print(extreme_points)
    
    # 计算截距
    intercepts = calculate_intercepts(extreme_points, ideal_point, nadir_point)
    if verbose:
        print("超平面截距:", intercepts)
    
    # 进行标准化
    obj_normalized = (obj - ideal_point) / intercepts
    
    if verbose:
        print("标准化后的目标函数值:")
        print(obj_normalized)
        print("标准化后目标函数的范围:")
        for i in range(obj.shape[1]):
            print(f"目标{i+1}: [{np.min(obj_normalized[:, i]):.6f}, {np.max(obj_normalized[:, i]):.6f}]")
    
    return obj_normalized, extreme_points, intercepts

def generate_reference_directions(n_obj, n_divisions):
    """
    生成参考方向（简化版本，适用于3目标）
    
    Parameters:
    n_obj: 目标函数数量
    n_divisions: 分割数
    
    Returns:
    reference_directions: 参考方向矩阵
    """
    if n_obj == 3:
        # 对于3目标问题，生成单纯形上的均匀分布点
        ref_dirs = []
        for i in range(n_divisions + 1):
            for j in range(n_divisions + 1 - i):
                k = n_divisions - i - j
                ref_dir = np.array([i, j, k]) / n_divisions
                ref_dirs.append(ref_dir)
        return np.array(ref_dirs)
    else:
        # 简化版本：为其他目标数量生成随机参考方向
        n_ref = (n_divisions + n_obj - 1) // n_obj * 10  # 估算参考方向数量
        ref_dirs = np.random.random((n_ref, n_obj))
        # 标准化到单位单纯形
        ref_dirs = ref_dirs / np.sum(ref_dirs, axis=1, keepdims=True)
        return ref_dirs

def associate_to_reference_directions(obj_normalized, reference_directions):
    """
    将解关联到参考方向
    
    Parameters:
    obj_normalized: 标准化后的目标函数值
    reference_directions: 参考方向
    
    Returns:
    distances: 每个解到其最近参考方向的距离
    associations: 每个解关联的参考方向索引
    """
    n_solutions = obj_normalized.shape[0]
    n_ref = reference_directions.shape[0]
    
    distances = np.zeros(n_solutions)
    associations = np.zeros(n_solutions, dtype=int)
    
    for i in range(n_solutions):
        min_distance = float('inf')
        best_ref = 0
        
        for j in range(n_ref):
            # 计算点到参考方向的垂直距离
            ref_dir = reference_directions[j]
            point = obj_normalized[i]
            
            # 投影长度
            projection_length = np.dot(point, ref_dir) / np.linalg.norm(ref_dir)
            
            # 投影点
            projection = projection_length * ref_dir / np.linalg.norm(ref_dir)
            
            # 垂直距离
            distance = np.linalg.norm(point - projection)
            
            if distance < min_distance:
                min_distance = distance
                best_ref = j
        
        distances[i] = min_distance
        associations[i] = best_ref
    
    return distances, associations

def crossover_variable(x1, x2, mu, x_min, x_max):
    """
    对单个变量进行SBX交叉操作
    
    Parameters:
    x1, x2: 父代变量值
    mu: 分布指数（分布参数）
    x_min, x_max: 变量的最小和最大边界
    
    Returns:
    offspring: 交叉后的子代变量值
    """
    # 如果两个父代值相等，直接返回
    if abs(x1 - x2) < 1e-14:
        return x1
    
    # 确保y1 <= y2
    y1 = min(x1, x2)
    y2 = max(x1, x2)
    
    # 计算beta的边界值（对下界进行截断，避免负值）
    dl = max(0.0, (y1 - x_min) / (y2 - y1))
    du = max(0.0, (x_max - y2) / (y2 - y1))
    beta_1 = 1.0 + 2.0 * dl
    beta_2 = 1.0 + 2.0 * du

    # 使用 Deb 原始形式，保证 2 - u*alpha > 0
    alpha_1 = 2.0 - beta_1 ** (-(mu + 1.0))
    alpha_2 = 2.0 - beta_2 ** (-(mu + 1.0))

    # 选择边界一侧并计算 beta_q（稳定且无负数幂风险）
    if random.random() <= 0.5:
        u = random.random()
        if u <= (1.0 / alpha_1):
            beta_q = (u * alpha_1) ** (1.0 / (mu + 1.0))
        else:
            beta_q = (1.0 / (2.0 - u * alpha_1)) ** (1.0 / (mu + 1.0))
    else:
        u = random.random()
        if u <= (1.0 / alpha_2):
            beta_q = (u * alpha_2) ** (1.0 / (mu + 1.0))
        else:
            beta_q = (1.0 / (2.0 - u * alpha_2)) ** (1.0 / (mu + 1.0))

    # 随机选择生成两个子代中的一个
    if random.random() <= 0.5:
        offspring = 0.5 * ((1 + beta_q) * y1 + (1 - beta_q) * y2)
    else:
        offspring = 0.5 * ((1 - beta_q) * y1 + (1 + beta_q) * y2)

    # 确保在边界范围内
    offspring = max(x_min, min(x_max, offspring))
    return offspring

def crossover(parent_1, parent_2, mu, max_time, max_flow):
    """
    对水库调度方案进行SBX交叉
    
    Parameters:
    parent_1, parent_2: 父代方案字典，包含't'和'q'数组
    mu: 分布指数
    
    Returns:
    offspring: 子代方案字典
    """
    offspring = copy.deepcopy(parent_1)
    
    # 对时间序列进行交叉（除了固定的时间点）
    for j in range(1, len(parent_1['t']) - 1):  # 避免交叉第一个和最后一个时间点
        if parent_1['t'][j] is not None and parent_2['t'][j] is not None:
            # 将下界设为offspring中前一个时间，确保非递减
            prev_t = offspring['t'][j-1]
            min_time = 0 if prev_t is None else prev_t
            
            offspring['t'][j] = crossover_variable(
                parent_1['t'][j], parent_2['t'][j], mu, min_time, max_time
            )
    
    # 对流量序列进行交叉
    for j in range(len(parent_1['q'])):
        if (
            parent_1['q'][j] is not None
            and parent_2['q'][j] is not None
            and parent_1['q'][j] != 0
        ):
            # 设置流量的合理边界
            min_flow = 0
            
            offspring['q'][j] = crossover_variable(
                parent_1['q'][j], parent_2['q'][j], mu, min_flow, max_flow
            )
    
    return offspring

# 多项式变异：对单个变量在 [x_min, x_max] 上进行多项式变异
def polynomial_mutation_variable(x, eta, x_min, x_max, mutation_rate):
    if x is None:
        return x
    if random.random() >= mutation_rate:
        return x
    if x_max <= x_min:
        raise ValueError(f"变量边界设置错误: x_max ({x_max}) <= x_min ({x_min})，请检查边界参数设置")
    # 归一化到 [0,1] 的距离
    delta1 = (x - x_min) / (x_max - x_min)
    delta2 = (x_max - x) / (x_max - x_min)
    u = random.random()
    mut_pow = 1.0 / (eta + 1.0)
    if u < 0.5:
        xy = 1.0 - delta1
        val = 2.0 * u + (1.0 - 2.0 * u) * (xy ** (eta + 1.0))
        delta_q = val ** mut_pow - 1.0
    else:
        xy = 1.0 - delta2
        val = 2.0 * (1.0 - u) + 2.0 * (u - 0.5) * (xy ** (eta + 1.0))
        delta_q = 1.0 - val ** mut_pow
    x_new = x + delta_q * (x_max - x_min)
    return max(x_min, min(x_max, x_new))

# 对方案进行变异：时间与流量分别按边界约束变异
def mutate_plan(offspring, mutation_rate, eta, max_time, max_flow):
    # 变异时间（保持非递减，首尾不变）
    if 't' in offspring and offspring['t'] is not None:
        for j in range(1, len(offspring['t']) - 1):
            if offspring['t'][j] is not None:
                prev_t = offspring['t'][j - 1]
                min_time = 0 if prev_t is None else prev_t
                offspring['t'][j] = polynomial_mutation_variable(
                    offspring['t'][j], eta, min_time, max_time, mutation_rate
                )
                # 再次保证非递减
                if prev_t is not None and offspring['t'][j] < prev_t:
                    offspring['t'][j] = prev_t
    # 变异流量（仅当当前值不为 None 且不为 0）
    if 'q' in offspring and offspring['q'] is not None:
        for j in range(len(offspring['q'])):
            if offspring['q'][j] is not None and offspring['q'][j] != 0:
                offspring['q'][j] = polynomial_mutation_variable(
                    offspring['q'][j], eta, 0.0, max_flow, mutation_rate
                )
    return offspring

def generate_offspring(P_plans_SMX, P_plans_XLD):
    """
    生成子代种群
    
    Parameters:
    P_plans_SMX: 父代SMX方案
    P_plans_XLD: 父代XLD方案  
    obj: 目标函数值矩阵
    
    Returns:
    Q_plans_SMX: 子代SMX方案
    Q_plans_XLD: 子代XLD方案
    """
    mu = 10    #越小探索性越强，一般默认10-20
    max_t = 2500 + 48     # 以小浪底结束时间为基准设置
    max_q_smx = 10974
    max_q_xld = 13311
    # 变异参数
    mutation_rate = 0.1
    eta_m = 20 #越大变异越小，常见默认20
    pop_size = len(P_plans_SMX)

    # 复制父代作为子代的初始值
    Q_plans_SMX = copy.deepcopy(P_plans_SMX)
    Q_plans_XLD = copy.deepcopy(P_plans_XLD)
    
    # 为每个子代个体选择父代并进行交叉
    for i in range(pop_size):
        # 随机选择4个不同的个体索引（类似breeding函数）
        available_indices = list(range(pop_size))
        
        if len(available_indices) >= 4:
            i1, i2, i3, i4 = random.sample(available_indices, 4)
        else:
            # 如果种群太小，允许重复选择
            i1, i2, i3, i4 = random.choices(available_indices, k=4)
        
        # 选择parent_1（参照breeding函数的选择机制）
        rand = int.from_bytes(os.urandom(8), byteorder='big') / ((1 << 64) - 1)
        if rand > 0.5:
            parent_1 = i1
        else:
            parent_1 = i2
            
        # 选择parent_2
        rand = int.from_bytes(os.urandom(8), byteorder='big') / ((1 << 64) - 1)
        if rand > 0.5:
            parent_2 = i3
        else:
            parent_2 = i4

        # 交叉操作
        Q_plans_SMX[i] = crossover(P_plans_SMX[parent_1], P_plans_SMX[parent_2], mu, max_t, max_q_smx)
        Q_plans_XLD[i] = crossover(P_plans_XLD[parent_1], P_plans_XLD[parent_2], mu, max_t, max_q_xld)
        # 变异操作
        Q_plans_SMX[i] = mutate_plan(Q_plans_SMX[i], mutation_rate, eta_m, max_t, max_q_smx)
        Q_plans_XLD[i] = mutate_plan(Q_plans_XLD[i], mutation_rate, eta_m, max_t, max_q_xld)

    return Q_plans_SMX, Q_plans_XLD