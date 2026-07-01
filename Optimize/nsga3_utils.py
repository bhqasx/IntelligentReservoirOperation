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

def generate_reference_points(n_obj=3, n_divisions=4):
    """
    生成NSGA-III的结构化参考点
    
    Parameters:
    n_obj: 目标函数数量（默认3个目标）
    n_divisions: 分割数（默认4，可根据需要调整）
    
    Returns:
    reference_points: 参考点矩阵
    """
    def generator(r_points, M, Q, T, D):
        """递归生成参考点"""
        points = []
        if (D == M - 1):
            r_points[D] = Q / T
            points.append(r_points.copy())
        elif (D != M - 1):
            for i in range(Q + 1):
                r_points[D] = i / T
                points.extend(generator(r_points.copy(), M, Q - i, T, D + 1))
        return points
    
    # 使用递归生成器生成参考点
    reference_points = np.array(generator(np.zeros(n_obj), n_obj, n_divisions, n_divisions, 0))
    
    return reference_points

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

def crossover(parent_1, parent_2, mu, max_time, max_flow, reservoir_id):
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
    
    if reservoir_id == 1:
        #对三门峡交叉
        gene_idx_change=[2, 4]
        gene_idx_copy=[3, 5]
    else:
        #对小浪底交叉
        gene_idx_change=[0, 2, 4, 5, 7, 9]
        gene_idx_copy=[1, 3, 6, 8, 10]

    # 对流量序列进行交叉
    for j in range(len(parent_1['q'])):
        if (
            parent_1['q'][j] is not None
            and parent_2['q'][j] is not None
            and parent_1['q'][j] != 0
        ):
            if j in gene_idx_change:
                # 只对指定位置进行交叉
                # 设置流量的合理边界
                min_flow = 100
                
                offspring['q'][j] = crossover_variable(
                    parent_1['q'][j], parent_2['q'][j], mu, min_flow, max_flow
                )
            elif j in gene_idx_copy:
                # 将j+1位置的基因设为j位置的基因值
                if j < len(offspring['q']):
                    offspring['q'][j] = offspring['q'][j-1]
    
    return offspring

# 多项式变异：对单个变量在 [x_min, x_max] 上进行多项式变异
def polynomial_mutation_variable(x, eta, x_min, x_max, mutation_rate):
    if x is None:
        return x
    if random.random() >= mutation_rate:
        return x
    if x_max <= x_min:
        raise ValueError(f"变量边界设置错误: x_max ({x_max}) <= x_min ({x_min})，请检查边界参数设置")
    x = max(x_min, min(x_max, x))
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
def mutate_plan(offspring, mutation_rate, eta, max_time, max_flow, reservoir_id):
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

    if reservoir_id == 1:
        # 对三门峡变异
        gene_idx_change = [2, 4]
        gene_idx_copy = [3, 5]
    else:
        # 对小浪底变异
        gene_idx_change = [0, 2, 4, 5, 7, 9]
        gene_idx_copy = [1, 3, 6, 8, 10]

    # 变异流量（仅当当前值不为 None 且不为 0）
    if 'q' in offspring and offspring['q'] is not None:
        for j in range(len(offspring['q'])):
            if offspring['q'][j] is not None and offspring['q'][j] != 0:
                if j in gene_idx_change:
                    # 只对指定位置进行变异
                    offspring['q'][j] = polynomial_mutation_variable(
                        offspring['q'][j], eta, 100, max_flow, mutation_rate
                    )
                elif j in gene_idx_copy:
                    # 将j+1位置的基因设为j位置的基因值
                    if j < len(offspring['q']):
                        offspring['q'][j] = offspring['q'][j-1]
    return offspring

