---
name: auto-config
description: 通过 MCP 接口完成接口对接的自动化配置，支持创建节点、参数映射、工作流和Mock验证
---

# 自动化配置 Skill

> 通过 MCP 接口完成接口对接的自动化配置

---

## 执行流程

```
0. 前置校验 → 检查本地服务是否启动
       ↓
1. 分析出入参 → 确定字段映射关系
       ↓
2. 创建节点 → 获取 nodeId
       ↓
3. 导入参数映射 → 前置 + 后置
       ↓
4. 创建 Mock → 获取 mockId
       ↓
5. 执行验证 → 查询日志确认映射正确
       ↓
6. 创建工作流 → 关联节点
```

---

## 步骤0：前置校验（必须）

在调用任何 MCP 接口前，**必须先校验本地服务是否启动**。

### 健康检查接口

**GET http://localhost:8099/HLOpenApi/Hjk**

### 校验逻辑

```
调用健康检查接口
     ↓
响应成功(200) → 继续执行后续步骤
     ↓
响应失败/超时 → 停止执行，提示用户启动服务,或者让用户告知端口是什么
```

### 服务未启动提示

```
⚠️ 本地服务未启动！

请先启动 interface-agent 服务后再执行自动化配置。
确认服务启动后，请重新发起配置请求。
```

---

## MCP 接口

### 基础路径

| 领域模型 | 路径 |
|------|------|
| Workflow | `/v1/ai/mcp/workflow` |
| WorkflowNode | `/v1/ai/mcp/workflow-node` |
| NodeParamConfig | `/v1/ai/mcp/node-param-config` |
| MockConfig | `/v1/ai/mcp/mock-config` |
| MockInvoke | `/v1/ai/mcp/mock-invoke` |
| InvokeLog | `/v1/ai/mcp/invoke-log` |

---

## 步骤1：创建节点

**POST /v1/ai/mcp/workflow-node/create**

```json
{
  "nodeName": "业务描述名称",
  "nodeType": "HTTP",
  "metaInfo": "{\"url\":\"http://xxx\"}",
  "keywordField": "patientCode"
}
```

**nodeType 选择**：
- HTTP → RESTful API
- WEBSERVICE → SOAP 接口
- DATABASE → 数据库直连

**响应**：`{"code":"200","rsp":8}` → rsp 就是 nodeId

---

## 步骤2：导入参数映射

**POST /v1/ai/mcp/node-param-config/import**

```json
{
  "nodeId": 8,
  "clearBeforeImport": true,
  "params": [
    {
      "processType": "PRE_PROCESS",
      "sourceParamKey": "patientCode",
      "sourceParamType": "STRING",
      "targetParamKey": "patNo",
      "targetParamType": "STRING",
      "mappingType": "NAME"
    }
  ]
}
```

### 前置处理模板（上游→下游）

**NAME 映射**：
```json
{
  "processType": "PRE_PROCESS",
  "sourceParamKey": "patientCode",
  "sourceParamType": "STRING",
  "targetParamKey": "patNo",
  "targetParamType": "STRING",
  "mappingType": "NAME"
}
```

**EXPRESSION 映射**：
```json
{
  "processType": "PRE_PROCESS",
  "sourceParamKey": "sex",
  "sourceParamType": "STRING",
  "targetParamKey": "gender",
  "targetParamType": "STRING",
  "mappingType": "EXPRESSION",
  "mappingRule": "#data == '1' ? '男' : '女'"
}
```

**CONSTANT 映射**：
```json
{
  "processType": "PRE_PROCESS",
  "sourceParamType": "NONE",
  "targetParamKey": "source",
  "targetParamType": "STRING",
  "mappingType": "CONSTANT",
  "mappingRule": "JARVIS"
}
```

### 后置处理模板（下游→上游）

**状态码转换**：
```json
{
  "processType": "POST_PROCESS",
  "sourceParamType": "NONE",
  "targetParamKey": "code",
  "targetParamType": "STRING",
  "mappingType": "EXPRESSION",
  "mappingSource": "RESPONSE",
  "mappingRule": "#response[returnCode] == '1' ? '200' : '-1'"
}
```

**字段映射**：
```json
{
  "processType": "POST_PROCESS",
  "sourceParamKey": "errorMessage",
  "sourceParamType": "STRING",
  "targetParamKey": "message",
  "targetParamType": "STRING",
  "mappingType": "NAME",
  "mappingSource": "RESPONSE"
}
```

### 嵌套对象

```json
{
  "processType": "PRE_PROCESS",
  "sourceParamType": "NONE",
  "targetParamKey": "patientInfo",
  "targetParamType": "OBJECT",
  "mappingType": "NAME",
  "childParams": [
    { "sourceParamKey": "code", ... },
    { "sourceParamKey": "name", ... }
  ]
}
```

### 数组（必须含虚拟节点）

```json
{
  "processType": "PRE_PROCESS",
  "sourceParamKey": "items",
  "sourceParamType": "ARRAY",
  "targetParamKey": "orders",
  "targetParamType": "ARRAY",
  "mappingType": "NAME",
  "childParams": [
    {
      "sourceParamType": "NONE",
      "targetParamKey": "orderNode",
      "targetParamType": "OBJECT",
      "mappingType": "NAME",
      "childParams": [
        { "sourceParamKey": "itemCode", "targetParamKey": "code", ... }
      ]
    }
  ]
}
```

---

## 步骤3：Mock 验证

### 创建 Mock

**POST /v1/ai/mcp/mock-config/create**

```json
{
  "nodeId": 8,
  "caseName": "成功场景",
  "mockResponse": "{\"returnCode\":\"1\",\"message\":\"成功\"}"
}
```

### 执行调用

**POST /v1/ai/mcp/mock-invoke/invoke?nodeId=8&mockId=15**

```json
{
  "patientCode": "TEST001",
  "patientName": "测试"
}
```

### 查询日志

**GET /v1/ai/mcp/invoke-log/latest?limit=1**

**验证项**：
- `paramBeforeInvoke` → 前置映射结果
- `paramAfterInvoke` → 后置映射结果

---

## 步骤4：创建工作流

**POST /v1/ai/mcp/workflow/create**

```json
{
  "flowName": "个人建档接口",
  "interfaceUri": "CreateArchives",
  "contentType": "JSON",
  "firstFlowNodes": [8],
  "status": 1
}
```

**interfaceUri 规则**：
- Jarvis 上游 → 使用具体的业务名称，如 CreateArchives
- 其他上游 → 使用 `/agent-open-api/**`

---

## 验证成功输出

```
✅ 配置完成！

节点：HIS建档接口 (nodeId: 8)
工作流：个人建档接口 (flowId: 10)

前置映射验证：
- patientCode → patNo: ✅
- sex "1" → gender "男": ✅

后置映射验证：
- returnCode "1" → code "200": ✅
```

---

## 验证失败处理

```
⚠️ 映射验证发现问题：

问题：性别转换未生效
- 期望：sex "1" → gender "男"
- 实际：gender "1"
- 原因：mappingType 应为 EXPRESSION

正在修复...
```
