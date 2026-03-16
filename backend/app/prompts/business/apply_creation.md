---
trigger: model_decision
description: 
---
# 申请单同步接口配置指南

> **业务专用指南**：提供申请单同步（PACS、LIS申请单推送）场景的完整配置示例和步骤

---

## 目的

将Jarvis的检查检验申请单推送至三方系统（PACS、LIS等），完成申请单创建，获取三方系统返回的申请单号，用于后续报告回传流程。

---

## 场景识别

当客户提到「申请单推送」「PACS申请」「LIS申请」「检查申请」「检验申请」时，明确为申请单同步场景。

---

## 业务要点

### 1. 申请单拆分逻辑 ⚠️

不同三方系统对批量申请单的支持不同，AI需根据三方接口文档判断模式：

| 模式 | 说明 | Jarvis字段 | 判断依据 |
|------|------|------------|----------|
| **批量模式** | 三方接口支持一次性创建多个申请单 | `items`（ARRAY） | 三方入参中申请单字段为数组 |
| **拆分模式** | 三方接口仅支持单个申请单创建 | `items`（OBJECT） | 三方入参中申请单字段为对象，或文档说明仅支持单个 |

**AI处理**：
1. 检查三方接口入参中申请单字段是数组还是对象
2. 如果是数组 → 配置为 `sourceParamType=ARRAY`（批量模式）
3. 如果是对象 → 配置为 `sourceParamType=OBJECT`（拆分模式），框架自动拆分items数组逐个调用
4. 不确定时 → **必须询问客户**三方接口是否支持批量

**配置差异**：

```json
// 批量模式：items保持数组
{
  "sourceParamKey": "items",
  "sourceParamType": "ARRAY",
  "targetParamKey": "orders",
  "targetParamType": "ARRAY"
}

// 拆分模式：items配置为对象
{
  "sourceParamKey": "items",
  "sourceParamType": "OBJECT",
  "targetParamKey": "order",
  "targetParamType": "OBJECT"
}
```

### 2. 节点关键字配置

**keywordField**：`patientInfo.patientCode`

用于日志检索和问题排查，框架会从 Jarvis 入参中提取此字段值作为业务关键字记录到调用日志中。

### 3. 常见映射场景

| 场景 | 源字段 | 映射规则 | 说明 |
|------|----------|----------|------|
| 嵌套字段提取 | `patientInfo.hisPatientId` | `#data[hisPatientId]` | patientInfo、doctorInfo 对象中的字段 |
| 性别转换 | `patientInfo.sex` | `#data[sex] == '1' ? '男' : '女'` | 数字转文字 |
| 时间生成 | - | `new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new java.util.Date())` | 动态生成当前时间 |
| 状态码转换 | 响应 `returnCode` | `#data == "1" ? "200" : "-1"` | 三方状态码转换 |
| 金额转换 | `price` | 使用 `priceYuan` 或 `#data / 100` | 分转元 |

**提示**：嵌套对象字段统一使用 `#data[fieldName]` 提取（不加引号），如 `#data[visitNo]`、`#data[age]` 等

### 4. 申请单数组映射配置要点

#### 批量模式数组映射

**一级数组映射**：`items` → 三方申请单数组
- 源参数类型：`ARRAY`
- 目标参数类型：`ARRAY`
- 必须包含虚拟节点（`sourceParamType=NONE`, `targetParamType=OBJECT`）
- 配置 `childParam` 进行子项字段映射

**虚拟节点命名**：通常使用目标字段名 + "Node" 后缀（如 `orderNode`）

#### 拆分模式对象映射

**对象映射**：`items` → 三方申请单对象
- 源参数类型：`OBJECT`
- 目标参数类型：`OBJECT`
- 直接配置 `childParam` 进行字段映射，无需虚拟节点
- 框架会在工作流层自动拆分items数组，每个元素触发一次独立调用

#### 后置数组映射(三方 → Jarvis)

**数据源选择**：
- 后置处理可从 `INPUT`(原始Jarvis入参)或 `RESPONSE`(三方响应)取值
- **关键**：响应映射依赖三方是否提供关联字段

