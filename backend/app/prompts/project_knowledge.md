# Interface-Agent 框架知识库

> 该文档描述框架的业务定位与领域模型事实：说明框架是做什么的，以及 3 个核心领域模型各自的字段与硬约束。

---

## 1. 框架定位

Interface-Agent 是上游系统与下游系统之间的接口中间层，核心职责如下：

1. 统一入口：通过 `interfaceUri` 接收请求并路由到对应工作流。
2. 协议适配：通过节点支持 `HTTP` / `WEBSERVICE` / `DATABASE` 调用。
3. 参数转换：通过参数映射完成双向结构转换。
4. 流程编排：通过工作流组织节点执行顺序，并支持调度与拆分。
5. 扩展能力：当上下游节点参数双向映射无法标准配置化时，通过 SPI 扩展远程调用行为。

数据流语义：

- `PRE_PROCESS`：上游请求 -> 下游请求
- `POST_PROCESS`：下游响应 -> 上游响应

---

## 2. 领域模型Workflow

Workflow 是对上游暴露的入口，按 `interfaceUri` 进行路由匹配。

| 字段 | 类型 | 必填 | 说明                                                                   |
|------|------|------|----------------------------------------------------------------------|
| flowId | Integer | 自动 | 主键                                                                   |
| flowName | String | 是 | 工作流名称，通常使用业务名称                                                       |
| interfaceUri | String | 是 | **路由键**；上游是Jarvis 的业务场景使用对应业务的固定值，非 Jarvis 场景推荐 `/agent-open-api/**` |
| contentType | WorkflowContentType | 是 | 请求与响应主格式：`JSON` / `XML`                                              |
| contentMetaInfo | String(JSON) | 否 | 仅 `contentType=XML` 时生效，用于 XML 解析控制（见下方说明）                           |
| firstFlowNodes | List<Integer> | 是 | 首节点 ID 列表，支持并行；**元素必须是已存在的 nodeId**                                  |
| status | Integer | 是 | 1 启用 / 0 禁用                                                          |

### 2.1 contentMetaInfo 配置说明

当 `contentType=XML` 且需 XML 解析控制时，可配置以下键：

| 键 | 说明                                       |
|------|------------------------------------------|
| elementName | 业务数据主节点名，用于定位实际业务数据载荷（如 SOAP Body 内目标节点） |
| isCDATA | 是否按 CDATA 方式读取/写入；未配置时默认 `true`          |
| escape | 是否先反转义再解析（`&lt;`→`<`）；适用于响应被二次转义的场景      |
| objectTag | 指定按对象解析的标签名集合，避免单元素被误判为数组                |

---

## 3. 领域模型WorkflowNode

WorkflowNode 是具体调用下游系统的节点单元，协议行为由 `nodeType` 与 `metaInfo` 决定。

| 字段 | 类型 | 必填 | 说明                                                           |
|------|------|------|--------------------------------------------------------------|
| nodeId | Integer | 自动 | 主键                                                           |
| nodeName | String | 是 | 节点名称，通常使用业务名称                                                |
| flowId | Integer | 否 | 所属工作流id                                                      |
| nodeType | NodeType | 是 | 节点协议类型：`HTTP` / `WEBSERVICE` / `DATABASE`                    |
| metaInfo | String(JSON) | 是 | 协议元配置，必填字段由 `nodeType` 决定（见下方说明）                             |
| keywordField | String | 否 | 日志关键字提取字段，用于从入参中提取业务关键字记入日志                                  |
| splitField | String | 否 | 数组拆分字段，用于把数组入参拆分成多次调用；适用于下游不支持批量数组的场景                        |
| paramFilterExpr | String | 否 | 过滤表达式（SpEL），上下文为 `#data`；过滤结果以 `#data` 变更结果为准，**过滤后为空则跳过调用** |
| scheduleExpr | String | 否 | 调度表达式（SpEL），**必须返回 `List<Integer>`（后续 nodeId 列表）或 `null`**   |
| scheduleParamSourceType | ScheduleParamSourceType | 条件 | 配置 `scheduleExpr` 时必填；`ORIGINAL`（原始入参）/ `PRE_RESPONSE`（前置节点响应） |
| remoteExtension | String | 否 | SPI 扩展名，用于标准配置无法覆盖的场景（如动态签名、加解密）                             |
| extensionParam | String(JSON) | 否 | SPI 扩展参数，与 `remoteExtension` 配合使用                            |