def generate_offspring(P_plans_SMX, P_plans_XLD, CV, nsga_config):
    """
    生成子代种群
    
    Parameters:
    P_plans_SMX: 父代SMX方案
    P_plans_XLD: 父代XLD方案
    CV: 约束违反度

    Returns:
    Q_plans_SMX: 子代SMX方案
    Q_plans_XLD: 子代XLD方案
    """
    mu = nsga_config.get('mu')
    if mu in ('', None):
        raise ValueError("CaseConfig.json 缺少 Paras_nsga.mu")
    mu = float(mu)
    max_t = 2500 + 48     # 以小浪底结束时间为基准设置
    max_q_smx = 10974
    max_q_xld = 13311
    # 变异参数
    mutation_rate = nsga_config.get('mutation_rate')
    if mutation_rate in ('', None):
        raise ValueError("CaseConfig.json 缺少 Paras_nsga.mutation_rate")
    mutation_rate = float(mutation_rate)
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
        
        # 使用带约束的二元锦标赛选择 parent_1
        cv1 = np.sum(CV[i1])
        cv2 = np.sum(CV[i2])
        if cv1 < 1e-6 and cv2 < 1e-6:  # 两个都可行，随机选择
            parent_1 = random.choice([i1, i2])
        elif cv1 < cv2:
            parent_1 = i1
        elif cv2 < cv1:
            parent_1 = i2
        else:  # 约束违反度相同（且不都为0），随机选择
            parent_1 = random.choice([i1, i2])
            
        # 使用带约束的二元锦标赛选择 parent_2
        cv3 = np.sum(CV[i3])
        cv4 = np.sum(CV[i4])
        if cv3 < 1e-6 and cv4 < 1e-6:  # 两个都可行，随机选择
            parent_2 = random.choice([i3, i4])
        elif cv3 < cv4:
            parent_2 = i3
        elif cv4 < cv3:
            parent_2 = i4
        else:  # 约束违反度相同（且不都为0），随机选择
            parent_2 = random.choice([i3, i4])

        # 交叉操作
        Q_plans_SMX[i] = crossover(P_plans_SMX[parent_1], P_plans_SMX[parent_2], mu, max_t, max_q_smx, 1)
        Q_plans_XLD[i] = crossover(P_plans_XLD[parent_1], P_plans_XLD[parent_2], mu, max_t, max_q_xld, 2)
        # 变异操作
        Q_plans_SMX[i] = mutate_plan(Q_plans_SMX[i], mutation_rate, eta_m, max_t, max_q_smx, 1)
        Q_plans_XLD[i] = mutate_plan(Q_plans_XLD[i], mutation_rate, eta_m, max_t, max_q_xld, 2)

    return Q_plans_SMX, Q_plans_XLD

def niching_selection(obj_normalized, last_front, s_indices, reference_points, remaining_slots):
    """
    执行NSGA-III的小生境选择过程。
    
    Parameters:
    obj_normalized: S和Fl中所有个体的标准化目标函数值
    last_front: 最后一个前沿的个体索引列表 (相对于R)
    s_indices: 已选入下一代的个体索引列表 (相对于R)
    reference_points: 参考点矩阵
    remaining_slots: 需要从最后一个前沿选择的个体数量

    Returns:
    selected_from_last_front: 从最后一个前沿中选出的个体索引列表
    """
    pop_size = len(s_indices) + len(last_front)
    n_obj = obj_normalized.shape[1]
    n_ref_points = len(reference_points)

    # 1. 关联操作 (Association)
    # --------------------------
    
    # 初始化每个参考点的关联列表和niche count
    associations = {i: [] for i in range(n_ref_points)}
    niche_counts = np.zeros(n_ref_points, dtype=int)
    
    # 将 obj_normalized 分为已选部分(S)和最后前沿部分(Fl)
    # s_indices 和 last_front 是 R 中的索引，而 obj_normalized 是按 s_indices + last_front 的顺序排列的
    s_obj_normalized = obj_normalized[:len(s_indices)]
    last_front_obj_normalized = obj_normalized[len(s_indices):]

    # a. 对已选种群 S 进行关联，并计算初始niche_counts
    if len(s_indices) > 0:
        # 计算每个解到所有参考点的垂直距离
        dist_matrix = np.full((len(s_indices), n_ref_points), np.inf)
        for i in range(len(s_indices)):
            for j in range(n_ref_points):
                # 计算点到线的垂直距离
                w = reference_points[j]
                norm_w_sq = np.dot(w, w)
                proj = np.dot(s_obj_normalized[i], w) / norm_w_sq
                dist = np.linalg.norm(s_obj_normalized[i] - proj * w)
                dist_matrix[i, j] = dist
        
        # 找到每个解最近的参考点
        closest_ref_indices = np.argmin(dist_matrix, axis=1)
        
        # 更新niche_counts
        for ref_idx in closest_ref_indices:
            niche_counts[ref_idx] += 1

    # b. 对最后前沿 Fl 进行关联
    if len(last_front) > 0:
        # 计算每个解到所有参考点的垂直距离
        dist_matrix_fl = np.full((len(last_front), n_ref_points), np.inf)
        for i in range(len(last_front)):
            for j in range(n_ref_points):
                w = reference_points[j]
                norm_w_sq = np.dot(w, w)
                proj = np.dot(last_front_obj_normalized[i], w) / norm_w_sq
                dist = np.linalg.norm(last_front_obj_normalized[i] - proj * w)
                dist_matrix_fl[i, j] = dist
        
        # 找到每个解最近的参考点
        closest_ref_indices_fl = np.argmin(dist_matrix_fl, axis=1)
        
        # 将Fl中的解加入对应参考点的关联列表
        for i, ref_idx in enumerate(closest_ref_indices_fl):
            original_index = last_front[i]  # 获取在R中的原始索引
            distance = dist_matrix_fl[i, ref_idx]
            associations[ref_idx].append({'index': original_index, 'dist': distance})

    # 2. Niche Count 和选择
    # --------------------------------
    selected_from_last_front = []
    
    # 找出Fl中实际关联到参考点的个体
    available_in_fl = set()
    for associated_list in associations.values():
        for item in associated_list:
            available_in_fl.add(item['index'])

    # 循环选择，直到填满剩余名额
    while len(selected_from_last_front) < remaining_slots:
        # 找出Fl中还有候选解的参考点
        active_ref_points = [
            j for j, associated_list in associations.items() if associated_list
        ]
        
        if not active_ref_points:
            # 如果Fl中没有更多可选择的解，但名额未满（不太可能发生，除非Fl为空）
            # 从所有未被选中的Fl解中随机选择
            remaining_to_select = remaining_slots - len(selected_from_last_front)
            if remaining_to_select > 0:
                pool = list(available_in_fl)
                selected_from_last_front.extend(random.sample(pool, min(len(pool), remaining_to_select)))
            break

        # 找到niche count最小的参考点
        min_niche_count = np.min(niche_counts[active_ref_points])
        potential_ref_indices = [
            j for j in active_ref_points if niche_counts[j] == min_niche_count
        ]
        
        # 从中随机选择一个参考点
        chosen_ref_idx = random.choice(potential_ref_indices)
        
        associated_solutions = associations[chosen_ref_idx]
        
        # 根据niche count选择策略
        if niche_counts[chosen_ref_idx] == 0:
            # 选择距离最近的解
            best_sol = min(associated_solutions, key=lambda x: x['dist'])
        else:
            # 随机选择一个解
            best_sol = random.choice(associated_solutions)
            
        # 添加到选择列表
        selected_from_last_front.append(best_sol['index'])
        
        # 从所有关联列表中移除已选中的解
        available_in_fl.remove(best_sol['index'])
        for ref_idx in associations:
            associations[ref_idx] = [
                s for s in associations[ref_idx] if s['index'] != best_sol['index']
            ]
            
        # 更新niche count
        niche_counts[chosen_ref_idx] += 1
 
    return selected_from_last_front

