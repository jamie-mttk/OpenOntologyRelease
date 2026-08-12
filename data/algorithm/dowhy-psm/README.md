# DoWhy PSM 部署包

ATE/ATT/ATC 估计（多种后门/IV 法）+ 政策反事实 invoke（`treatmentRate`）。

v2.0 起 hyperparams 分区：`causalModel` / `identify` / `estimate` / `methodParams`；bindings 支持 `graph`、`instruments`、`effectModifiers`。

## 环境

**DoWhy 需 Python 3.10–3.13**（不支持 3.14）。后端在**首次训练**时会自动：

1. 用 `algorithm.python-executable`（默认 `py -3.12`）创建 `dowhy-psm/.venv`
2. `pip install -r requirements.txt`

本地 fixture 自测仍须已有 venv：

```powershell
cd data/algorithm
dowhy-psm/.venv/Scripts/python run_fixture_test.py dowhy-psm
```

## 共享库

因果推断公共逻辑位于 `scripts/dowhy_common/`（bindings、identify、estimate、report 等）。

## 注册

`POST /api/algorithm/deploy` 扫描本目录 `manifest.json` 入库。

## 附录：demo1 营销因果

见原 README 流程；`code` 仍为 `dowhy-psm`，兼容已有实例与剧本。