### 3.1 metaInfo 配置说明（按 nodeType）

#### HTTP

| 字段 | 必填 | 说明                                  |
|------|------|-------------------------------------|
| url | 是 | 完整 URL                              |
| method | 否 | `POST`/`GET`，默认 `POST`              |
| headers | 否 | 默认 `Content-Type: application/json` |

```json
{
  "url": "http://example.com/api",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json"
  }
}
```

#### WEBSERVICE

| 字段 | 必填 | 作用阶段 | 说明 |
|------|------|----------|------|
| url | 是 | 入参封装 | SOAP 地址 |
| headers | 否 | 入参封装 | 请求头 |
| soupTemplate | 是 | 入参封装 | SOAP 模板，`${inputParam}` 为占位符 |
| dataType | 否 | 入参封装 + 条件出参解析 | `json`/`xml`，默认 `xml`；用于请求体封装；在响应解析阶段仅当配置 `elementName` 且按文本/CDATA 抽取内容时，决定按 JSON 还是 XML 解析该内容 |
| elementName | 否 | 出参解析 | 响应业务数据标签定位 |
| isCDATA | 否 | 出参解析 | 默认 `true`，控制按 CDATA/文本读取 |
| escape | 否 | 出参解析 | 是否先反转义再解析 |
| objectTag | 否 | 出参解析 | 指定按对象解析的标签名列表 |

说明：

1. `responseType` 是独立键，用于后置映射完成后的结果结构格式化（`json`/`xml`），不用于 SOAP 原始响应解析。
2. WEBSERVICE 的原始响应解析由 `elementName`、`isCDATA`、`escape`、`objectTag`（以及条件下的 `dataType`）共同决定。

```json
{
  "url": "http://example.com/soap",
  "headers": {
    "Content-Type": "text/xml;charset=UTF-8"
  },
  "soupTemplate": "<soapenv:Envelope>...${inputParam}...</soapenv:Envelope>",
  "dataType": "xml",
  "elementName": "request",
  "isCDATA": true,
  "escape": false,
  "objectTag": [
    "PatientInfo"
  ]
}
```

#### DATABASE

| 字段 | 必填 | 说明 |
|------|------|------|
| driverClassName | 是 | JDBC 驱动类全限定名（非厂商简称） |
| url | 是 | JDBC URL |
| username | 是 | 用户名 |
| password | 是 | 密码 |
| operation | 是 | `SELECT`/`INSERT`/`UPDATE`/`DELETE` |
| sqlTemplate | 是 | SQL 模板，使用 `{paramName}` 占位 |
| responseType | 否 | 可选响应格式标识 |

常见驱动类：

- MySQL：`com.mysql.cj.jdbc.Driver`
- SQLServer：`com.microsoft.sqlserver.jdbc.SQLServerDriver`
- Oracle：`oracle.jdbc.OracleDriver`
- OpenGauss：`org.opengauss.Driver`

数据库响应约定：

- `SELECT`：`{"data": [...], "total": 行数}`
- 非 `SELECT`：`{"affectedRows": 影响行数}`

### 3.2 SpEL 表达式示例

`paramFilterExpr` 示例：

```spel
// 厂商类型过滤：仅处理 PACS 厂商的请求
#data[ServiceProviderType] == 'PACS' ? #data : #data.clear()

// 申请单场景中对 items 数组筛选：仅保留 PACS 科室的项目，过滤后为空则跳过调用
(#tempItems = #data[items]?.?[departType == PACS]) == null || #tempItems.isEmpty() ? #data.clear() : #data.put('items', #tempItems)
```

`scheduleExpr` 示例：

```spel
// 根据响应结果调度：成功时调度到节点 2，失败时不调度
#data[code] == '200' ? T(java.util.Arrays).asList(2) : null

// 条件分支调度：成功时并行调度节点 2、3，失败时调度节点 4
#data[code] == '200' ? T(java.util.Arrays).asList(2, 3) : T(java.util.Arrays).asList(4)
```

---

## 4. NodeParamConfig领域模型

NodeParamConfig 描述字段级转换规则，支撑 PRE_PROCESS/POST_PROCESS 双向转换。

