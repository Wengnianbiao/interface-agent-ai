---
trigger: model_decision
description: 
---
# 账单创建接口配置指南

> **业务专用指南**：提供账单创建（开单、收费推送）场景的完整配置示例和步骤

---

## 目的

将Jarvis的收费账单推送至HIS系统，完成患者收费流程，获取HIS返回的账单ID和明细ID，用于后续业务流程。

---

## 场景识别

当客户提到「创建账单」「推送收费」「开单接口」「账单推送」时，明确为账单创建场景。

---

## 业务要点

### 1. 账单模式差异

不同HIS厂商账单设计不同，AI需根据HIS接口文档判断模式：

| 模式 | 说明 | Jarvis字段 | 判断依据 |
|------|------|------------|----------|
| **总价模式** | HIS只需账单总金额 | `chagPatientSheet.sumAmount` | HIS入参只有总金额字段，无明细数组 |
| **明细模式** | HIS需要收费项列表 | `chagPatientSheetDetail` | HIS入参有明细数组，但明细中无物价子数组 |
| **物价模式** | HIS需要到物价级别 | `chagPatientSheetDetail` + `consumeList` | HIS明细中有物价子数组 |

### 2. 节点关键字配置

**keywordField**：`patientInfo.patientCode`

用于日志检索和问题排查，框架会从Jarvis入参中提取此字段值作为业务关键字记录到调用日志中。

**配置位置**：节点配置的 `keywordField` 字段

### 3. 幂等控制字段（必须关注）

**关键字段**：`chagPatientSheet.idChagSync`

**作用**：Jarvis生成的账单版本号，HIS需存储并做幂等判断。

**AI处理**：
1. 检查HIS入参是否有幂等ID字段（如 `orderId`、`billNo`、`syncId`）
2. 有 → 将 `idChagSync` 映射到该字段
3. 没有 → **必须提示客户**确认HIS是否支持幂等控制

### 4. 常见字段转换

账单接口常见的值转换场景：

| 字段 | Jarvis值 | HIS可能要求 | 转换示例 |
|------|----------|-------------|----------|
| 性别 | "1"/"2" | "男"/"女" | `#data == '1' ? '男' : '女'` |
| 金额单位 | 分(sumAmount) | 元 | 使用 `sumAmountYuan` 或 `#data / 100` |
| 金额单位 | 元(sumAmountYuan) | 分 | 使用 `sumAmount` 或 `#data * 100` |
| 状态码 | "1" | "200" | `#data == "1" ? "200" : "-1"` |

### 5. 嵌套字段提取

Jarvis入参中部分字段在嵌套对象内，需用EXPRESSION提取：

| 目标 | 来源 | 映射规则 |
|------|------|----------|
| 患者ID | `patientInfo.hisPatientId` | `#data['hisPatientId']` |
| 就诊号 | `patientInfo.visitNo` | `#data['visitNo']` |
| 患者姓名 | `patientInfo.patientName` | `#data['patientName']` |
| 操作员ID | `doctorInfo.number` | `#data['number']` |
| 操作员姓名 | `doctorInfo.userName` | `#data['userName']` |

### 6. 数组映射配置要点

#### 前置数组映射（Jarvis → HIS）

**一级数组映射**：`chagPatientSheetDetail` → HIS明细数组
- 映射类型：`OBJECT`
- 配置 `childParam` 进行子项字段映射
- 示例：`chagPatientSheetDetail` → `orderDetails`

**二级数组映射**：`consumeList` → HIS物价数组（嵌套在明细内）
- 父节点：明细数组的 `consumeList` 字段
- 映射类型：`OBJECT`
- 再次配置 `childParam` 进行物价子项映射
- 示例：`consumeList` → `itemList`

#### 后置数组映射（HIS → Jarvis）

**数据源选择**：
- 后置处理可从 `INPUT`（原始Jarvis入参）或 `RESPONSE`（HIS响应）取值
- 数组映射中，父节点确定数据源后，子节点只能在该数据源下映射
- 示例：`hisItems` 需要关联 INPUT 的 `idPatientFeeItem` 和 RESPONSE 的 `hisDetailId`

