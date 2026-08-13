# 安装手册

本文说明如何安装并运行 OpenOntology 发行包。

## 1. 环境要求

| 项 | 要求 |
|---|---|
| JDK | **25** 或更高（`bin/server.bat` / `server.sh` 会校验主版本） |
| `JAVA_HOME` | 指向 JDK 安装目录（需存在 `%JAVA_HOME%\bin\java.exe` 或 `$JAVA_HOME/bin/java`） |
| 操作系统 | Windows / Linux / macOS（脚本均已提供） |
| 浏览器 | 需支持 **HTML5** 的现代浏览器（Chrome / Edge / Firefox / Safari 等） |

默认使用包内 **H2** 文件库（`db/ontology.mv.db`），无需单独安装数据库即可使用。

仅使用智能体工作台查数、剧本等，**不必**安装 Python / bash。若要使用 **算法训练与推理**，或依赖 bash 的 **技能执行（skill_exec）**，请先按下一节准备环境。

<a id="python-bash"></a>

## 1.1 可选：Python 与 bash（算法 / 技能）

### 何时需要

| 能力 | 需要 |
|---|---|
| 算法库训练、推理（创建 venv、pip 装依赖、跑 Python 算法包） | **Python** |
| 技能里通过 bash 执行命令（`skill_exec` 等） | **bash** |

### Python

- 版本：**3.10–3.13**（代码侧提示：部分算法如 DoWhy **不支持 3.14**）  
- 安装后终端可执行 `python --version`（Windows 也可用 `py -3.12 --version`）  
- 系统需能找到 Python（在 `PATH` 中），或在配置中指定，例如 `algorithm.pythonExecutable`（可为 `python` 或 `py -3.12`）  
- 首次跑某算法时，平台会在 `data/algorithm-runtime/` 下自动创建 `.venv` 并安装依赖，可能较久，属正常现象  

