---
trigger: model_decision
description: 
---
# 账单收费通知接口配置指南

> **业务专用指南**：提供HIS主动推送收费通知场景的完整配置示例和步骤

---

## 目的

接收HIS系统主动推送的账单收费通知，更新Jarvis的账单支付状态。

---

## 场景识别

当客户提到「收费通知」「支付通知回调」「HIS推送支付状态」「收费回调」时，明确为账单收费通知场景。

---

## 业务要点

### 1. 数据流向（重要）

**与其他接口不同**：此接口是 **HIS → Jarvis** 的推送场景

- **上游接口**：HIS系统（主动推送方）
- **下游接口**：Jarvis接口（被动接收方）
- **Jarvis入参格式固定**：不可更改
- **Jarvis出参格式固定**：不可更改

### 2. 通知类型

HIS推送的通知类型：

| chargeType | 说明 |
|------------|------|
| CHARGED | 收费通知 |
| REFUNDED | 退费通知（可能存在） |

### 3. 前置处理映射（HIS → Jarvis）

从HIS推送数据中提取关键字段：

| HIS字段 | Jarvis字段 | 说明 |
|---------|-----------|------|
| data.hisOrderId | presId | HIS处方ID |
| data.settleUserId | - | 收费员ID（不传给Jarvis） |
| data.settleUserName | - | 收费员姓名（不传给Jarvis） |
| data.settleUserTime | - | 收费时间（不传给Jarvis） |

### 4. 后置处理映射（Jarvis → HIS）

将Jarvis响应转换为HIS期望的格式：

| Jarvis字段 | HIS字段 | 转换规则 |
|-----------|---------|----------|
| code | returnCode | `#data == '200' ? '1' : '0'` |
| message | errorMessage | 直接映射 |

### 5. 嵌套字段提取

HIS推送数据在 `data` 对象内，需用EXPRESSION提取：

| 目标 | 来源 | 映射规则 |
|------|------|----------|
| presId | `data.hisOrderId` | `#data[data][hisOrderId]` |

---

## HIS推送入参

```json
{
  "chargeType": "CHARGED",
  "data": {
    "patientId": "5023461",
    "settleUserId": "8888",
    "settleUserName": "一卡通",
    "settleUserTime": "2026/1/14 13:43:01",
    "hisOrderId": "35857670"
  }
}
```

**关键字段**：
- `chargeType` - 通知类型（CHARGED=收费）
- `data.hisOrderId` - HIS处方ID（必填）
- `data.settleUserId` - 收费员ID
- `data.settleUserName` - 收费员姓名
- `data.settleUserTime` - 收费时间
- `data.patientId` - HIS患者档案号

---

## Jarvis接口入参（固定格式）

```json
{
  "presId": "35857670"
}
```

**字段说明**：

| 字段 | 说明 | 必填 |
|------|------|------|
| presId | HIS处方ID | 是 |

---

## Jarvis接口出参（固定格式）

```json
{
  "code": "200",
  "message": "成功"
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| code | 状态码，200成功 |
| message | 响应消息 |

---

## HIS期望响应

```json
{
  "errorMessage": "成功",
  "returnCode": "1"
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| returnCode | 状态码，1成功，0失败 |
| errorMessage | 响应消息 |

---

## 映射配置示例

> **重要说明**：Jarvis接口的入参、出参格式是固定的，不可更改。需根据HIS实际推送的字段进行前置映射配置。

### 前置处理映射（HIS → Jarvis）

| HIS字段 | 源参数类型 | Jarvis字段 | 目标参数类型 | 映射类型 | 映射规则 |
|---------|-----------|-------------|-------------|----------|----------|
| data | OBJECT | presId | STRING | EXPRESSION | `#data[data][hisOrderId]` |

### 后置处理映射（Jarvis → HIS）

| Jarvis字段 | 源参数类型 | HIS字段 | 目标参数类型 | 映射类型 | 映射数据源 | 映射规则 |
|-----------|-----------|---------|-------------|----------|-----------|----------|
| code | STRING | returnCode | STRING | EXPRESSION | RESPONSE | `#data == '200' ? '1' : '0'` |
| message | STRING | errorMessage | STRING | NAME | RESPONSE | - |

---

## AI配置步骤

### 步骤1：明确数据流向

**关键认知**：此接口与其他接口方向相反

- 其他接口：Jarvis调用HIS（Jarvis → HIS → Jarvis）
- 此接口：HIS推送Jarvis（HIS → Jarvis → HIS）

### 步骤2：获取HIS推送格式

询问客户提供HIS推送通知的数据格式，或明确以下信息：

**必须信息**：
1. HIS推送的入参字段及格式（包含chargeType、data结构）
2. HIS期望的响应字段及格式
3. 通知类型的取值含义（CHARGED、REFUNDED等）

### 步骤3：生成前置映射（HIS → Jarvis）

参考上述前置处理映射表

**注意**：
- Jarvis入参格式固定，只能从HIS推送数据中提取对应字段
- 使用EXPRESSION从嵌套对象中提取字段

### 步骤4：生成后置映射（Jarvis → HIS）

参考上述后置处理映射表

**注意**：
- Jarvis出参格式固定

