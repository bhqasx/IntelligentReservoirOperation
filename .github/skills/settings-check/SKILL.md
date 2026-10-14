---
name: settings-check
description: "检查 IntelligentReservoirOperation 算例设置。Use when the user asks to check a case configuration, CaseConfig.json, initial reservoir levels, CSINIL files, iniWL_XLD, iniWL_SMX, or exe_directory."
argument-hint: "可选：算例名称"
user-invocable: true
---

# 设置检查 Skill

用于检查 `Cases` 目录下指定算例的配置是否与数值模拟程序输入文件一致。

## Procedure

1. 若用户未提供算例名称，先询问：`您要检查哪一个算例的设置？`
2. 在工作区根目录的 `Cases/<算例名称>/` 中定位算例文件夹。若不存在，报告该路径未找到并停止检查。
3. 读取 `Cases/<算例名称>/CaseConfig.json`，获取以下字段：
   - `iniWL_XLD`
   - `iniWL_SMX`
   - `exe_directory`
4. 检查以上字段均存在且可解析；缺失或无效时，逐项报告并停止依赖该字段的检查。
5. 在 `<exe_directory>/Input/` 中读取：
   - `CSINIL  1.Dat`：取得最后一个非空行中以空白分隔的最后一个数值，作为三门峡初始水位。
   - `CSINIL  2.Dat`：取得最后一个非空行中以空白分隔的最后一个数值，作为小浪底初始水位。
6. 分别比较数值：
   - `CSINIL  1.Dat` 的末断面水位是否等于 `iniWL_SMX`。
   - `CSINIL  2.Dat` 的末断面水位是否等于 `iniWL_XLD`。
7. 向用户报告每个文件的路径、配置值、文件末断面值和匹配结果。读取失败、文件不存在或末行不是有效数值时，要明确报告原因。

## Comparison Rules

- `CaseConfig.json` 使用 UTF-8 或 UTF-8 with BOM 解码。
- 水位按浮点数比较；同时展示原始值和数值比较结果。
- 不修改算例文件、模型输入文件或运行目录。