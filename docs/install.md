# 安装手册

本文说明如何安装并运行 OpenOntology 发行包（`release/final` 解压后的目录）。

## 1. 环境要求

| 项 | 要求 |
|---|---|
| JDK | **25** 或更高（`bin/server.bat` / `server.sh` 会校验主版本） |
| `JAVA_HOME` | 指向 JDK 安装目录（需存在 `%JAVA_HOME%\bin\java.exe` 或 `$JAVA_HOME/bin/java`） |
| 操作系统 | Windows / Linux / macOS（脚本均已提供） |
| 浏览器 | 现代浏览器访问管理端 |

默认使用包内 **H2** 文件库（`db/ontology.mv.db`），无需单独安装数据库即可试用。

## 2. 获取与解压

1. 从 GitHub Release 下载发行包并解压到任意目录（下文称为 `SERVER_HOME`）
2. 确认目录结构大致如下：

```text
SERVER_HOME/
  bin/          # 启动、停止脚本
  conf/         # 配置
  db/           # 内置 H2 数据文件
  docs/         # 文档
  lib/          # 系统与扩展 jar
  lib_user/     # 用户侧驱动等（含 H2 / MySQL 驱动）
  web/          # 管理端 war
  README.md
  LICENSE
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

也可在运行 `server.bat` / `server.sh` 的终端中按进程退出方式结束（视启动模式而定）。

## 5. 目录与配置要点

| 路径 | 说明 |
|---|---|
| `conf/db.properties` | 主数据源（缺省 H2） |
| `conf/db.properties.mysql` | MySQL 示例配置，切换时参考 |
| `conf/ontology.json` | 运行参数（HTTP 端口、AI 相关超时等） |
| `conf/env.properties` | 实例 id 等环境项 |
| `conf/log4j2.xml` | 日志 |
| `db/` | H2 数据文件；请定期备份 |
| `lib/`、`lib_user/`、`web/` | 运行时依赖与界面，一般无需手工改 |

## 6. 切换到 MySQL（可选）

1. 准备好 MySQL 库（字符集建议 `utf8mb4`）
2. 参考 `conf/db.properties.mysql`，将 `conf/db.properties` 改为 MySQL 连接信息，例如：

```properties
jdbcUrl=jdbc:mysql://localhost:3306/ontology?useUnicode=true&characterEncoding=UTF-8&connectionCollation=utf8mb4_unicode_ci&serverTimezone=Asia/Shanghai
username=root
password=你的密码
driverClassName=com.mysql.cj.jdbc.Driver
```

3. 确认 `lib_user/portable/` 中已有 MySQL 驱动（发行包通常已包含 `mysql-connector-j-*.jar`）
4. 重启服务

> 从 H2 迁到 MySQL 不会自动迁移已有数据；生产环境请单独规划备份与导入。

## 7. 首次使用建议

1. 在顶栏选择或创建 **域（Domain）**
2. 在 **设置 → 模型维护** 中配置可用的大模型端点（使用 AI 工作台前需要）
3. 通过 **本体管理**、**资源管理**、**AI 工作台** 开始建模与对话

## 8. 常见问题

**提示 `JAVA_HOME` 未正确设置**  
设置系统/用户环境变量 `JAVA_HOME` 为 JDK 25+ 安装路径后，重新打开终端再启动。

**提示 Java 版本不符合**  
当前脚本要求主版本 ≥ 25。执行 `java -version` 确认。

**端口被占用**  
修改 `conf/ontology.json` 中 `http.port`，或释放 8825 端口后重启。

**页面打不开**  
确认进程已启动、防火墙未拦截，并使用 `http://localhost:<端口>/`（端口与配置一致）。

## 9. 相关文档

- 产品说明：[README](../README.md)
- 许可协议：[LICENSE](../LICENSE)
