---
trigger: model_decision
description: 
---
# 取消拟退账单接口配置指南

> **业务专用指南**：提供取消拟退账单场景的完整配置示例和步骤

---

## 目的

将Jarvis的取消拟退操作同步至HIS系统，撤销之前的拟退申请，恢复账单正常状态。

---

## 场景识别

当客户提到「取消拟退」「撤销退费申请」「拟退取消」「退费驳回」时，明确为取消拟退账单场景。

---

## 业务要点

### 1. 节点关键字配置

**keywordField**：`patientInfo.patientCode`

用于日志检索和问题排查，框架会从Jarvis入参中提取此字段值作为业务关键字记录到调用日志中。

**配置位置**：节点配置的 `keywordField` 字段

### 2. 取消拟退标识字段

取消拟退接口通常需要传递：

| 字段 | 来源 | 说明 |
|------|------|------|
| patientId | `patientInfo.hisPatientId` | HIS患者档案号 |
| hisOrderIds | `chagPatientSheetList[].presId` | HIS处方ID数组（支持批量取消） |
| operatorId | `doctorInfo.number` | 操作员编号 |
| operatorName | `doctorInfo.userName` | 操作员姓名 |

### 3. 数组映射配置要点

**一级数组映射**：`chagPatientSheetList` → `hisOrderIds`

- **虚拟节点必须配置**：数组映射需配置虚拟节点 `hisOrderIdNode`
- **数组元素提取**：从 `presId` 提取到 `hisOrderId`
- **映射结构**：
  ```
  chagPatientSheetList (ARRAY)
    └─ hisOrderIdNode (虚拟节点, OBJECT)
        └─ presId → hisOrderId (STRING)
  ```

### 4. 嵌套字段提取

Jarvis入参中关键字段在嵌套对象内，需用EXPRESSION提取：

| 目标 | 来源 | 映射规则 |
|------|------|----------|
| patientId | `patientInfo.hisPatientId` | `#data[patientInfo][hisPatientId]` |
| operatorId | `doctorInfo.number` | `#data[number]` |
| operatorName | `doctorInfo.userName` | `#data[userName]` |

---

## Jarvis入参

```json
{
  "chargeMode": "cash",
  "doctorInfo": {
    "idUser": 748,
    "userName": "朱娜",
    "number": "0000442"
  },
  "patientInfo": {
    "sex": "1",
    "age": 29,
    "marriage": "3",
    "identitycard": "330303199601231211",
    "cardType": "1",
    "patientLevelName": "普通体检人",
    "phone": "13212515632",
    "birthday": "1996-01-23",
    "address": "浙江省温州市龙湾区永中街道横浃后岸路３号",
    "patientName": "林俊涵",
    "patientCode": "82601060003",
    "hisPatientId": "4517155",
    "visitNo": "2100428187",
    "userType": 0,
    "orgName": "",
    "registertime": "2026-01-06 10:19:52",
    "physicalTypes": "physical:types:A",
    "physicalTypeName": "健康体检",
    "nation": "01",
    "nationName": "汉族"
  },
  "chagPatientSheet": {
    "presId": "35790568",
    "idPatientSheet": 2846,
    "settlementOrderNo": "2846",
    "sumAmount": 2,
    "originalPayAmount": 2,
    "originalPayAmountYuan": 0.02,
    "refundChagId": 2847,
    "idChagSync": 3116,
    "sumAmountYuan": 0.02
  },
  "chagPatientSheetList": [
    {
      "presId": "35790568",
      "idPatientSheet": 2846,
      "settlementOrderNo": "2846",
      "sumAmount": 2,
      "originalPayAmount": 2,
      "originalPayAmountYuan": 0.02,
      "refundChagId": 2847,
      "idChagSync": 3116,
      "sumAmountYuan": 0.02
    }
  ],
  "chagPatientSheetDetail": [
    {
      "idPatientFeeItem": 49498,
      "price": -13900,
      "factPrice": -1,
      "discount": "7.20000000000000018e-05",
      "factPriceYuan": -0.01,
      "dfiInterfaceCode1": "20401",
      "dfiInterfaceCode7": "2817",
      "interfaceCode": "20401",
      "feeItemName": "胸部CT",
      "idPatientSheetDetail": 57214,
      "idPatientSheet": 2847,
      "departName": "CT",
      "departCode": "2001",
      "departType": "PACS",
      "presId": "35790568",
      "resent": 0,
      "realRefund": 1,
      "firstPresId": "35790419",
      "applyId": "80010049498",
      "barCode": "8031361178",
      "consumeList": [
        {
          "dciName": "胸部CT",
          "consumeItemCode": "20401",
          "idConsumeItem": 510152,
          "factPrice": "1.00",
          "price": "13900.00",
          "priceYuan": 139,
          "idPatientFeeItem": "49498",
          "interfaceCode": "20401",
          "quantity": 1,
          "factPriceYuan": 0.01
        }
      ]
    },
    {
      "idPatientFeeItem": 49501,
      "price": -23900,
      "factPrice": -1,
      "discount": "4.19999999999999977e-05",
      "factPriceYuan": -0.01,
      "dfiInterfaceCode7": "5021",
      "feeItemName": "智能高血压分型检测",
      "idPatientSheetDetail": 57225,
      "idPatientSheet": 2847,
      "departName": "血动图",
      "departType": "OTHER",
      "presId": "35790568",
      "resent": 0,
      "realRefund": 0,
      "firstPresId": "35790419",
      "applyId": "80000049501",
      "consumeList": [
        {
          "dciName": "智能高血压分型检测",
          "idConsumeItem": 510400,
          "factPrice": "1.00",
          "price": "23900.00",
          "priceYuan": 239,
          "idPatientFeeItem": "49501",
          "quantity": 1,
          "factPriceYuan": 0.01
        }
      ]
    }
  ]
}
```

