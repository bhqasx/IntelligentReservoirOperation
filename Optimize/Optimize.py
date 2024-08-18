import subprocess

# 指定exe文件的路径
exe_path = r'E:\MyGithubProj\MyModel_openmp\1D_RiverNet_OCTC\Debug\1D_RiverNet_OCTC.exe'  # 替换为你的exe文件路径

# 启动exe文件
try:
    result = subprocess.run([exe_path], check=True)
    print("程序成功执行。")
except subprocess.CalledProcessError as e:
    print(f"程序执行失败，错误代码：{e.returncode}")
except FileNotFoundError:
    print("找不到指定的exe文件，请检查路径。")