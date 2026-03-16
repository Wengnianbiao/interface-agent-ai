---
trigger: model_decision
description: 
---
# 报告状态推送接口配置指南

> **业务专用指南**：提供三方系统主动推送报告状态场景的完整配置示例和步骤

---

## 目的

接收三方系统（PACS/LIS等）主动推送的检查/检验报告状态，更新Jarvis的报告状态。

---

## 场景识别

当客户提到「报告状态推送」「报告状态回调」「PACS推送报告状态」「LIS推送报告状态」「报告状态通知」时，明确为报告状态推送场景。

---

## 业务要点

### 1. 数据流向（重要）

**与主动查询接口不同**：此接口是 **三方 → Jarvis** 的推送场景

- **上游接口**：三方系统（PACS/LIS等，主动推送方）
- **下游接口**：Jarvis接口（被动接收方）
- **Jarvis入参格式固定**：不可更改
- **Jarvis出参格式固定**：不可更改

### 2. 关键字段说明

**serviceProviderType**：厂商类型（PACS/LIS等）

**paramType**：指定使用哪个字段进行匹配（3选1）

| paramType | 对应字段 | 说明 | 常用场景 |
|-----------|---------|------|----------|
| 1 | outFeeItemId | 使用收费项外部编码匹配 | 特定场景 |
| 2 | applyNo | 使用申请单号匹配 | **PACS常用** |
| 3 | barCode | 使用条码号匹配 | **LIS常用** |

**业务差异说明**：
- **PACS系统**：通常使用申请单号（applyNo）作为主要标识，paramType=2
- **LIS系统**：通常优先使用条码号（barCode）作为主要标识，paramType=3

**state**：报告状态值

| state | 说明 |
|-------|------|
| 0 | 已采样（或已上机） |
| 1 | 已审核 |
| 2 | 取消采样 |
| 3 | 取消审核 |
| 99 | 特殊状态（不修改is_liststate） |

**支持的三种匹配方式**：
- **方式1**：通过收费项外部编码（outFeeItemId）匹配 - 特定场景使用
- **方式2**：通过申请单号（applyNo）匹配 - **PACS系统常用**
- **方式3**：通过条码号（barCode）匹配 - **LIS系统常用**

### 3. 前置处理映射（三方 → Jarvis）

从三方推送数据中转换字段：

| 三方字段 | Jarvis字段 | 说明 |
|---------|-----------|------|
| serviceProviderType | serviceProviderType | 厂商类型（PACS/LIS等） |
| patientCode | patientCode | 患者编号 |
| sourceId/applyNo/barCode | outFeeItemId/applyNo/barCode | 根据三方推送的字段决定 |
| status | state | 报告状态（需转换） |
| - | paramType | 根据使用的匹配字段设置（1/2/3） |

### 4. 状态转换示例

**重要**：state的具体值需要根据三方的业务状态进行转换。以下是常见的转换场景：

**场景1：三方推送采样状态**

| 三方状态 | Jarvis state | 说明 |
|---------|-------------|------|
| SAMPLED | 0 | 已采样（或已上机） |
| SAMPLE_CANCELLED | 2 | 取消采样 |

**场景2：三方推送审核状态**

| 三方状态 | Jarvis state | 说明 |
|---------|-------------|------|
| REPORTED/AUDITED | 1 | 已审核 |
| AUDIT_CANCELLED | 3 | 取消审核 |

**场景3：三方推送特殊状态**

| 三方状态 | Jarvis state | 说明 |
|---------|-------------|------|
| SPECIAL_STATE | 99 | 特殊状态（不修改is_liststate） |

### 5. 后置处理映射（Jarvis → 三方）

将Jarvis响应转换为三方期望的格式：

| Jarvis字段 | 三方字段 | 转换规则 |
|-----------|---------|----------|
| code | returnCode | `#data == '200' ? '1' : '0'` |
| message | errorMessage | 直接映射 |

---

## 三方推送入参示例

**示例1：PACS通过申请单号推送（最常见）**