**场景A：三方提供关联字段**(推荐)
- 入参中提供唯一标识(如 `applyId` 或 `idPatientFeeItem`)
- 三方响应必须返回：
  - **关联字段**：能关联到入参的唯一标识(字段名可以不同,但值能对应)
    - 可能对应入参的 `applyId`(如三方字段名: `sourceApplyNo`、`orderNo`、`refApplyId`)
    - 可能对应入参的 `idPatientFeeItem`(如三方字段名: `sourceItemId`、`feeItemNo`、`refItemId`)
  - **三方生成的ID**：三方系统生成的申请单号(如 `hisApplyId`、`hisOrderId`)
- 配置：
  - 关联字段映射到 Jarvis 的对应字段，数据源 `RESPONSE`
  - 三方生成的ID映射到 `applyId`，数据源 `RESPONSE`
  - 数组以 `RESPONSE` 为数据源
  - 框架通过关联字段的值匹配找到对应数据

**场景B：三方不提供关联字段**
- 三方响应只返回成功状态，无可用于关联的ID字段
- 或三方返回ID但无法与入参建立对应关系
- 配置：`applyId` 和 `idPatientFeeItem` 都从 `INPUT` 取值
- 响应仅用于判断成功与否

---

## Jarvis入参

```json
{
  "items": [
    {
      "presId": "595322",
      "isConsum": 0,
      "departType": "PACS",
      "interfaceCode": "1237",
      "idDepart": 67,
      "isFeeType": "0",
      "feeItemName": "常规心电图检查",
      "discount": "1.00000",
      "price": 2000,
      "priceYuan": 20,
      "toPayPrice": 2000,
      "isFeeState": 0,
      "originalPrice": 2000,
      "originalPriceYuan": 20,
      "factPrice": 2000,
      "factPriceYuan": 20,
      "idPatientFeeItem": "158314",
      "idFeeItem": "744",
      "applyId": "80158314",
      "departName": "心电图室",
      "ddInterfaceCode1": "1058",
      "dfiInterfaceCode1": "1237",
      "dfiInterfaceCode2": "",
      "dfiInterfaceCode3": "",
      "dfiInterfaceCode4": "",
      "dfiInterfaceCode5": "",
      "number": "zqf0558",
      "loginName": "zqf0558",
      "userName": "朱秋芳",
      "idRegister": 722,
      "sampleName": ""
    },
    {
      "presId": "595322",
      "isConsum": 0,
      "departType": "PACS",
      "interfaceCode": "1258",
      "idDepart": 18,
      "isFeeType": "0",
      "feeItemName": "胸部后前位",
      "discount": "1.00000",
      "price": 3900,
      "priceYuan": 39,
      "toPayPrice": 3900,
      "isFeeState": 0,
      "originalPrice": 3900,
      "originalPriceYuan": 39,
      "factPrice": 3900,
      "factPriceYuan": 39,
      "idPatientFeeItem": "158315",
      "idFeeItem": "907",
      "applyId": "80158315",
      "departName": "放射科DR",
      "ddInterfaceCode1": "1063",
      "dfiInterfaceCode1": "1258",
      "dfiInterfaceCode2": "",
      "dfiInterfaceCode3": "",
      "dfiInterfaceCode4": "",
      "dfiInterfaceCode5": "",
      "number": "zqf0558",
      "loginName": "zqf0558",
      "userName": "朱秋芳",
      "idRegister": 722,
      "sampleName": ""
    }
  ],
  "patientInfo": {
    "sex": "2",
    "age": 54,
    "marriage": "3",
    "identitycard": "330502197101062226",
    "cardType": "1",
    "phone": "18367276320",
    "birthday": "1971-01-06",
    "address": "浙江省湖州市吴兴区滨湖街道大钱村唐家浒２０号",
    "patientName": "蔡培勤",
    "patientCode": "2504280032",
    "hisPatientId": "85184",
    "visitNo": "2504280032",
    "userType": 0,
    "orgName": "",
    "registrationExtend1": "330502197101062226",
    "registrationExtend2": "2025007226",
    "registertime": "2025-04-28 08:00:55",
    "physicalTypes": "physical:types:O",
    "physicalTypeName": "入职体检"
  },
  "doctorInfo": {
    "idUser": 722,
    "userName": "朱秋芳",
    "number": "zqf0558"
  }
}
```

