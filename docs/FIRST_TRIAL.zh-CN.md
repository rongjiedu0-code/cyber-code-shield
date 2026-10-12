# 两分钟演示与第一次试用

目标：让第一次接触项目的人完成一个小任务，理解本地 AI 补丁审查流程，并指出操作中的卡点。

## 准备

下载或克隆仓库，在仓库根目录打开终端。先运行 `python --version` 确认 Python 可用；如果系统使用 `python3` 或 `py`，相应替换下方命令的 `python`。

本次演示只使用 Python 标准库，不需要 Ollama、模型下载或 API Key。`--dry-run` 展示的是提示词及上下文预览，不会生成修复建议，也不修改代码。

## 两分钟录屏顺序

| 时间 | 屏幕操作 | 讲解要点 |
| --- | --- | --- |
| 0:00–0:20 | 打开示例 `app.py` 和 `traceback.txt` | 函数收到了 `raw_username`，却使用未定义的 `username`。 |
| 0:20–0:55 | 运行下面的错误修复预览命令 | 工具读取日志，定位 `app.py:2`，选取附近代码组织上下文。 |
| 0:55–1:20 | 在输出中找到主故障位置和代码片段 | 说明提供给模型的具体范围；这是预览，没有调用模型。 |
| 1:20–1:45 | 运行 TODO 预览命令 | 显式提供 `app.py`，关注 `is_valid_username` 的 ASCII 字符约束。 |
| 1:45–2:00 | 打开仓库的 `examples/sample-report-bundle` | 这是已有示例证据包。真实生成需要配置本地模型；补丁最终由人审查应用。 |

错误修复预览，在仓库根目录运行：

```bash
python setup_local_ai.py --fix-error --project examples/demo-buggy-project --error-log examples/demo-buggy-project/traceback.txt --context-lite --dry-run
```

应看到：命令成功结束、主故障位置包含 `app.py:2`、提示词包含 `username` 的错误及对应源码。

TODO 补全预览：

```bash
python setup_local_ai.py --complete-todo --project examples/demo-todo-project --files app.py --context-lite --dry-run
```

应看到：提示词包含 `is_valid_username` 及 3–20 个小写 ASCII 字母、数字或下划线的约束。

## 给试用者的十分钟任务

找熟悉 Python 或使用过本地 AI 编程工具的人试用。初轮 2–3 人即可用于寻找明显卡点，并不代表市场验证。

1. 从 README 找到首次体验入口，完成错误修复预览。
2. 指出最可能需要修改的文件和行号。
3. 判断预览命令是否已经调用模型、生成报告或修改代码。
4. 记录一处说明不清或操作受阻的位置。

不要求试用者安装模型，也不要求泛泛评价“好不好”。收集：操作系统、Python 版本、实际命令、卡住步骤、期望结果；不要收集真实业务源码、密钥或个人账务资料。

## 验收标准

- 文档引用的示例文件实际存在。
- 两个预览命令退出码均为 0。
- 错误预览定位 `app.py:2`。
- 预览没有改变示例源码或创建补丁报告。
- 试用者能区分提示词预览、实际模型输出和样例证据包。

## 验证范围

自动测试验证了核心规则和这两个命令的预览路径。它没有验证不同本地模型的建议质量、真实企业部署或所有平台兼容性。实际模型验证应单独记录模型、硬件、输入、结果和失败案例。