```json
{
  "serviceProviderType": "PACS",
  "patientCode": "26011300006",
  "applyNo": "DJ20260113170908000006",
  "status": "AUDITED"
}
```

**示例2：LIS通过条码号推送（最常见）**

```json
{
  "serviceProviderType": "LIS",
  "patientCode": "26011300006",
  "barCode": "BC202601130001",
  "status": "SAMPLED"
}
```

**示例3：通过收费项外部编码推送**

```json
{
  "serviceProviderType": "PACS",
  "patientCode": "26011300006",
  "outFeeItemId": "CT001",
  "status": "REPORTED"
}
```

**关键字段**：
- `serviceProviderType` - 厂商类型（PACS/LIS等）
- `patientCode` - 患者编号
- `applyNo` - 申请单号（三选一）
- `barCode` - 条码号（三选一）
- `outFeeItemId` - 收费项外部编码（三选一）
- `status` - 报告状态（需要转换为Jarvis的state值）

---

## Jarvis接口入参（固定格式）

**示例1：PACS通过申请单号匹配**

```json
[
  {
    "serviceProviderType": "PACS",
    "patientCode": "26011300006",
    "applyNo": "DJ20260113170908000006",
    "paramType": 2,
    "state": 1
  }
]
```

**示例2：LIS通过条码号匹配**

```json
[
  {
    "serviceProviderType": "LIS",
    "patientCode": "26011300006",
    "barCode": "BC202601130001",
    "paramType": 3,
    "state": 0
  }
]
```

**示例3：通过收费项外部编码匹配**

```json
[
  {
    "serviceProviderType": "PACS",
    "patientCode": "26011300006",
    "outFeeItemId": "CT001",
    "paramType": 1,
    "state": 1
  }
]
```

**字段说明**：

| 字段 | 说明 | 必填 | 备注 |
|------|------|------|------|
| serviceProviderType | 厂商类型 | 是 | PACS/LIS等 |
| patientCode | 患者编号 | 是 | - |
| outFeeItemId | 收费项外部编码 | 3选1 | paramType=1时使用 |
| applyNo | 申请单号 | 3选1 | paramType=2时使用 |
| barCode | 条码号 | 3选1 | paramType=3时使用 |
| paramType | 匹配字段类型 | 是 | 1=outFeeItemId, 2=applyNo, 3=barCode |
| state | 报告状态 | 是 | 0=已采样, 1=已审核, 2=取消采样, 3=取消审核, 99=特殊状态 |

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

## 三方期望响应

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

> **重要说明**：Jarvis接口的入参、出参格式是固定的，不可更改。需根据三方实际推送的字段进行前置映射配置。

### 前置处理映射（三方 → Jarvis）

**情况1：PACS通过申请单号推送状态（最常见）**

| 三方字段 | 源参数类型 | Jarvis字段 | 目标参数类型 | 映射类型 | 映射规则 |
|---------|-----------|-------------|-------------|----------|----------|
| serviceProviderType | STRING | [0].serviceProviderType | STRING | NAME | - |
| patientCode | STRING | [0].patientCode | STRING | NAME | - |
| applyNo | STRING | [0].applyNo | STRING | NAME | - |
| - | NONE | [0].paramType | INTEGER | CONSTANT | `2` |
| status | STRING | [0].state | INTEGER | EXPRESSION | 根据业务转换（见下方） |

**情况2：LIS通过条码号推送状态（最常见）**

| 三方字段 | 源参数类型 | Jarvis字段 | 目标参数类型 | 映射类型 | 映射规则 |
|---------|-----------|-------------|-------------|----------|----------|
| serviceProviderType | STRING | [0].serviceProviderType | STRING | NAME | - |
| patientCode | STRING | [0].patientCode | STRING | NAME | - |
| barCode | STRING | [0].barCode | STRING | NAME | - |
| - | NONE | [0].paramType | INTEGER | CONSTANT | `3` |
| status | STRING | [0].state | INTEGER | EXPRESSION | 根据业务转换（见下方） |

