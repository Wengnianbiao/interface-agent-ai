---
trigger: model_decision
description: 
---
# 账单退费状态查询接口配置指南

> **业务专用指南**：提供账单退费状态查询场景的完整配置示例和步骤

---

## 目的

查询HIS系统中账单的退费状态，确认账单是否已退费、退费人员、退费时间等信息。

---

## 场景识别

当客户提到「查询退费状态」「查询退款状态」「账单退费查询」「退费确认」时，明确为退费状态查询场景。

---

## 业务要点

### 1. 节点关键字配置

**keywordField**：`patientInfo.patientCode`

用于日志检索和问题排查，框架会从Jarvis入参中提取此字段值作为业务关键字记录到调用日志中。

**配置位置**：节点配置的 `keywordField` 字段

### 2. 查询条件字段

退费状态查询通常需要传递：

| 字段 | 来源 | 说明 |
|------|------|------|
| hisOrderId | `presId` | HIS处方ID/订单号 |
| patientCode | `patientInfo.patientCode` | 体检编号 |

### 3. 响应数据结构转换

**特殊映射**：HIS返回 OBJECT，需转换为 ARRAY

- HIS响应：`data` (OBJECT)
- Jarvis出参：`rsp` (ARRAY)
- **虚拟节点必须配置**：`rspNode`，用于对象转数组映射

### 4. 退费状态字段转换

**状态码转换**：HIS与Jarvis的退费状态定义可能不同

| HIS orderStatus | Jarvis status | 说明 |
|-----------------|---------------|------|
| "2" | "1" | 已退费 |
| 其他 | "0" | 未退费 |

**映射规则**：`#data == '2' ? '1' : '0'`

### 5. 退费状态信息

HIS返回的退费状态信息：

| HIS字段 | Jarvis字段 | 说明 |
|---------|-----------|------|
| hisOrderId | presId | 处方ID |
| orderStatus | status | 退费状态（转换后：1=已退费，0=未退费） |
| settleUserId | - | 退费员ID |
| settleUserName | - | 退费员姓名 |
| settleUserTime | - | 退费时间 |

### 6. 嵌套字段提取

Jarvis入参中关键字段在嵌套对象内，需用EXPRESSION提取：

| 目标 | 来源 | 映射规则 |
|------|------|----------|
| patientCode | `patientInfo.patientCode` | `#data[patientCode]` |

---

## Jarvis入参

```json
{
  "presId": "35819619",
  "hisDetailIdList": [
    null
  ],
  "patientInfo": {
    "sex": "2",
    "age": 40,
    "marriage": "3",
    "identitycard": "330381198508301507",
    "cardType": "1",
    "patientLevelName": "普通体检人",
    "phone": "13958809733",
    "birthday": "1985-08-30",
    "address": "浙江省温州市龙湾区海城街道中心南路９７号",
    "patientName": "周志芳",
    "patientCode": "82601100001",
    "hisPatientId": "4602675",
    "visitNo": "2100498142",
    "userType": 0,
    "orgName": "",
    "registertime": "2026-01-10 08:02:38",
    "physicalTypes": "physical:types:A",
    "physicalTypeName": "健康体检",
    "nation": "01",
    "nationName": "汉族"
  }
}
```

**关键字段**：
- `patientInfo.patientCode` - keywordField，体检编号
- `presId` - HIS处方ID（查询条件）
- `patientInfo.hisPatientId` - HIS患者档案号
- `patientInfo.visitNo` - HIS就诊号

---

## Jarvis出参

```json
{
  "code": "200",
  "message": "成功!",
  "rsp": [
    {
      "presId": "35819619",
      "status": "0"
    }
  ]
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| code | 状态码，200成功 |
| message | 响应消息 |
| rsp | 退费状态列表（数组） |
| rsp[].presId | 处方ID |
| rsp[].status | 退费状态（1=已退费，0=未退费） |

---

## 映射配置示例

> **重要说明**：以下示例仅用于说明映射配置方法，实际HIS接口的入参、出参字段必须以客户提供的接口文档或实际出入参为准。

### HIS入参示例

```json
{
  "hisOrderId": "35819619",
  "patientCode": "82601100001"
}
```

### HIS响应示例

```json
{
  "data": {
    "hisOrderId": "35819619",
    "patientCode": "82601100001",
    "settleUserId": "8888",
    "settleUserName": "8888",
    "settleUserTime": "2026/1/10 8:05:21",
    "orderStatus": "1"
  },
  "returnCode": "1",
  "errorMessage": "成功!"
}
```

### 前置处理映射（Jarvis → HIS）

| Jarvis字段 | 源参数类型 | HIS字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| presId | STRING | hisOrderId | STRING | NAME | - |
| patientInfo | OBJECT | patientCode | STRING | EXPRESSION | `#data[patientCode]` |

### 后置处理映射（HIS → Jarvis）

| HIS字段 | 源参数类型 | Jarvis字段 | 目标参数类型 | 映射类型 | 映射数据源 | 映射规则 |
|---------|-----------|-------------|-------------|----------|-----------|----------|
| returnCode | STRING | code | STRING | EXPRESSION | RESPONSE | `#data == "1" ? "200" : "-1"` |
| errorMessage | STRING | message | STRING | NAME | RESPONSE | - |
| data | OBJECT | rsp | ARRAY | NAME | RESPONSE | 对象转数组映射 |
| - | NONE | └─ rspNode | OBJECT | NAME | RESPONSE | 虚拟节点 |
| └─ hisOrderId | STRING |     └─ presId | STRING | NAME | RESPONSE | - |
| └─ orderStatus | STRING |     └─ status | STRING | EXPRESSION | RESPONSE | `#data == '2' ? '1' : '0'` |

---

## AI配置步骤

### 步骤1：获取HIS接口信息

询问客户提供HIS接口文档，或明确以下信息：

**必须信息**：
1. HIS查询退费状态接口的入参字段及格式
2. HIS查询退费状态接口的响应字段及格式
3. 退费状态字段的取值含义（如：2=已退费，1=已支付，0=未支付）

### 步骤2：生成前置映射（Jarvis → HIS）

参考上述前置处理映射表

### 步骤3：生成后置映射（HIS → Jarvis）

参考上述后置处理映射表

**注意**：
- 对象转数组映射必须配置虚拟节点
- 退费状态需根据HIS接口定义进行转换
