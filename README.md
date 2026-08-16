# 调试方法
资源管理器中双击运行start-server.bat，然后打开VScode/Cursor，打开文件夹，点击Run->start debugging，填写完后点击保存，将浏览器下载的SMX_keypoints.json和XLD_keypoints.json粘贴Cases下自己命名的算例文件夹中，然后在VScode/Cursor中打开Optimize文件夹，注意Optimize.py中的exe_directory是否设置为了水沙动力学模型所在文件夹，运行Optimize.py文件。

## 优化中断后的恢复

Optimize.py 现在支持从历史代断点续算，并且会在恢复前自动备份旧的 PopHistory.json、裁剪恢复代之后的历史记录、恢复保存过的随机数状态。

### CaseConfig.json 可选字段

```json
{
	"start_mode": 3,
	"resume_generation": 25
}
```

- `start_mode = 1`：生成初始方案并开始优化
- `start_mode = 2`：从 `XLD_Plan.json` 和 `SMX_Plan.json` 读取初始方案
- `start_mode = 3`：从 `PopHistory.json` 的指定代恢复

### 命令行恢复

```bash
python Optimize.py 2R20_17_TP 3 25
```

上面的参数依次表示：算例目录名、启动模式、恢复代数。
