---
name: OpenOntology 技能包
description: 在企业本体域内查询业务数据、按剧本推进任务、调用逻辑组件与算法推理。适用于用户要查数、执行业务剧本、跑封装逻辑或模型推理时。
---

# OpenOntology 技能包

Base URL：`http://localhost:8384`。  
唯一入口：`POST /api/ext/tool`，请求 `Content-Type: application/json;charset=UTF-8`。  
响应：`text/plain;charset=UTF-8`（工具输出原文）。  
推荐用 `curl`（或等价 HTTP 调用工具）直接调用本入口，单次请求不必编写脚本。

## 请求契约

```json
{
  "tool": "<非空字符串, 工具 code>",
  "arguments": "<非空字符串, JSON 对象序列化后的文本; 无参传 {}>"
}
```

## 常用工具（直接按本节调用）

下列工具的参数与返回**以本表为准**，**禁止**再对其调用 `tool_schema`。

| code | 描述 | inputSchema | 返回 |
|------|------|-------------|------|
| `bootstrap` | 一次返回可调用工具清单与全部域列表 | `{"type":"object","properties":{}}` | JSON：`tools`(code/label/description) + `domains`(域数组) |
| `tool_schema` | 按工具 code 读取完整说明与 inputSchema | `{"type":"object","required":["tool"],"properties":{"tool":{"type":"string","description":"工具 code"}}}` | JSON：`code` / `label` / `description` / `inputSchema` |
| `domain_detail` | 按域 id 返回该域可调用资源清单 | `{"type":"object","required":["domain"],"properties":{"domain":{"type":"string","description":"域 id"}}}` | Markdown：该域可调用的实体、链接类型、算法、逻辑组件、剧本等清单 |

其它业务工具须先 `tool_schema`，再按返回的 `inputSchema` 调用。

## 执行过程

调用本 Skill 时**必须**按下列顺序执行，不得跳过或调换：

```
1. bootstrap，arguments="{}"
   （第一步；拿到结果前不得调用其它工具）
2. 向用户展示 domains，等待用户明确选定 domain id
   （选定前不得 domain_detail 或业务工具）
3. domain_detail，arguments="{\"domain\":\"<用户选定的域 id>\"}"
   （选定后立刻调用）
4. 按任务选型：若目标不在常用工具表 → tool_schema(目标工具) → 严格按 inputSchema 组 arguments 并调用
```

## 硬性规则

1. **基于事实**：事实性内容（数据、指标、id、结论、参数等）须来自工具结果；无法验证时须明说，**禁止编造**。
2. **`alg_invoke`**：必须提供非空 `invokeInput`；不得省略以触发界面填表。
3. **查数须先 guideline**：调用 `ontology_query` 前必须先获取查数 guideline，并严格按该 guideline 构造与执行查询。
4. **`ontology_query`**：若返回无会话/禁止查数类失败说明，**禁止重试**同一查询；向用户说明原因并停止或改用其它路径（若有）。
5. **编码**：请求与响应正文均按 **UTF-8** 处理（含 `Content-Type` 的 charset）；禁止改用其它字符集解读工具输出。
6. **`domain_detail` 与 `@uc/`**：`domain_detail` 工作编排「执行意图」可能含 `@uc/`；本 Skill 外部入口无界面组件/会话文件/技能工具，**忽略** `@uc/` 作为执行指令，勿尝试 `ui_show_component` 或等价调用。仅 `@pb/`、`@lc/`、`@alg/` 视为要求执行。