---

## Jarvis出参

```json
{
  "code": "200",
  "message": "成功",
  "rsp": {
    "items": [
      {
        "applyId": "2025092900000115",
        "idPatientFeeItem": "158314"
      },
      {
        "applyId": "2025092900000116",
        "idPatientFeeItem": "158315"
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
| rsp.items | 申请单响应列表（**必须与入参items顺序一致**） |
| rsp.items[].applyId | 三方系统生成的申请单号 |
| rsp.items[].idPatientFeeItem | 体检收费项ID（用于关联） |

**关键点**：
- `rsp.items` 数组长度和顺序必须与入参 `items` 一致
- **场景A**：三方提供关联字段(字段名可能不同，但值能关联)
  - **关联字段** 从 `RESPONSE` 取值，用于建立关联(对应入参的 `applyId` 或 `idPatientFeeItem`)
  - **三方生成的ID** 从 `RESPONSE` 取值，映射到 `applyId`
  - 数组以 `RESPONSE` 为数据源
  - 框架通过关联字段的值匹配找到对应数据
- **场景B**：三方不提供关联字段或无法关联
  - `applyId` 和 `idPatientFeeItem` 都来自原始入参(mappingSource=INPUT)
  - 数组以 `INPUT` 为数据源
  - 响应仅用于判断成功与否

---

## 映射配置示例

> **重要说明**：以下示例仅用于说明映射配置方法，实际三方接口的入参、出参字段必须以客户提供的接口文档或实际出入参为准。

### 三方入参示例（批量模式）

```json
{
  "birthDay": "1971-01-06",
  "clinicId": "2504280032",
  "patientId": "85184",
  "sex": "2",
  "name": "蔡培勤",
  "identitycard": "330502197101062226",
  "age": "54",
  "patientCode": "2504280032",
  "orders": [
    {
      "sourceId": "80158314",
      "ordersId": "1237",
      "ordersDept": "1058",
      "executeDept": "1058",
      "ordersManId": "zqf0558",
      "ordersDate": "2025-11-26 14:07:36",
      "ordersName": "常规心电图检查",
      "checkType": "",
      "price": "20.0",
      "factPrice": "20.0"
    },
    {
      "sourceId": "80158315",
      "ordersId": "1258",
      "ordersDept": "1063",
      "executeDept": "1063",
      "ordersManId": "zqf0558",
      "ordersDate": "2025-11-26 14:07:36",
      "ordersName": "胸部后前位",
      "checkType": "",
      "price": "39.0",
      "factPrice": "39.0"
    }
  ]
}
```

### 三方响应示例

**场景A：提供关联字段**(推荐)

```json
// 示例1: 三方返回对应入参applyId的关联字段
{
  "returnCode": "1",
  "errorMessage": "成功",
  "data": [
    {
      "sourceApplyNo": "80158314",     // 关联字段：对应入参的applyId
      "hisOrderId": "HIS9080158314"    // 三方生成的申请单号
    },
    {
      "sourceApplyNo": "80158315",
      "hisOrderId": "HIS9080158315"
    }
  ]
}