**情况3：通过收费项外部编码推送状态**

| 三方字段 | 源参数类型 | Jarvis字段 | 目标参数类型 | 映射类型 | 映射规则 |
|---------|-----------|-------------|-------------|----------|----------|
| serviceProviderType | STRING | [0].serviceProviderType | STRING | NAME | - |
| patientCode | STRING | [0].patientCode | STRING | NAME | - |
| outFeeItemId | STRING | [0].outFeeItemId | STRING | NAME | - |
| - | NONE | [0].paramType | INTEGER | CONSTANT | `1` |
| status | STRING | [0].state | INTEGER | EXPRESSION | 根据业务转换（见下方） |

**状态转换表达式示例**（根据三方实际状态值调整）：

```javascript
// 示例1：三方使用SAMPLED/AUDITED等状态
#data == 'SAMPLED' ? 0 : (#data == 'AUDITED' ? 1 : (#data == 'SAMPLE_CANCELLED' ? 2 : (#data == 'AUDIT_CANCELLED' ? 3 : 99)))

// 示例2：三方使用数字状态码
#data == '10' ? 0 : (#data == '20' ? 1 : (#data == '30' ? 2 : (#data == '40' ? 3 : 99)))

// 示例3：三方直接使用Jarvis的state值
#data  // 直接使用（如果三方状态码与Jarvis一致）
```

### 后置处理映射（Jarvis → 三方）

| Jarvis字段 | 源参数类型 | 三方字段 | 目标参数类型 | 映射类型 | 映射数据源 | 映射规则 |
|-----------|-----------|---------|-------------|----------|-----------|----------|
| code | STRING | returnCode | STRING | EXPRESSION | RESPONSE | `#data == '200' ? '1' : '0'` |
| message | STRING | errorMessage | STRING | NAME | RESPONSE | - |

---

## AI配置步骤

### 步骤1：明确数据流向

**关键认知**：此接口与主动查询接口方向相反

- 主动查询接口：Jarvis查询三方（Jarvis → 三方 → Jarvis）
- 此接口：三方推送Jarvis（三方 → Jarvis → 三方）

### 步骤2：获取三方推送格式

询问客户提供三方推送通知的数据格式，或明确以下信息：

**必须信息**：
1. 三方推送的入参字段及格式（包含报告状态字段）
2. 三方期望的响应字段及格式
3. 报告状态的取值含义和枚举值

### 步骤3：确定匹配字段和状态格式

**匹配字段**（3选1）：
- **申请单号**（applyNo）- **PACS系统常用**，适用于影像检查
- **条码号**（barCode）- **LIS系统常用**，适用于检验项目
- **收费项外部编码**（outFeeItemId）- 特定场景使用

**业务建议**：
- PACS系统推荐使用申请单号（paramType=2）
- LIS系统推荐使用条码号（paramType=3）
- 根据三方系统实际推送的字段选择合适的匹配方式

**状态字段**：
- 确认三方推送的状态字段名称（如status、state、reportStatus等）
- 确认状态值的含义（如SAMPLED、AUDITED等）
- 建立三方状态值到Jarvis state的映射关系

### 步骤4：生成前置映射（三方 → Jarvis）

参考上述前置处理映射表

**关键配置**：

1. **确定paramType的值**：
   - 如果三方推送applyNo，设置paramType=2
   - 如果三方推送barCode，设置paramType=3
   - 如果三方推送outFeeItemId，设置paramType=1

2. **配置state转换表达式**：
   - 根据三方的状态值建立映射关系
   - 0=已采样（或已上机）
   - 1=已审核
   - 2=取消采样
   - 3=取消审核
   - 99=特殊状态（不修改is_liststate）

3. **数组格式**：
   - Jarvis入参为数组格式，映射时使用 `[0].字段名`
   - 如果三方支持批量推送，需要配置数组映射

### 步骤5：生成后置映射（Jarvis → 三方）

参考上述后置处理映射表

**注意**：
- Jarvis出参格式固定
- 返回码需要根据三方期望格式进行转换
