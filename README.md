# 本地代码安全体检与电商效率工具箱

**定制脚本 / Excel 数据处理 / 本地自动化联系：[rongjiedu1@gmail.com](mailto:rongjiedu1@gmail.com)**

纯本地 Python CLI + 中文桌面 GUI，另有仅监听本机回环地址的浏览器界面。账单与源码分析无需云账号、付费 API 或远程计算服务；国内公开内容采集是可选联网功能。

## 实际验证

历史版本工程累计有过 232 项自动化验证。本次本地核心版本使用 pytest：**277 项核心与本机 HTTP 回归已通过**，覆盖十进制金额、长订单号精度、导出行数限制、双轨离线激活、源码扫描与本机上传。新增版本测试记录见本仓库 CI；不把历史测试数量当作当前测试结果。

## 直接运行

```shell
python -m pip install -r requirements-dev.txt
python local_toolbox/start.py
# 可选：仅在本机浏览器打开
python local_toolbox/start.py --web
```

支持 Python 3.11。桌面模式需要系统 Tk；源码仓库不包含 Windows 绿色运行环境。独立发货包自带运行环境，联系邮箱获取。

CLI 示例：

```shell
cd local_toolbox
python -m toolbox.cli reconcile --orders 示例表格/示例_订单表.csv --payments 示例表格/示例_流水表.csv --export 核对结果.xlsx
python -m toolbox.cli security --path 示例表格/示例代码 --export 代码体检.csv
python -m toolbox.cli trends --limit 20
```

## 四项能力

- CSV/XLSX 双表核对，提示漏收款、差额、重复订单及多笔流水，异常 Excel 行标红。有效位数不足的长订单号标记核实，不伪造尾数。
- 国内公开社区内容或本地反馈表的需求措辞排序。规则分不是已验证需求、成交概率或投资建议。
- 国内公开热榜快照，或基于导入商品报价计算同表品类价格带、估算毛利；不为热词编造价格与销量。
- 只读扫描 Python / JS / TS，Python AST + 正则、JS/TS 正则，常见密钥脱敏；不会执行被检查代码，也不保证发现所有问题。

## 试用与开源范围

默认所有计算功能开放，软件包装层未激活时导出前 10 行。离线激活解锁本机全量导出，无服务器验证。开源许可允许审阅和修改代码；这是一项轻量商业交付限制，不是不可绕过的 DRM。收费内容与定制范围应在交易前明确。

仓库不含卖家算号器界面或收款自动化。固定测试码仅用于人工构造的测试机器码，不是用户激活记录。

## 运行测试

```shell
python -m pytest tests -q
```

随附示例均为人工构造，供验证功能；真实订单应保留文本主键并用脱敏数据沟通。旧有本地 CLI 与协议工具保留作为工程兼容接口；新用户从 local_toolbox 开始。

许可证与组件说明见 LICENSE、local_toolbox/开源组件说明.txt。