| 字段 | 类型 | 必填 | 说明                                                                                                                  |
|------|------|----|---------------------------------------------------------------------------------------------------------------------|
| configId | Integer | 自动 | 主键                                                                                                                  |
| nodeId | Integer | 是  | 所属节点 ID                                                                                                             |
| processType | ProcessType | 是  | 映射阶段：`PRE_PROCESS`（上游请求→下游请求）/ `POST_PROCESS`（下游响应→上游响应）                                                            |
| parentId | Integer | 否  | 父配置 ID，用于构建嵌套结构                                                                                                     |
| sourceParamKey | String | 条件 | 源字段名；`sourceParamType != NONE` 时必填                                                                                  |
| sourceParamType | ParamType | 是  | 源字段类型：`STRING`/`INTEGER`/`LONG`/`DOUBLE`/`BOOLEAN`/`OBJECT`/`ARRAY`/`PURE_ARRAY`/`NONE`                             |
| targetParamKey | String | 是  | 目标字段名                                                                                                               |
| targetParamType | ParamType | 是  | 目标字段类型（同 sourceParamType 枚举）                                                                                        |
| mappingType | MappingType | 是  | 映射方式：`NAME`（同名）/ `CONSTANT`（常量，需填 mappingRule）/ `EXPRESSION`（SpEL，需填 mappingRule）/ `BEAN_EXPRESSION` / `SINGLE_MAP` |
| mappingSource | MappingSource | 条件 | **仅 POST_PROCESS 生效**：`RESPONSE`（下游响应）/ `INPUT`（原始入参）；父子节点应保持同一来源，跨源时用表达式显式访问                                       |
| mappingRule | String | 条件 | 映射规则；`CONSTANT` 填常量值，`EXPRESSION` 填 SpEL，`BEAN_EXPRESSION` 填 Bean 表达式                                               |
| keepSingleElementKey | Boolean | 否  | 单元素数组是否保留 key，若保留会将数组元素包装成对象(即使对象只有一个元素)                                                                            |
| paramDesc | String | 否  | 描述                                                                                                                  |
| sort | Integer | 是  | 排序字段,默认0                                                                                                            |

### 4.1 SINGLE_MAP 映射类型说明

`SINGLE_MAP` 用于处理基础数据类型数组（如 `[1, 2, 3]` 或 `["a", "b"]`）的元素映射。

**适用条件**：父节点的父节点为 `ARRAY` 或 `PURE_ARRAY`，且数组元素为基础数据类型。

**执行逻辑**：从包装的 Map 中取出第一个值（即原始基础类型值）。

### 4.2 数组类型说明

| 类型 | 适用场景 | 说明 |
|------|----------|------|
| `ARRAY` | `{"items": [...]}` | 数组包裹在对象字段中，源/目标皆可用 |
| `PURE_ARRAY` | `[...]` | **仅用于 sourceParamType**，适用于下游入参是纯数组格式（无包裹字段） |

### 4.3 数组类型虚拟节点结构

`ARRAY` / `PURE_ARRAY` 必须包含一层虚拟节点：

```text
ARRAY/PURE_ARRAY
  └── 虚拟节点(sourceParamType=NONE, targetParamType=OBJECT)
        └── 元素字段
```

虚拟节点名需要携带上`Node`后缀。

### 4.4 SpEL 上下文（映射表达式）

| 变量 | PRE_PROCESS | POST_PROCESS | 说明 |
|------|-------------|--------------|------|
| `#data` | 是 | 是 | 当前层级数据 |
| `#parent` | 是 | 否 | 父层级数据 |
| `#source` | 是 | 否 | 根层级数据 |
| `#input` | 否 | 是 | 原始输入 |
| `#response` | 否 | 是 | 下游响应 |

`mappingRule` SpEL表达式示例：

```spel
// PRE_PROCESS：从当前层级取字段值
#data[fieldName]

// PRE_PROCESS：从嵌套对象中取值
#data[patientInfo][patientCode]

// PRE_PROCESS：数组元素中取父层级字段（仅适用于 ARRAY/PURE_ARRAY 场景）
#parent[visitNo]

// POST_PROCESS：从下游响应取值并转换
#response[code] == '1' ? '200' : '-1'

// POST_PROCESS：从原始入参回填到响应
#input[requestId]
```

说明（适用于框架中所有 SpEL 场景）：

1. 统一使用中括号路径风格，如 `#data[fieldName]`，避免与 `.` 风格混用。
