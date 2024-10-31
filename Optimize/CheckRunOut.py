import tkinter as tk
from tkinter import filedialog

def select_json_file():
    # 创建根窗口但不显示
    root = tk.Tk()
    root.withdraw()

    # 打开文件选择对话框
    file_path = filedialog.askopenfilename(
        title='选择JSON文件',
        filetypes=[
            ('JSON文件', '*.json'),
            ('所有文件', '*.*')
        ]
    )
    
    # 如果用户选择了文件，返回文件路径
    if file_path:
        print(f'选择的文件路径: {file_path}')
        return file_path
    else:
        print('没有选择文件')
        return None

if __name__ == '__main__':
    # 调用函数打开文件选择器
    selected_file = select_json_file()