Windows 可从 [python.org](https://www.python.org/downloads/) 安装，勾选 **Add python.exe to PATH**。

### bash

平台解析可用 bash 时**不会**回退到 cmd / PowerShell。

- **Linux / macOS**：一般系统自带；执行 `bash --version` 确认  
- **Windows**：推荐安装 [Git for Windows](https://git-scm.com/download/win)（含 Git Bash），并将 **`Git\bin`**（含 `bash.exe`）加入系统 `PATH`（仅加 `Git\cmd` 往往不够）  
- 也可在 `conf/ontology.json` 中增加配置项，显式指定 bash 绝对路径，例如 key 为 `bash.path`、value 为 `C:\\Program Files\\Git\\bin\\bash.exe`（按本机实际路径修改；改完需重启）  

自检：

```bat
bash -c "echo BASH_OK"
```

应输出 `BASH_OK`。修改 `PATH` 或 `conf/ontology.json` 中的 `bash.path` 后请**重启**本服务。

## 2. 目录说明

从 GitHub Release 下载发行包并解压到任意目录（下文称为 `SERVER_HOME`）。目录大致如下：

```text
SERVER_HOME/
  bin/          # 启动、停止脚本
  conf/         # 配置
  db/           # 内置 H2 数据文件
  data/         # 运行期业务数据（技能包、算法包、会话文件等；首次运行可自动创建）
  temp/         # 临时目录（解压、运行中间文件等；可清理，勿作持久存储）
  docs/         # 文档与 Skills
  lib/          # 系统与扩展 jar
  lib_user/     # 用户侧驱动等（含 H2 / MySQL 驱动）
  web/          # 管理端 war
  README.md
  LICENSE
  NOTICE
```

## 3. 启动

### Windows

```bat
cd /d SERVER_HOME
bin\startup.bat
```

### Linux / macOS

```bash
cd SERVER_HOME
chmod +x bin/*.sh
./bin/startup.sh
```

启动成功后，浏览器打开：

```text
http://localhost:8825/
```

端口来自 `conf/ontology.json` 中的 `http.port`（缺省 **8825**）。修改后需重启生效。

## 4. 停止

### Windows

```bat
bin\shutdown.bat
```

### Linux / macOS

```bash
./bin/shutdown.sh
```

## 5. 切换其他数据库（可选）

缺省使用包内 H2。若要改用 MySQL、PostgreSQL 等其它库：

1. **修改** `conf/db.properties`：按目标库填写 `jdbcUrl`、`username`、`password`、`driverClassName` 等（可参考同目录下的 `db.properties.mysql` 示例）  
2. **拷贝** 对应 JDBC 驱动 jar 到 `SERVER_HOME/lib_user/portable/`（发行包通常已带 MySQL 驱动；其它库需自行放入）  
3. **重启** 服务  

> 更换数据源不会自动迁移已有库中的数据；生产环境请单独规划备份与导入。

## 6. 首次使用建议

首次打开会进入 **系统初始化**（详见 [快速开始 · 系统初始化](quickstart.md#4-系统初始化首次必做)）：

1. 配置大语言模型：推荐点 **使用 DeepSeek**，按弹窗说明申请并填写 API Key；或自行填写兼容端点  
2. 配置业务域：推荐 **导入零售测试数据**，或自行填写 JDBC 新建  
3. 通过 **本体管理**、**资源管理**、**智能体工作台** 开始建模与对话

## 7. 本系统内安装 Skills

本系统的技能包从 `SERVER_HOME/data/skills/` 加载（每个子目录一份包，且须含 `SKILL.md`）。运行态依赖在 `data/skills-runtime/`，一般无需手工改。

### 7.1 安装步骤

1. 将技能包目录（含 `SKILL.md` 及包内文件）**拷贝**到：

```text
SERVER_HOME/data/skills/<技能目录名>/
```

例如：`SERVER_HOME/data/skills/my-skill/SKILL.md`。

2. 任选其一使系统生效：  
   - **重启**服务；或  
   - 在界面 **设置 → 技能管理** 中点击 **刷新目录**（重新扫描 `data/skills`）

3. 在技能管理中确认已出现该技能，并可在智能体侧按域选用。

> `docs/skills/` 下的 OpenOntology 技能包是给 **Claude Code / Cursor 等外部平台** 用的，见下一节；与本系统 `data/skills` 不是同一安装路径。

## 8. Skills（外部平台）

本发行包将部分能力以 **Skill** 形式提供，可安装到 Claude Code、Cursor 等支持 Agent Skills 的外部平台，通过 HTTP 调用本系统已启动的服务（如查数、剧本、逻辑组件等；**不含** `alg_invoke` 算法推理）。

技能包位置：`docs/skills/`（例如 `docs/skills/openOntology/`，入口文件为 `SKILL.md`）。

### 8.1 前提

1. 已按上文启动 OpenOntology，并完成系统初始化（至少一个域与可用大模型，视任务而定）  
2. 确认管理端可访问（缺省 `http://localhost:8825/`）  
3. 外部平台所在机器能访问该服务地址（本机或内网）

### 8.2 安装到外部平台

将整个技能目录（含 `SKILL.md`）复制到目标平台的 skills 加载路径。常见做法：

| 平台 | 参考做法 |
|---|---|
| Claude Code | 复制到项目或用户 skills 目录（以官方 Agent Skills 约定为准，例如项目下 `.claude/skills/openOntology/`） |
| Cursor | 复制到项目 skills 目录（以 Cursor Skills 约定为准，例如 `.cursor/skills/openOntology/`） |
| 其它 | 按该平台文档将含 `SKILL.md` 的目录放到其扫描路径 |

目录名建议保持 `openOntology`，与 `SKILL.md` 中的技能名一致，避免平台无法识别。

### 8.3 配置服务地址

`SKILL.md` 中的 **Base URL** 须指向本系统实际地址。缺省示例可能为 `http://localhost:8384`；若你的 `conf/ontology.json` 中 `http.port` 为 **8825**，请改为：

```text
http://localhost:8825
```

唯一工具入口：`POST {Base URL}/api/ext/tool`（详见该 `SKILL.md` 的请求契约与执行顺序）。

### 8.4 验证

1. 确认 OpenOntology 已启动  
2. 在外部平台启用/选中该 Skill 后发起一次简单任务（如列出可用域）  
3. 若调用失败，检查 Base URL、端口、防火墙，以及服务端日志

更细的工具列表、调用顺序与硬性规则以技能包内 [`SKILL.md`](skills/openOntology/SKILL.md) 为准。

## 9. 常见问题

**提示 `JAVA_HOME` 未正确设置**  
设置系统/用户环境变量 `JAVA_HOME` 为 JDK 25+ 安装路径后，重新打开终端再启动。

**提示 Java 版本不符合**  
当前脚本要求主版本 ≥ 25。执行 `java -version` 确认。

**端口被占用**  
修改 `conf/ontology.json` 中 `http.port`，或释放 8825 端口后重启。

**页面打不开**  
确认进程已启动、防火墙未拦截，并使用 `http://localhost:<端口>/`（端口与配置一致）；浏览器需支持 HTML5。

**外部 Skill 调用失败**  
确认服务已启动、Base URL 与端口一致，且 `POST /api/ext/tool` 可从外部平台所在环境访问。

**本系统技能列表没有新包**  
确认已拷贝到 `data/skills/<目录>/SKILL.md`，并已重启或在「设置 → 技能管理」中点击 **刷新目录**。

## 10. 相关文档

- 产品说明：[README](../README.md)
- 快速开始：[快速开始](quickstart.md)
- 许可协议：[LICENSE](../LICENSE)
- OpenOntology Skill（外部平台）：[skills/openOntology/SKILL.md](skills/openOntology/SKILL.md)
