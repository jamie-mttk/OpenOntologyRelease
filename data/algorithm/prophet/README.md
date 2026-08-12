# Prophet 时序预测

Facebook Prophet 通用时序插件（`FIT_FORECAST`）。按 Prophet 能力设计，**不**绑定特定业务表。

## 能力

- 绑定：`ds`（时间）、`y`（目标）
- 多项 `regressors` → `add_regressor`
- 多项 `holidays` → Prophet `holidays` DataFrame（BOOLEAN 指示列）
- 超参：`freq`（D/W/MS/…）、季节项开关、`seasonalityMode`、`growth` 等
- 训练产物：`model.joblib` + `meta.json`
- 预测：`periods`（单位 = `freq` 一步）+ 可选 `regressorValues` + 可选 `futureHolidays`（推理前合并进模型 holidays，与训练时同名 holiday 共用效应系数）

## 环境

```bash
cd data/algorithm/prophet
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### Windows：C++ 工具链 + CmdStan

Prophet 训练需要 **CmdStan**（统计引擎）和 **C++ 编译器**（`g++` + `make`）。

1. 安装 RTools45（提供 `g++` / `make`）：
   ```powershell
   winget install RProject.Rtools --accept-package-agreements --accept-source-agreements
   ```
2. 将以下目录加入**用户 PATH**（已为本机配置可跳过）：
   - `C:\rtools45\usr\bin`
   - `C:\rtools45\x86_64-w64-mingw32.static.posix\bin`
   - `C:\Users\<你>\.cmdstan\cmdstan-2.39.0\stan\lib\stan_math\lib\tbb`（CmdStan 安装后才有）
3. RTools45 默认只有 `make.exe`，CmdStan 需要 `mingw32-make`：
   ```powershell
   Copy-Item C:\rtools45\usr\bin\make.exe C:\rtools45\usr\bin\mingw32-make.exe
   ```
4. **新开终端**后编译 CmdStan（约 5–10 分钟）：
   ```powershell
   .venv\Scripts\python -m cmdstanpy.install_cmdstan
   ```

后端训练/推理优先使用本目录 `.venv\Scripts\python.exe`。**修改 PATH 后需重启后端**（`run-backend.cmd`），Java 子进程才能找到编译器与 TBB。

> Windows 注意：后端子进程**不能**设置 `PYTHONUTF8=1`，否则 cmdstanpy 读取 `where.exe` 输出会乱码，训练报 `stan_backend` 相关错误。已由 `PythonProcessSupport` 修复，改代码后请重启后端。

## 本地自测

```bash
cd data/algorithm
prophet/.venv/Scripts/python run_fixture_test.py prophet
```

## 注册

`POST /api/algorithm/deploy?domainId=d010000000000000000000000000001`

或 `backend/src/main/resources/db/demo/24_seed_prophet_algorithm.sql`。

## 附录：demo1_sales 冒烟（可选）

1. 实体 `sales`，query 自行 filter / orderBy
2. `ds=sale_date`, `y=weekly_sales`, `freq=W`
3. `holidays=[{ name:"节假日", column:"is_holiday" }]`