def dominates_with_constraints(obj1, cv1, obj2, cv2):
    """
    判断解1是否支配解2（考虑约束）
    
    Parameters:
    obj1, obj2: 目标函数值数组
    cv1, cv2: 约束违反度数组
    
    Returns:
    bool: 解1是否支配解2
    """
    # 计算总约束违反度
    total_cv1 = np.sum(cv1)
    total_cv2 = np.sum(cv2)
    
    # 情况1：两个解都可行
    if total_cv1 <= 1e-10 and total_cv2 <= 1e-10:
        # 使用目标函数进行支配比较
        better = np.all(obj1 <= obj2)
        strictly_better = np.any(obj1 < obj2)
        return better and strictly_better
    
    # 情况2：一个可行一个不可行
    elif total_cv1 <= 1e-10 and total_cv2 > 1e-10:
        return True  # 可行解支配不可行解
    elif total_cv1 > 1e-10 and total_cv2 <= 1e-10:
        return False  # 不可行解不支配可行解
    
    # 情况3：两个解都不可行
    else:
        # 约束违反度小的支配约束违反度大的
        return total_cv1 < total_cv2

def constrained_non_dominated_sorting(obj, constraint_violation):
    """
    有约束的非支配排序
    
    Parameters:
    obj: 目标函数值矩阵 (n_solutions x n_objectives)
    constraint_violation: 约束违反度矩阵 (n_solutions x n_constraints)
    
    Returns:
    fronts: 前沿列表，每个前沿包含解的索引
    ranks: 每个解的等级
    """
    n_solutions = obj.shape[0]
    
    # 初始化
    dominated_solutions = [[] for _ in range(n_solutions)]  # 每个解支配的解集合
    domination_count = np.zeros(n_solutions)  # 每个解被支配的次数
    ranks = np.zeros(n_solutions, dtype=int)
    
    # 计算支配关系
    for i in range(n_solutions):
        for j in range(n_solutions):
            if i != j:
                if dominates_with_constraints(obj[i], constraint_violation[i], 
                                            obj[j], constraint_violation[j]):
                    dominated_solutions[i].append(j)
                elif dominates_with_constraints(obj[j], constraint_violation[j], 
                                              obj[i], constraint_violation[i]):
                    domination_count[i] += 1
    
    # 找到第一前沿（未被任何解支配的解）
    fronts = []
    current_front = []
    for i in range(n_solutions):
        if domination_count[i] == 0:
            current_front.append(i)
            ranks[i] = 0
    
    fronts.append(current_front)
    
    # 构建后续前沿
    front_index = 0
    while front_index < len(fronts) and len(fronts[front_index]) > 0:
        next_front = []
        for i in fronts[front_index]:
            for j in dominated_solutions[i]:
                domination_count[j] -= 1
                if domination_count[j] == 0:
                    next_front.append(j)
                    ranks[j] = front_index + 1
        
        if len(next_front) > 0:
            fronts.append(next_front)
        front_index += 1
    
    return fronts, ranks