// 示例2: 三方返回对应入参idPatientFeeItem的关联字段
{
  "returnCode": "1",
  "errorMessage": "成功",
  "data": [
    {
      "feeItemNo": "12345",            // 关联字段：对应入参的idPatientFeeItem
      "hisApplyId": "HIS9080158314"    // 三方生成的申请单号
    },
    {
      "feeItemNo": "12346",
      "hisApplyId": "HIS9080158315"
    }
  ]
}
```

**说明**：
- 三方字段名可以自定义(如 `sourceApplyNo`、`feeItemNo`、`orderNo`、`refId` 等)
- 关键是字段的**值**能关联到入参的唯一标识(`applyId` 或 `idPatientFeeItem`)
- 配置时需要正确映射三方字段名到Jarvis字段
- 框架通过关联字段的值进行匹配

**场景B：不提供关联字段**

```json
{
  "returnCode": "1",
  "errorMessage": "成功",
  "data": {
    "success": true
  }
}
```

**说明**：响应仅返回成功状态，无申请单号，此时响应中的items完全从INPUT复制

### 前置处理映射（Jarvis → 三方）- 批量模式

| Jarvis字段 | 源参数类型 | 三方字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| patientInfo | OBJECT | patientId | STRING | EXPRESSION | `#data[hisPatientId]` |
| patientInfo | OBJECT | clinicId | STRING | EXPRESSION | `#data[visitNo]` |
| patientInfo | OBJECT | patientCode | STRING | EXPRESSION | `#data[patientCode]` |
| patientInfo | OBJECT | name | STRING | EXPRESSION | `#data[patientName]` |
| patientInfo | OBJECT | age | STRING | EXPRESSION | `#data[age]` |
| patientInfo | OBJECT | sex | STRING | EXPRESSION | `#data[sex]` |
| patientInfo | OBJECT | birthDay | STRING | EXPRESSION | `#data[birthday]` |
| patientInfo | OBJECT | identitycard | STRING | EXPRESSION | `#data[identitycard]` |
| items | ARRAY | orders | ARRAY | NAME | 数组映射 |
| - | NONE | └─ orderNode | OBJECT | NAME | 虚拟节点 |
| └─ applyId | STRING |     └─ sourceId | STRING | NAME | - |
| └─ dfiInterfaceCode1 | STRING |     └─ ordersId | STRING | NAME | - |
| └─ ddInterfaceCode1 | STRING |     └─ ordersDept | STRING | NAME | - |
| └─ ddInterfaceCode1 | STRING |     └─ executeDept | STRING | NAME | - |
| └─ number | STRING |     └─ ordersManId | STRING | NAME | - |
| └─ feeItemName | STRING |     └─ ordersName | STRING | NAME | - |
| └─ priceYuan | STRING |     └─ price | STRING | NAME | - |
| └─ factPriceYuan | STRING |     └─ factPrice | STRING | NAME | - |
| - | NONE |     └─ ordersDate | STRING | EXPRESSION | `new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new java.util.Date())` |

### 前置处理映射（Jarvis → 三方）- 拆分模式

| Jarvis字段 | 源参数类型 | 三方字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| patientInfo | OBJECT | patientId | STRING | EXPRESSION | `#data[hisPatientId]` |
| patientInfo | OBJECT | clinicId | STRING | EXPRESSION | `#data[visitNo]` |
| patientInfo | OBJECT | name | STRING | EXPRESSION | `#data[patientName]` |
| items | OBJECT | order | OBJECT | NAME | 对象映射（无虚拟节点） |
| └─ applyId | STRING | └─ sourceId | STRING | NAME | - |
| └─ dfiInterfaceCode1 | STRING | └─ ordersId | STRING | NAME | - |
| └─ ddInterfaceCode1 | STRING | └─ ordersDept | STRING | NAME | - |
| └─ number | STRING | └─ ordersManId | STRING | NAME | - |
| └─ feeItemName | STRING | └─ ordersName | STRING | NAME | - |
| └─ priceYuan | STRING | └─ price | STRING | NAME | - |

**注意**：拆分模式下，items配置为OBJECT类型，框架会自动拆分数组逐个调用

### 后置处理映射(三方 → Jarvis)

**场景A：三方提供关联字段**

