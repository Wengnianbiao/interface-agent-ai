---
trigger: model_decision
description: 
---
# 账单删除接口配置指南

> **业务专用指南**：提供账单删除（退费）场景的完整配置示例和步骤

---

## 目的

将Jarvis的账单删除（退费）操作同步至HIS系统，删除是指还未收费的账单，确保HIS侧账单数据与Jarvis保持一致。

---

## 场景识别

当客户提到「删除账单」「退费」「取消收费」「账单作废」时，明确为账单删除场景。

---

## 业务要点

### 1. 节点关键字配置

**keywordField**：`patientInfo.patientCode`

用于日志检索和问题排查，框架会从Jarvis入参中提取此字段值作为业务关键字记录到调用日志中。

**配置位置**：节点配置的 `keywordField` 字段

### 2. 删除标识字段

账单删除接口通常需要传递：

| 字段 | 来源 | 说明 |
|------|------|------|
| hisOrderId | `chagPatientSheet.presId` | HIS处方ID/订单号 |
| patientId | `patientInfo.hisPatientId` | HIS患者档案号 |
| operatorId | `doctorInfo.number` | 操作员编号 |
| operatorName | `doctorInfo.userName` | 操作员姓名 |

### 3. 嵌套字段提取

Jarvis入参中关键字段在嵌套对象内，需用EXPRESSION提取：

| 目标 | 来源 | 映射规则 |
|------|------|----------|
| hisOrderId | `chagPatientSheet.presId` | `#data[chagPatientSheet][presId]` |
| patientId | `patientInfo.hisPatientId` | `#data[patientInfo][hisPatientId]` |
| operatorId | `doctorInfo.number` | `#data[number]` |
| operatorName | `doctorInfo.userName` | `#data[userName]` |

---

## Jarvis入参

```json
{
  "chargeMode": "cash",
  "doctorInfo": {
    "idUser": 22,
    "userName": "信息科(勿删)",
    "number": "xxk"
  },
  "patientInfo": {
    "sex": "1",
    "age": 29,
    "marriage": "3",
    "identitycard": "412723199609114238",
    "cardType": "1",
    "patientLevelName": "普通体检人",
    "phone": "15839464947",
    "birthday": "1996-09-11",
    "address": "河南",
    "patientName": "王金辉",
    "patientCode": "2512240004",
    "hisPatientId": "4729293",
    "visitNo": "2100640056",
    "userType": 0,
    "orgName": "",
    "registertime": "2025-12-24 10:22:24",
    "physicalTypes": "physical:types:A",
    "physicalTypeName": "健康体检",
    "nation": "01",
    "nationName": "汉族"
  },
  "chagPatientSheet": {
    "presId": "31628557",
    "idPatientSheet": 2765,
    "settlementOrderNo": "2765",
    "sumAmount": 34,
    "idChagSync": 3073,
    "sumAmountYuan": 0.34
  },
  "chagPatientSheetDetail": [
    {
      "idPatientFeeItem": 47912,
      "factPrice": 12,
      "factPriceYuan": 0.12,
      "dfiInterfaceCode1": "07218486",
      "dfiInterfaceCode4": "5079",
      "interfaceCode": "07218486",
      "feeItemName": "尿常规",
      "idPatientSheetDetail": 55594,
      "idPatientSheet": 2765,
      "departName": "检验科",
      "departCode": "2027",
      "departType": "LIS",
      "settlementOrderNo": "2765",
      "presId": "31628557",
      "applyId": "80000047912",
      "barCode": "8030301177",
      "consumeList": [
        {
          "dciName": "尿常规",
          "consumeItemCode": "07218486",
          "idConsumeItem": 510194,
          "factPrice": "12.00",
          "price": "1800.00",
          "priceYuan": 18,
          "idPatientFeeItem": "47912",
          "interfaceCode": "07218486",
          "quantity": 1,
          "factPriceYuan": 0.12
        }
      ]
    },
    {
      "idPatientFeeItem": 47911,
      "factPrice": 4,
      "factPriceYuan": 0.04,
      "dfiInterfaceCode1": "07214911",
      "dfiInterfaceCode4": "4911",
      "interfaceCode": "07214911",
      "feeItemName": "空腹血糖",
      "idPatientSheetDetail": 55593,
      "idPatientSheet": 2765,
      "departName": "检验科",
      "departCode": "2027",
      "departType": "LIS",
      "settlementOrderNo": "2765",
      "presId": "31628557",
      "applyId": "80000047911",
      "barCode": "8030301180",
      "consumeList": [
        {
          "dciName": "空腹血糖",
          "idConsumeItem": 510186,
          "factPrice": "4.00",
          "price": "600.00",
          "priceYuan": 6,
          "idPatientFeeItem": "47911",
          "quantity": 1,
          "factPriceYuan": 0.04
        }
      ]
    }
  ]
}
```

**关键字段**：
- `patientInfo.patientCode` - keywordField，体检编号
- `chagPatientSheet.presId` - HIS处方ID（必填）
- `patientInfo.hisPatientId` - HIS患者档案号（必填）
- `doctorInfo.number` - 操作员编号
- `doctorInfo.userName` - 操作员姓名
- `chagPatientSheetDetail` - 账单明细（包含退费项目信息）

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
  "hisOrderId": "31628557",
  "patientId": "4729293",
  "operatorId": "xxk",
  "operatorName": "信息科(勿删)"
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
| chagPatientSheet | OBJECT | hisOrderId | STRING | EXPRESSION | `#data[presId]` |
| patientInfo | OBJECT | patientId | STRING | EXPRESSION | `#data[hisPatientId]` |
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
1. HIS删除账单接口的入参字段及格式
2. HIS删除账单接口的响应字段及格式

### 步骤2：生成前置映射（Jarvis → HIS）

参考上述前置处理映射表

### 步骤3：生成后置映射（HIS → Jarvis）

参考上述后置处理映射表