**关键字段**：
- `patientInfo.patientCode` - keywordField，体检编号
- `chagPatientSheetList` - 待取消拟退账单列表（数组，支持批量）
- `chagPatientSheetList[].presId` - HIS处方ID（取消拟退标识）
- `patientInfo.hisPatientId` - HIS患者档案号（必填）
- `doctorInfo.number` - 操作员编号
- `doctorInfo.userName` - 操作员姓名
- `chagPatientSheetDetail` - 拟退项目明细

---

## Jarvis出参

```json
{
  "code": "200",
  "message": "成功!"
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| code | 状态码，200成功 |
| message | 响应消息 |

---

## 映射配置示例

> **重要说明**：以下示例仅用于说明映射配置方法，实际HIS接口的入参、出参字段必须以客户提供的接口文档或实际出入参为准。

### HIS入参示例

```json
{
  "patientId": "4517155",
  "hisOrderIds": [
    "35790568"
  ],
  "operatorId": "0000442",
  "operatorName": "朱娜"
}
```

### HIS响应示例

```json
{
  "returnCode": "1",
  "errorMessage": "成功!"
}
```

### 前置处理映射（Jarvis → HIS）

| Jarvis字段 | 源参数类型 | HIS字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| patientInfo | OBJECT | patientId | STRING | EXPRESSION | `#data[hisPatientId]` |
| chagPatientSheetList | ARRAY | hisOrderIds | ARRAY | NAME | 数组映射 |
| - | NONE | └─ hisOrderIdNode | OBJECT | NAME | 虚拟节点 |
| └─ presId | STRING |     └─ hisOrderId | STRING | NAME | - |
| doctorInfo | OBJECT | operatorId | STRING | EXPRESSION | `#data[number]` |
| doctorInfo | OBJECT | operatorName | STRING | EXPRESSION | `#data[userName]` |

### 后置处理映射（HIS → Jarvis）

| HIS字段 | 源参数类型 | Jarvis字段 | 目标参数类型 | 映射类型 | 映射数据源 | 映射规则 |
|---------|-----------|-------------|-------------|----------|-----------|----------|
| returnCode | STRING | code | STRING | EXPRESSION | RESPONSE | `#data == "1" ? "200" : "-1"` |
| errorMessage | STRING | message | STRING | NAME | RESPONSE | - |

---

## AI配置步骤

### 步骤1：获取HIS接口信息

询问客户提供HIS接口文档，或明确以下信息：

**必须信息**：
1. HIS取消拟退账单接口的入参字段及格式
2. HIS取消拟退账单接口的响应字段及格式
3. 是否支持批量取消（单个处方ID还是数组）

### 步骤2：生成前置映射（Jarvis → HIS）

参考上述前置处理映射表

**注意**：数组映射必须配置虚拟节点

### 步骤3：生成后置映射（HIS → Jarvis）

参考上述后置处理映射表