| 三方字段 | 源参数类型 | Jarvis字段 | 目标参数类型 | 映射类型 | 映射数据源 | 映射规则 |
|---------|-----------|-------------|-------------|----------|-----------|----------|
| returnCode | STRING | code | STRING | EXPRESSION | RESPONSE | `#data == "1" ? "200" : "-1"` |
| errorMessage | STRING | message | STRING | NAME | RESPONSE | - |
| - | NONE | rsp | OBJECT | NAME | - | 嵌套映射 |
| data | ARRAY | └─ items | ARRAY | NAME | RESPONSE | 数组映射(以RESPONSE为基础) |
| - | NONE |     └─ itemNode | OBJECT | NAME | RESPONSE | 虚拟节点 |
|     └─ sourceApplyNo | STRING |         └─ idPatientFeeItem | STRING | NAME | RESPONSE | 关联字段(对应入参applyId) |
|     └─ hisOrderId | STRING |         └─ applyId | STRING | NAME | RESPONSE | 三方生成的申请单号 |

**说明**：
- 示例使用 `sourceApplyNo` 作为关联字段，实际可能是其他字段名
- 关联字段的**值**对应入参的 `applyId` 或 `idPatientFeeItem`
- 配置时根据三方实际字段名进行映射
- 数组以 `RESPONSE` 为数据源
- 框架通过关联字段的值匹配找到对应数据

**常见三方关联字段名**：
- 对应 `applyId`: `sourceApplyNo`、`orderNo`、`refApplyId`、`applyNumber`
- 对应 `idPatientFeeItem`: `sourceItemId`、`feeItemNo`、`refItemId`、`itemCode`

**场景B：三方不提供关联字段**

| 三方字段 | 源参数类型 | Jarvis字段 | 目标参数类型 | 映射类型 | 映射数据源 | 映射规则 |
|---------|-----------|-------------|-------------|----------|-----------|----------|
| returnCode | STRING | code | STRING | EXPRESSION | RESPONSE | `#data == "1" ? "200" : "-1"` |
| errorMessage | STRING | message | STRING | NAME | RESPONSE | - |
| - | NONE | rsp | OBJECT | NAME | - | 嵌套映射 |
| items | ARRAY | └─ items | ARRAY | NAME | INPUT | 数组映射(以INPUT为基础) |
| - | NONE |     └─ itemNode | OBJECT | NAME | INPUT | 虚拟节点 |
|     └─ applyId | STRING |         └─ applyId | STRING | NAME | INPUT | 来自原始入参 |
|     └─ idPatientFeeItem | STRING |         └─ idPatientFeeItem | STRING | NAME | INPUT | 来自原始入参 |

**说明**：
- 数组以 `INPUT` 为数据源
- `applyId` 和 `idPatientFeeItem` 都从原始入参取值
- 三方响应仅用于状态判断

---

## AI配置步骤

### 步骤1：获取三方接口信息

询问客户提供三方接口文档，或明确以下信息：

**必须信息**：
1. 三方申请单接口的入参字段及格式
2. 三方申请单接口的响应字段及格式
3. **关键**：是否支持批量创建（一次发送多个申请单）

### 步骤2：判断items处理模式

**判断标准**：
- 三方入参中申请单字段是数组 → 批量模式（`sourceParamType=ARRAY`）
- 三方入参中申请单字段是对象 → 拆分模式（`sourceParamType=OBJECT`）
- 不确定 → 询问客户

### 步骤3：生成前置映射（Jarvis → 三方）

参考上述前置处理映射表（根据批量/拆分模式选择）

### 步骤4：生成后置映射(三方 → Jarvis)

**关键判断**：三方响应是否提供关联字段?

**场景A**：三方响应返回能关联到入参的字段
- 识别三方哪个字段能关联到入参的 `applyId` 或 `idPatientFeeItem`
- 该关联字段从 `RESPONSE` 取值，映射到对应的Jarvis字段
- 三方生成的申请单号从 `RESPONSE` 取值，映射到 `applyId`
- 数组以 `RESPONSE` 为数据源
- 框架通过关联字段的值建立对应关系

**注意**：三方字段名可能不同(如 `sourceApplyNo`、`feeItemNo`、`orderNo` 等)，需要根据实际情况配置

**场景B**：三方响应不包含关联字段或无法关联
- `applyId` 和 `idPatientFeeItem` 都从 `INPUT` 取值
- 数组以 `INPUT` 为数据源
- 响应仅用于判断成功与否

参考上述后置处理映射表
