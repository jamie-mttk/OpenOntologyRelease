---
name: OpenOntology 技能包
description: 在企业本体域内查询业务数据、按剧本推进任务、调用逻辑组件。适用于用户要查数、执行业务剧本或跑封装逻辑时。算法推理(alg_invoke)不对外部 Skill 开放。
---

# OpenOntology 技能包

Base URL：`http://localhost:8825`。  
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
| `bootstrap` | 一次返回可调用工具清单与全部域列表 | `{"type":"object","properties":{}}` | JSON：`tools` + `domains` |
| `tool_schema` | 按工具 code 读取完整说明与 inputSchema | `{"type":"object","required":["tool"],"properties":{"tool":{"type":"string"}}}` | JSON：`code` / `label` / `description` / `inputSchema` |
| `domain_detail` | 当前域信息、资源发现约定、执行铁律、查数规则 | `{"type":"object","required":["domain"],"properties":{"domain":{"type":"string","description":"域 id"}}}` | Markdown（**不含**全量资源表） |
| `resource_search` | 按 kind 分页搜索资源（对齐主流程） | `{"type":"object","required":["kind","domain"],"properties":{"kind":{"type":"string"},"domain":{"type":"string"},"page":{"type":"integer"},"size":{"type":"integer"}}}` | JSON PageResult |
| `resource_get` | 按 kind+id 读详情 | `{"type":"object","required":["kind","id"],"properties":{"kind":{"type":"string"},"id":{"type":"string"},"domain":{"type":"string"}}}` | JSON 或剧本 Markdown |

其它业务工具须先 `tool_schema`，再按返回的 `inputSchema` 调用。

### resource_search 要点

- `kind`: `entity` \| `relation` \| `algl` \| `alg` \| `lc` \| `uc` \| `pb` \| `skill`
- **必须**传用户选定的 `domain`（域 id）；与主流程「会话绑域」等价，由调用方显式传入
- `pb` 仅 ON_DEMAND；常驻剧本已在 `domain_detail`「执行铁律」中，勿再 search/get
- 无关键字过滤；翻页用 `page`（从 0）/ `size`（默认 20）

### resource_get 要点

- `id` 须来自同 `kind` 的 `resource_search` 返回，禁止臆造
- `domain` 可选（服务端按 id 加载，不校验归属）

## 执行过程

调用本 Skill 时**必须**按下列顺序执行，不得跳过或调换：

```
1. bootstrap，arguments="{}"
   （第一步；拿到结果前不得调用其它工具）
2. 向用户展示 domains，等待用户明确选定 domain id
   （选定前不得 domain_detail / resource_* / 业务工具）
3. domain_detail，arguments="{\"domain\":\"<用户选定的域 id>\"}"
   （选定后立刻调用；记下当前域 id，后续 resource_search 一律带同一 domain）
4. 按任务用 resource_search / resource_get 发现与读取资源（对齐主流程，禁止臆造 id）
5. 业务工具：若目标不在常用工具表 → tool_schema → 严格按 inputSchema 调用
   （查数前须 ontology_guide；逻辑组件用 logic_component_invoke）
```

## 硬性规则

1. **基于事实**：事实性内容（数据、指标、id、结论、参数等）须来自工具结果；无法验证时须明说，**禁止编造**。
2. **禁止 `alg_invoke`**：外部入口已屏蔽；见算法相关资源时不得尝试调用。
3. **查数须先 guideline**：调用 `ontology_query` 前必须先 `ontology_guide`，并严格按指南构造查询；字段不清时先 `resource_get(kind=entity, id=...)`。
4. **`ontology_query`**：若返回无会话/禁止查数类失败说明，**禁止重试**同一查询；向用户说明原因并停止或改用其它路径（若有）。
5. **编码**：请求与响应正文均按 **UTF-8** 处理；禁止改用其它字符集解读工具输出。
6. **执行意图**：仅 `@pb/`、`@lc/` 视为要求执行（逻辑组件用 `logic_component_invoke`）。**忽略** `@uc/`、`@alg/`、技能执行指令（外部无对应工具）。
7. **禁止假会话**：外部无 conversation；资源发现靠显式 `domain`，勿假设存在会话上下文。
