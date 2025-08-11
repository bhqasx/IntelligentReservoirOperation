# 更好用的Web版本见https://gemini.google.com/app/967b10a64c9c9383
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import json

def select_json_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title='选择JSON文件',
        filetypes=[
            ('JSON文件', '*.json'),
            ('所有文件', '*.*')
        ]
    )
    if file_path:
        print(f'选择的文件路径: {file_path}')
        return file_path
    else:
        print('没有选择文件')
        return None

def add_json_to_tree(tree, parent, dictionary):
    # 递归添加JSON数据到树形结构，只显示key，并在叶子节点添加单选框
    if isinstance(dictionary, dict):
        for key in dictionary.keys():
            is_leaf = not isinstance(dictionary[key], (dict, list)) or \
                     (isinstance(dictionary[key], list) and not any(isinstance(x, (dict, list)) for x in dictionary[key]))
            item = tree.insert(parent, 'end', text=key, values=('○' if is_leaf else '',))
            add_json_to_tree(tree, item, dictionary[key])
    elif isinstance(dictionary, list):
        for index, value in enumerate(dictionary):
            if isinstance(value, (dict, list)):
                item = tree.insert(parent, 'end', text=f'[{index}]')
                add_json_to_tree(tree, item, value)

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
    return None

if __name__ == '__main__':
    selected_file = select_json_file()
    with open(selected_file, 'r') as file:
        data = json.load(file)
    
    # 创建新窗口
    root = tk.Tk()
    root.title("请选择入库的t序列")
    root.geometry("400x600")
    
    # 创建并配置样式以禁用选择高亮
    style = ttk.Style()
    style.map('Treeview',
        background=[('selected', 'white')],
        foreground=[('selected', 'black')]
    )
    
    # 创建树形结构，添加checkbox列
    tree = ttk.Treeview(root, columns=('checkbox',), selectmode='none')
    tree.heading('checkbox', text='选择')
    tree.column('checkbox', width=50, anchor='center')
    tree.pack(fill='both', expand=True)
    
    # 添加滚动条
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
    scrollbar.pack(side='right', fill='y')
    tree.configure(yscrollcommand=scrollbar.set)
    
    # 保存当前选中的项和选择的值
    selected_item = None
    t_in = None
    Q_in = None
    t_out = None
    Q_out = None
    WL = None
    Vol = None
    selection_stage = 1  # 用于标记当前选择阶段：1=t_in, 2=Q_in, 3=t_out, 4=Q_out, 5=WL, 6=Vol
    
    def get_value_from_path(data, path):
        """根据路径获取JSON中的值"""
        current = data
        for key in path:
            if isinstance(current, list):
                current = current[int(key[1:-1])]  # 处理形如 "[0]" 的索引
            else:
                current = current[key]
        return current
    
    def confirm_selection():
        global selected_item, t_in, Q_in, t_out, Q_out, WL, Vol, selection_stage
        if selected_item:
            # 获取选中项的完整路径
            path = []
            current = selected_item
            while current:
                path.insert(0, tree.item(current)['text'])
                current = tree.parent(current)
            
            # 根据当前选择阶段存储值
            if selection_stage == 1:
                t_in = get_value_from_path(data, path)
                print(f"已选择入库t序列: {t_in}")
                root.title("请选择入库的Q序列")
                selection_stage = 2
                tree.item(selected_item, values=('○',))
                selected_item = None
            elif selection_stage == 2:
                Q_in = get_value_from_path(data, path)
                print(f"已选择入库Q序列: {Q_in}")
                root.title("请选择出库的t序列")
                selection_stage = 3
                tree.item(selected_item, values=('○',))
                selected_item = None
            elif selection_stage == 3:
                t_out = get_value_from_path(data, path)
                print(f"已选择出库t序列: {t_out}")
                root.title("请选择出库的Q序列")
                selection_stage = 4
                tree.item(selected_item, values=('○',))
                selected_item = None
            elif selection_stage == 4:
                Q_out = get_value_from_path(data, path)
                print(f"已选择出库Q序列: {Q_out}")
                root.title("请选择库容曲线中的水位")
                selection_stage = 5
                tree.item(selected_item, values=('○',))
                selected_item = None
            elif selection_stage == 5:
                WL = get_value_from_path(data, path)
                print(f"已选择水位序列: {WL}")
                root.title("请选择库容曲线中的库容")
                selection_stage = 6
                tree.item(selected_item, values=('○',))
                selected_item = None
            else:  # selection_stage == 6
                Vol = get_value_from_path(data, path)
                print(f"已选择库容序列: {Vol}")
                
                # 对入库流量进行线性插值
                Q_in_interp = [interpolate(t, t_in, Q_in) for t in t_out]
                print("已完成线性插值计算")
                print(f"插值结果 Q_in_interp: {Q_in_interp}")

                # 在t_out,Q_in_interp序列上求出每个时刻的累计入库水量
                # 声明一个和t_out长度相同的列表，用于存储累计入库水量
                Acc_in = [0] * len(t_out)
                for i in range(1, len(t_out)):
                    Acc_in[i] = Acc_in[i-1] + (Q_in_interp[i] + Q_in_interp[i-1]) * (t_out[i] - t_out[i-1]) * 3600 / 2 / 1e8
                print(f"累计入库水量(亿m3): {Acc_in}")

                # 在t_out, Q_out序列上求出每个时刻的累计出库水量
                # 声明一个和t_out长度相同的列表，用于存储累计出库水量
                Acc_out = [0] * len(t_out)
                for i in range(1, len(t_out)):
                    Acc_out[i] = Acc_out[i-1] + (Q_out[i] + Q_out[i-1]) * (t_out[i] - t_out[i-1]) * 3600 / 2 / 1e8
                print(f"累计出库水量(亿m3): {Acc_out}")

                NetVolOut = [out - inn for out, inn in zip(Acc_out, Acc_in)]
                print(f"净出库水量(亿m3): {NetVolOut}")
                root.destroy()  # 全部选择完后关闭窗口
    
    # 添加确认按钮
    confirm_button = tk.Button(root, text="确认", command=confirm_selection)
    confirm_button.pack(pady=10)
    
    # 添加点击事件处理
    def on_click(event):
        global selected_item
        item = tree.identify('item', event.x, event.y)
        if item and tree.item(item)['values'] and tree.item(item)['values'][0]:
            # 如果之前有选中的项，将其状态改回未选中
            if selected_item:
                tree.item(selected_item, values=('○',))
            # 更新当前选中项
            tree.item(item, values=('●',))
            selected_item = item
    
    tree.bind('<Button-1>', on_click)
    
    # 递归添加JSON数据到树形结构
    add_json_to_tree(tree, '', data)
    
    root.mainloop()