**关联字段映射**：
- HIS返回的明细ID数组需映射到 `rsp.hisItems`
- 关键：通过 `idPatientFeeItem` 关联原始明细
- 确保数组元素顺序对应或使用ID关联

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
    "age": 35,
    "marriage": "3",
    "identitycard": "110107199001018138",
    "cardType": "1",
    "patientLevelName": "普通体检人",
    "phone": "17826809454",
    "birthday": "1990-01-01",
    "patientName": "测试账号",
    "patientCode": "102509080001",
    "hisPatientId": "030001375",
    "visitNo": "20250908000204",
    "userType": 0,
    "orgName": "",
    "registertime": "2025-09-08 10:17:52",
    "physicalTypes": "physical:types:A",
    "physicalTypeName": "健康体检"
  },
  "chagPatientSheet": {
    "idPatientSheet": 2484,
    "idChagSync": "幂等ID",
    "settlementOrderNo": "2484",
    "sumAmount": 17000,
    "sumAmountYuan": 170
  },
  "chagPatientSheetDetail": [
    {
      "idPatientFeeItem": 45857,
      "price": 8000,
      "factPrice": 8000,
      "discount": "1",
      "factPriceYuan": 80,
      "dfiInterfaceCodeName1": "收费编码",
      "dfiInterfaceCodeName2": "医技对照编码",
      "dfiInterfaceCodeName6": "条码数量",
      "feeItemName": "B超(肾输尿管膜胱)",
      "idPatientSheetDetail": 51364,
      "idPatientSheet": 2484,
      "departName": "彩超",
      "ddInterfaceCodeName1": "科室外部编码",
      "departCode": "5",
      "departType": "PACS",
      "idFeeItem": 8353,
      "settlementOrderNo": "2484",
      "resent": 0,
      "realRefund": 0,
      "consumeList": [
        {
          "dciName": "B超(肾输尿管膜胱)",
          "idConsumeItem": 510098,
          "factPrice": "8000.00",
          "price": "8000.00",
          "priceYuan": 80,
          "idPatientFeeItem": "45857",
          "quantity": 1,
          "factPriceYuan": 80
        }
      ]
    },
    {
      "idPatientFeeItem": 45856,
      "price": 9000,
      "factPrice": 9000,
      "discount": "1",
      "factPriceYuan": 90,
      "dfiInterfaceCodeName1": "收费编码",
      "dfiInterfaceCodeName2": "医技对照编码",
      "dfiInterfaceCodeName6": "条码数量",
      "feeItemName": "颈椎正侧位片(DR)",
      "idPatientSheetDetail": 51363,
      "idPatientSheet": 2484,
      "departName": "DR",
      "ddInterfaceCodeName1": "科室外部编码",
      "departCode": "137",
      "departType": "PACS",
      "idFeeItem": 8334,
      "settlementOrderNo": "2484",
      "resent": 0,
      "realRefund": 0,
      "consumeList": [
        {
          "dciName": "颈椎正侧位片(DR)",
          "idConsumeItem": 510079,
          "factPrice": "9000.00",
          "price": "9000.00",
          "priceYuan": 90,
          "idPatientFeeItem": "45856",
          "quantity": 1,
          "factPriceYuan": 90
        }
      ]
    }
  ]
}
```

**关键字段**：
- `patientInfo.patientCode` - keywordField，体检号
- `patientInfo.hisPatientId` - HIS患者档案ID（必填）
- `patientInfo.patientName` - 患者姓名（必填）
- `chagPatientSheet.idChagSync` - 幂等ID（必须映射）
- `chagPatientSheet.sumAmount` - 账单总金额（分）
- `chagPatientSheet.sumAmountYuan` - 账单总金额（元）
- `chagPatientSheetDetail` - 明细数组（明细模式/物价模式需要）
- `consumeList` - 物价数组（物价模式需要）
- `doctorInfo.number` - 操作员编号（从嵌套对象提取）

---

## Jarvis出参

```json
{
  "code": "200",
  "message": "成功",
  "rsp": {
    "presId": "HIS账单ID",
    "hisItems": [
      {
        "idPatientFeeItem": "45857",
        "hisDetailId": "HIS明细ID_001"
      },
      {
        "idPatientFeeItem": "45858",
        "hisDetailId": "HIS明细ID_002"
      }
    ]
  }
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| code | 状态码，200成功 |
| message | 响应消息 |
| rsp.presId | HIS分配的账单ID |
| rsp.hisItems | HIS明细ID数组 |
| rsp.hisItems[].idPatientFeeItem | 体检明细ID（用于关联） |
| rsp.hisItems[].hisDetailId | HIS明细ID |

---

## 映射配置示例

> **重要说明**：以下示例仅用于说明映射配置方法，实际HIS接口的入参、出参字段必须以客户提供的接口文档或实际出入参为准。

### HIS入参示例

```json
{
  "patientId": "客户 ID",
  "clinicId": "门诊号",
  "patientCode": "体检编号",
  "orderId": "Jarvis账单 id",
  "name": "张三",
  "age": "28",
  "sex": "男",
  "orderType": "1",
  "sumAmount": "10000",
  "sumAmountYuan": "100",
  "operatorId": "操作员 ID",
  "orderDeptId": "开单部门 ID",
  "orderDetails": [
    {
      "orderDetailId": "Jarvis账单明细 ID",
      "itemName": "收费项名称",
      "itemId": "收费项 id",
      "itemPrice": "价格",
      "itemFactPrice": "收费金额,单位元",
      "itemDiscount": "收费项折扣",
      "itemDepartCode": "收费项所属科室 id",
      "consumeList": [
        {
          "consumeId": "物价 id",
          "quantity": "物价数量",
          "factPrice": "物价价格， 分",
          "factPriceYuan": "物价价格， 元"
        }
      ]
    }
  ]
}
```

### HIS响应示例

```json
{
  "returnCode": "1",
  "errorMessage": "成功",
  "data": {
    "hisOrderId": "",
    "orderId": "",
    "hisOrderDetails": [
      {
        "hisOrderDetailId": "",
        "orderDetailId": ""
      },
      {
        "hisOrderDetailId": "",
        "orderDetailId": ""
      }
    ]
  }
}
```

### 前置处理映射（Jarvis → HIS）

| Jarvis字段 | 源参数类型 | HIS字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| patientInfo | OBJECT | patientId | STRING | EXPRESSION | `#data['hisPatientId']` |
| patientInfo | OBJECT | clinicId | STRING | EXPRESSION | `#data['visitNo']` |
| patientInfo | OBJECT | name | STRING | EXPRESSION | `#data['patientName']` |
| patientInfo | OBJECT | age | STRING | EXPRESSION | `#data['age']` |
| patientInfo | OBJECT | sex | STRING | EXPRESSION | `#data['sex']` |
| - | NONE | orderType | STRING | CONSTANT | `"1"` |
| chagPatientSheet | OBJECT | sumAmountYuan | STRING | EXPRESSION | `#data['sumAmountYuan']` |
| chagPatientSheet | OBJECT | orderId | STRING | EXPRESSION | `#data['idChagSync']` |
| doctorInfo | OBJECT | operatorId | STRING | EXPRESSION | `#data['number']` |
| - | NONE | orderDeptId | STRING | CONSTANT | `"21"` |
| chagPatientSheetDetail | ARRAY | orderDetails | ARRAY | NAME | 数组映射 |
| - | NONE | └─ orderDetailsNode | OBJECT | NAME | 虚拟节点 |
| └─ idPatientFeeItem | STRING |     └─ orderDetailId | STRING | NAME | - |
| └─ feeItemName | STRING |     └─ itemName | STRING | NAME | - |
| └─ dfiInterfaceCodeName1 | STRING |     └─ itemId | STRING | NAME | - |
| └─ factPriceYuan | STRING |     └─ itemFactPrice | STRING | NAME | - |
| └─ price | STRING |     └─ itemPrice | STRING | NAME | - |
| └─ departCode | STRING |     └─ itemDepartCode | STRING | NAME | - |
| └─ discount | STRING |     └─ itemDiscount | STRING | NAME | - |
| └─ consumeList | ARRAY |     └─ consumeList | ARRAY | NAME | 嵌套数组映射 |
| - | NONE |         └─ consumeListNode | OBJECT | NAME | 虚拟节点 |
|     └─ idConsumeItem | STRING |             └─ consumeId | STRING | NAME | - |
|     └─ quantity | STRING |             └─ quantity | STRING | NAME | - |
|     └─ factPriceYuan | STRING |             └─ factPriceYuan | STRING | NAME | - |

### 后置处理映射（HIS → Jarvis）

| HIS字段 | 源参数类型 | Jarvis字段 | 目标参数类型 | 映射类型 | 映射数据源 | 映射规则 |
|---------|-----------|-------------|-------------|----------|-----------|----------|
| returnCode | STRING | code | STRING | EXPRESSION | RESPONSE | `#data == "1" ? "200" : "-1"` |
| errorMessage | STRING | message | STRING | NAME | RESPONSE | - |
| data | OBJECT | rsp | OBJECT | NAME | RESPONSE | 嵌套映射 |
| └─ hisOrderId | STRING | └─ presId | STRING | NAME | RESPONSE | - |
| └─ hisOrderDetails | ARRAY | └─ hisItems | ARRAY | NAME | RESPONSE | 数组映射 |
| - | NONE |     └─ hisItemsNode | OBJECT | NAME | RESPONSE | 虚拟节点 |
|     └─ orderDetailId | STRING |         └─ idPatientFeeItem | STRING | NAME | RESPONSE | - |
|     └─ hisOrderDetailId | STRING |         └─ hisDetailId | STRING | NAME | RESPONSE | - |

---

## AI配置步骤

### 步骤1：获取HIS接口信息

询问客户提供HIS接口文档，或明确以下信息：

**必须信息**：
1. HIS创建账单接口的入参字段及格式
2. HIS创建账单接口的响应字段及格式
3. 账单模式（总价/明细/物价）
4. 是否有幂等ID字段

### 步骤2：生成前置映射（Jarvis → HIS）

参考上述前置处理映射表

### 步骤3：生成后置映射（HIS → Jarvis）

参考上述后置处理映射表
