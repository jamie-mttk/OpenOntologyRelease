---
name: skillhub-install
description: 理解用户意图, 在 SkillHub 上搜索并安装合适的技能到本平台 skills 目录.
context: inline
version: "1.0.0"
---

# skillhub-install(SkillHub 搜索与安装)

## SKILLS_ROOT

**SKILLS_ROOT** 即本平台 **`skills` 根目录**: 根据 **本技能包所在路径** 判定(本包装在 `{SKILLS_ROOT}/skillhub-install/` 下, 故 **SKILLS_ROOT** 为其父目录).

- 每个技能占 **SKILLS_ROOT** 下的 **一个子目录**, 子目录名为该技能的 **code**(小写, 与 `resource_search(kind=skill)` 中的 code 一致).
- 子目录内须含 **`SKILL.md`** 及技能包文件.

---

## 流程

### Step 1 · 理解需求

从用户自然语言归纳 **搜索意图**, 并提取 **1~3 个关键词**(中英文均可). 不把用户随口说的名称当作已选定、待安装的技能.

### Step 2 · 搜索 SkillHub

调用 SkillHub 公开搜索接口, 用 **shell** 取回 JSON 并解析. **本步可重复执行, 最多 3 次**(每次换用 Step 1 中的不同关键词).

**请求**(与 SkillHub 官网一致; keyword 须 URL 编码, 含空格)

```text
GET https://api.skillhub.cn/api/skills?page=1&pageSize=24&sortBy=score&order=desc&keyword={关键词}
```

**搜索结果字段**

从 `data.skills` 解析; 多次搜索按 **`slug`**(技能 code, 小写) 去重合并. 每条命中须保留下列字段, 用于理解「这是什么 skill」以及 Step 5 调用下载 API:

| JSON 字段 | 含义 | 后续用途 |
|-----------|------|----------|
| **`slug`** | 技能 **code**(小写); 与本平台 `{SKILLS_ROOT}/{code}/`、`choose_one` 的 **value** 一致 | Step 5 下载 URL 查询参数 **`slug`**(SkillHub 固定参数名, 取值即 code) |
| **`name`** | SkillHub 展示名 | Step 3 choose_one 卡片 **label** |
| **`description`** | 技能描述 | 向用户说明命中项; Step 3 卡片 **description** |
| **`version`** | 发布版本 | Step 5 可选 **`&version={version}`** |
| **`namespace.handle`** | 发布者 handle | Step 5 下载 URL 查询参数 **`handle`** |

仍无可用条目则换词或如实说明.

### Step 3 · 用户择一(必须)

在 Step 2 得到的全部结果中, 按与用户 **意图** 的贴合度筛选, **最多 5 个** 候选, 用 **@uc/choose_one[多项择一]** 请用户选定一项.

1. `resource_get(kind=uc, id=choose_one)` 读取组件 schema.
2. `ui_show_component` 渲染 choose_one:
   - **description**(Markdown): 写清用户的 **意图**、本流程用过的 **关键词**. 若有候选已在本地安装, 另起一段用 **加粗** 与红色强调, 例如: **<span style="color:#F56C6C">下列标「本平台已安装」的项无需重复安装; 若仍要选择, 下一步将确认是否覆盖.</span>**
   - **options**(最多 5 项):
     - **label**: 取 Step 2 条目 JSON **`name`**; 已安装时可加 ` · 已安装` 后缀.
     - **description**: 结合搜索结果中的 **description** 说明用途与匹配理由. 若 `resource_search(kind=skill)` 已有相同 **code**, **description 必须以固定前缀开头** `【本平台已安装】`(界面红色加粗), 前缀后换行再写解读; 不得仅放在末尾或弱提示.
     - **value**: 填该技能的 **code**(小写). 未填时组件会回传 label, 因此 **务必填写 code**.
3. 用户点 **取消** → 结束并说明已取消.
4. 用户点选某卡片 → 组件 **selectAction** 回传该项的 **value**(即 **code**). Agent 在 Step 2 的搜索结果里用 **code** 找到对应条目的 **handle**、**version** 等, 供安装使用; **不要**要用户再口述 handle 或版本.

### Step 4 · 覆盖确认(若已存在)

用户选定 **code** 后, 若 **`resource_search(kind=skill)`** 中已有该 code → **choose_one** 或明确追问 **跳过 / 覆盖安装**; **覆盖**时删除 `{SKILLS_ROOT}/{code}/` 后再进入 Step 5.

### Step 5 · 下载并安装(Agent 执行)

安装参数来自 Step 3 选中 **code** 在 Step 2 搜索结果中的 **handle**、**code**、**version**(可选).

**下载请求**

```text
GET https://api.skillhub.cn/api/v1/download?handle={handle}&slug={技能 code}
```

可选: `&version={version}`. URL 中查询参数 **`slug`** 为 SkillHub 固定名, 取值即 **code**.

1. 用 shell 下载 zip 到临时路径.
2. 解压到临时目录, 定位 **skill 根目录**:
   - 解压根有 `SKILL.md`, 或
   - 解压根下 **仅一个** 子目录且该目录含 `SKILL.md`.
3. 将 skill 根 **整树复制** 到 `{SKILLS_ROOT}/{code}/` (覆盖时先删目标).
4. 校验 `{SKILLS_ROOT}/{code}/SKILL.md` 存在.

### Step 6 · 收尾

- 在 **SKILLS_ROOT** 创建空文件 **`.oo-skills-reload`**, 触发平台重载技能目录(约数秒内生效).
- 用 `resource_search(kind=skill)` 核对后再提示用 `skill(code, …)` 调用.

---

## 失败处理

| 情况 | 处理 |
|------|------|
| 搜索无结果 | 换同义词/英文/更泛关键词(仍受 Step 2 最多 3 次限制); 仍无则如实说明 |
| 下载失败或 zip 无效 | 报错, 勿留不完整目录; 可建议设置页手动安装 |
| 包内无 SKILL.md | 拒绝安装, 删除不完整目标目录 |
| 重载后仍搜不到新技能 | 稍等一轮或联系管理员 |
