---
trigger: model_decision
description: 
---
# LIS报告获取接口配置指南

> **业务专用指南**：提供LIS报告获取场景的完整配置示例和步骤

---

## 目的

主动从LIS系统查询并获取检验报告详细信息（如血常规、生化、免疫等检验项目结果）。

---

## 场景识别

当客户提到「LIS报告获取」「LIS报告查询」「检验报告查询」「获取检验报告详情」「查询检验报告内容」时，明确为LIS报告获取场景。

**注意**：PACS影像报告获取是另外的业务场景，请使用对应的PACS报告获取配置指南。

---

## 业务要点

### 1. 节点关键字配置

**keywordField**：`PatientCode`

用于日志检索和问题排查，框架会从Jarvis入参中提取此字段值作为业务关键字记录到调用日志中。

**配置位置**：节点配置的 `keywordField` 字段

### 2. 数据流向

**标准查询场景**：Jarvis → LIS

- **上游接口**：Jarvis（主动查询方）
- **下游接口**：LIS系统（被动响应方）

### 3. 查询条件

**支持三种查询方式**（3选1）：

| 查询方式 | 字段 | 说明 | paramType |
|---------|------|------|----------|
| 方式1 | outFeeItemId | 通过收费项外部编码查询 | 1 |
| 方式2 | applyNo | 通过申请单号查询 | 2 |
| 方式3 | barCode | 通过条码号查询 | 3 |

**必填字段**：
- `serviceProviderType` - 厂商类型（固定为LIS）
- `patientCode` - 患者编号
- `outFeeItemId` / `applyNo` / `barCode` - 三选一，根据paramType决定
- `paramType` - 指定使用哪种查询方式（1/2/3）

**业务建议**：
- **LIS系统推荐使用条码号**（barCode）作为主要查询方式，paramType=3
- 条码号是LIS检验业务的核心标识

**注意**：
- 查询字段支持数组格式，可同时查询多条报告
- LIS返回的是明细数据（每个检验小项一条记录）

### 4. 响应数据结构

LIS通常返回**数组**，一个收费项包含多个检验小项：

```json
{
  "total": 6,
  "data": [
    {
      "PatientCode": "25102100095",
      "ID_FeeItem": "101",
      "FeeItem": "电解质6项",
      "InterfaceCode1": "0301521",
      "ExamItemName": "钙",
      "ExamItemValue": "2.3",
      "Unit": "mmol/L",
      "RangeValue": "2.1--2.52",
      "LISTag": "M",
      "ExamDotor": "许依超",
      "ExamTime": "2026-01-19 00:00:00",
      "auditDoctor": "朱梅松",
      "auditTime": "2026-01-19 10:36:39",
      "barcode": "8054551097"
    }
  ]
}
```

### 5. 关键字段映射

**Jarvis → 三方（前置）**：

| Jarvis字段 | 三方字段 | 说明 |
|-----------|---------|------|
| ServiceProviderType | - | 固定为LIS，不传给三方 |
| PatientCode | PatientCode | 患者编号 |
| OutFeeItemIdList / ApplyNoList / BarCodeList | 对应查询字段 | 根据paramType决定 |
| ParamType | - | 查询方式标识，不传给三方 |

**三方 → Jarvis（后置）**：

| 三方字段 | Jarvis字段 | 说明 |
|---------|-----------|------|
| - | code | 固定值200 |
| data | rsp | 报告数据数组 |
| data[].PatientCode | rsp[].patientCode | 体检编号 |
| data[].ID_FeeItem | rsp[].outFeeItemId | 收费项外部编码 |
| data[].InterfaceCode1 | rsp[].outExamItemId | 检查项外部编码 |
| data[].ExamItemValue | rsp[].examItemValue | 检测结果 |
| data[].LISTag | rsp[].listag | LIS标记符（↑/↓/阳性等） |
| data[].LISTag | rsp[].idSeverelevel | 严重级别（0=正常，3=异常） |
| data[].RangeValue | rsp[].rangeValue | 参考范围 |
| data[].Unit | rsp[].units | 单位 |
| data[].ExamDotor | rsp[].examDoctor | 检查人 |
| data[].ExamTime | rsp[].examTime | 检查时间 |
| data[].auditDoctor | rsp[].auditDoctor | 审核人 |
| data[].auditTime | rsp[].auditTime | 审核时间 |
| data[].FeeItem | rsp[].outFeeItemName | 收费项名称 |
| data[].ExamItemName | rsp[].outExamItemName | 检查项名称 |
| - | rsp[].serviceProviderType | 固定值LIS |

---

## Jarvis入参

**示例1：通过条码号查询（LIS推荐）**

```json
{
  "BusinessMethod": "GetItemResult",
  "ServiceProviderType": "LIS",
  "PatientCode": "25102100095",
  "BarCodeList": [
    "8054551097"
  ],
  "ParamType": 3
}
```

**示例2：通过收费项外部编码查询**

```json
{
  "BusinessMethod": "GetItemResult",
  "ServiceProviderType": "LIS",
  "PatientCode": "25102100095",
  "OutFeeItemIdList": [
    "101"
  ],
  "ParamType": 1
}
```

**示例3：通过申请单号查询**

```json
{
  "BusinessMethod": "GetItemResult",
  "ServiceProviderType": "LIS",
  "PatientCode": "25102100095",
  "ApplyNoList": [
    "LIS20260119001"
  ],
  "ParamType": 2
}
```

**字段说明**：

| 字段 | 说明 | 必填 | 备注 |
|------|------|------|------|
| BusinessMethod | 业务方法标识 | 是 | 固定值GetItemResult |
| ServiceProviderType | 厂商类型 | 是 | 固定值LIS |
| PatientCode | 患者编号 | 是 | - |
| OutFeeItemIdList | 收费项外部编码列表 | 3选1 | ParamType=1时使用 |
| ApplyNoList | 申请单号列表 | 3选1 | ParamType=2时使用 |
| BarCodeList | 条码号列表 | 3选1 | ParamType=3时使用（推荐） |
| ParamType | 查询方式 | 是 | 1=收费项编码, 2=申请单号, 3=条码号 |

---

## Jarvis出参

```json
{
  "code": "200",
  "rsp": [
    {
      "patientCode": "25102100095",
      "outFeeItemId": "101",
      "outExamItemId": "0301521",
      "serviceProviderType": "LIS",
      "examItemValue": "2.3",
      "idSeverelevel": "0",
      "rangeValue": "2.1--2.52",
      "units": "mmol/L",
      "examDoctor": "许依超",
      "examTime": "2026-01-19 00:00:00",
      "auditDoctor": "朱梅松",
      "auditTime": "2026-01-19 10:36:39",
      "outFeeItemName": "电解质6项",
      "outExamItemName": "钙"
    },
    {
      "patientCode": "25102100095",
      "outFeeItemId": "101",
      "outExamItemId": "0301523",
      "serviceProviderType": "LIS",
      "examItemValue": "1.1",
      "listag": "↑",
      "idSeverelevel": "3",
      "rangeValue": "0.75--1.02",
      "units": "mmol/L",
      "examDoctor": "许依超",
      "examTime": "2026-01-19 00:00:00",
      "auditDoctor": "朱梅松",
      "auditTime": "2026-01-19 10:36:39",
      "outFeeItemName": "电解质6项",
      "outExamItemName": "镁"
    }
  ]
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| code | 状态码，200成功 |
| rsp | 报告数据数组（每个检验小项一条记录） |
| rsp[].serviceProviderType | 厂商类型（固定值LIS） |
| rsp[].patientCode | 体检编号 |
| rsp[].outFeeItemId | 收费项外部编码 |
| rsp[].outExamItemId | 检查项外部编码 |
| rsp[].examItemValue | 检测结果值 |
| rsp[].listag | LIS标记符（↑/↓/阳性等） |
| rsp[].idSeverelevel | 严重级别（0=正常，3=异常） |
| rsp[].rangeValue | 参考范围 |
| rsp[].units | 单位 |
| rsp[].examDoctor | 检查人 |
| rsp[].examTime | 检查时间 |
| rsp[].auditDoctor | 审核人 |
| rsp[].auditTime | 审核时间 |
| rsp[].outFeeItemName | 收费项名称 |
| rsp[].outExamItemName | 检查项名称 |

---

## 映射配置示例

> **重要说明**：以下示例仅用于说明映射配置方法，实际LIS接口的入参、出参字段必须以客户提供的接口文档或实际出入参为准。

### 三方入参示例

**示例1：通过条码号查询（SQL）**

```sql
SELECT * FROM tj_result WHERE PatientCode = '25102100095' AND barcode = '8054551097'
```

**示例2：通过收费项外部编码查询（SQL）**

```sql
SELECT * FROM tj_result WHERE PatientCode = '25102100095' AND ID_FeeItem IN ('101')
```

### 三方响应示例

```json
{
  "total": 6,
  "data": [
    {
      "PatientCode": "25102100095",
      "ID_FeeItem": "101",
      "FeeItem": "电解质6项",
      "InterfaceCode1": "0301521",
      "ExamItemName": "钙",
      "ExamItemValue": "2.3",
      "Unit": "mmol/L",
      "RangeValue": "2.1--2.52",
      "LISTag": "M",
      "ExamDotor": "许依超",
      "ExamTime": "2026-01-19 00:00:00",
      "auditDoctor": "朱梅松",
      "auditTime": "2026-01-19 10:36:39",
      "barcode": "8054551097"
    },
    {
      "PatientCode": "25102100095",
      "ID_FeeItem": "101",
      "FeeItem": "电解质6项",
      "InterfaceCode1": "0301523",
      "ExamItemName": "镁",
      "ExamItemValue": "1.1",
      "Unit": "mmol/L",
      "RangeValue": "0.75--1.02",
      "LISTag": "H",
      "ExamDotor": "许依超",
      "ExamTime": "2026-01-19 00:00:00",
      "auditDoctor": "朱梅松",
      "auditTime": "2026-01-19 10:36:39",
      "barcode": "8054551097"
    }
  ]
}
```

### 前置处理映射（Jarvis → 三方）

**方式1：通过收费项外部编码查询**

| Jarvis字段 | 源参数类型 | 三方字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| PatientCode | STRING | PatientCode | STRING | NAME | - |
| OutFeeItemIdList | ARRAY | ID_FeeItem | ARRAY | NAME | - |
| ParamType | INTEGER | - | - | - | 不传给三方 |

**方式2：通过条码号查询**

| Jarvis字段 | 源参数类型 | 三方字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| PatientCode | STRING | PatientCode | STRING | NAME | - |
| BarCodeList | ARRAY | barcode | ARRAY | NAME | - |
| ParamType | INTEGER | - | - | - | 不传给三方 |

### 后置处理映射（三方 → Jarvis）

| 三方字段 | 源参数类型 | Jarvis字段 | 目标参数类型 | 映射类型 | 映射数据源 | 映射规则 |
|---------|-----------|-------------|-------------|----------|-----------|----------|
| - | NONE | code | STRING | CONSTANT | RESPONSE | `200` |
| data | ARRAY | rsp | ARRAY | NAME | RESPONSE | 嵌套映射 |
| └─ PatientCode | STRING | └─ patientCode | STRING | NAME | RESPONSE | - |
| └─ ID_FeeItem | STRING | └─ outFeeItemId | STRING | NAME | RESPONSE | - |
| └─ InterfaceCode1 | STRING | └─ outExamItemId | STRING | NAME | RESPONSE | - |
| └─ ExamItemValue | STRING | └─ examItemValue | STRING | NAME | RESPONSE | - |
| └─ LISTag | STRING | └─ listag | STRING | EXPRESSION | RESPONSE | LIS标记符转换 |
| └─ LISTag | STRING | └─ idSeverelevel | STRING | EXPRESSION | RESPONSE | 严重级别转换 |
| └─ RangeValue | STRING | └─ rangeValue | STRING | NAME | RESPONSE | - |
| └─ Unit | STRING | └─ units | STRING | EXPRESSION | RESPONSE | 空值处理 |
| └─ ExamDotor | STRING | └─ examDoctor | STRING | NAME | RESPONSE | - |
| └─ ExamTime | STRING | └─ examTime | STRING | NAME | RESPONSE | - |
| └─ auditDoctor | STRING | └─ auditDoctor | STRING | NAME | RESPONSE | - |
| └─ auditTime | STRING | └─ auditTime | STRING | NAME | RESPONSE | - |
| └─ FeeItem | STRING | └─ outFeeItemName | STRING | NAME | RESPONSE | - |
| └─ ExamItemName | STRING | └─ outExamItemName | STRING | NAME | RESPONSE | - |
| - | NONE | └─ serviceProviderType | STRING | CONSTANT | RESPONSE | `LIS` |

**LISTag转换规则**：

| LISTag值 | listag显示 | idSeverelevel | 说明 |
|---------|-----------|---------------|------|
| M | null | 0 | 正常 |
| P | 阳性 | 3 | 阳性 |
| H | ↑ | 3 | 偏高 |
| L | ↓ | 3 | 偏低 |
| Q | 阳性 | 3 | 阳性 |

**映射表达式**：

```javascript
// listag转换
#data == 'M' ? null : (#data == 'P' ? '阳性' : (#data == 'H' ? '↑' : (#data == 'L' ? '↓' : (#data == 'Q' ? '阳性' : null))))

// idSeverelevel转换
#data == 'P' ? '3' : (#data == 'H' ? '3' : (#data == 'L' ? '3' : (#data == 'Q' ? '3' : '0')))

// units空值处理
#data == null ? '' : #data
```

**说明**：
- `serviceProviderType` 固定值为LIS
- `code` 固定值为200
- `listag` 和 `idSeverelevel` 都从LISTag字段转换
- `units` 需要处理空值情况

---

## AI配置步骤

### 步骤1：获取LIS接口信息

询问客户提供LIS报告查询接口文档，或明确以下信息：

**必须信息**：
1. LIS查询接口的入参字段及格式（SQL或接口）
2. LIS查询接口的响应字段及格式
3. LIS标记符（LISTag）的取值及含义
4. 是否支持批量查询

### 步骤2：确认查询条件和查询方式

**确认查询方式**（3选1）：
- **方式1**：通过收费项外部编码（outFeeItemId）查询
- **方式2**：通过申请单号（applyNo）查询
- **方式3**：通过条码号（barCode）查询 - **LIS推荐**

**确认必填字段**：
- `serviceProviderType` - 厂商类型（固定为LIS）
- `patientCode` - 患者编号
- `paramType` - 查询方式标识（1/2/3）
- 对应的查询字段列表（根据paramType决定）

### 步骤3：确认响应数据结构

确认LIS响应的数据格式：

- **数据结构**：通常为数组，一个收费项包含多个检验小项
- **LIS标记符**：M/P/H/L/Q等的具体含义
- **必需字段**：哪些字段是必然返回的
- **可选字段**：哪些字段可能为空

### 步骤4：生成前置映射（Jarvis → LIS）

参考上述前置处理映射表

**关键配置**：

1. **确定查询方式**：根据LIS接口支持的查询方式，选择对应的映射方案
   - LIS推荐使用条码号（barCode），paramType=3
   - 如果使用收费项编码，paramType=1
   - 如果使用申请单号，paramType=2

2. **ParamType字段**：
   - 不传给LIS，仅在Jarvis内部使用

3. **数组格式**：
   - 查询字段支持数组格式，可批量查询

### 步骤5：生成后置映射（LIS → Jarvis）

参考上述后置处理映射表

**注意**：
- LIS返回的是明细数据（每个检验小项一条记录）
- serviceProviderType固定为LIS
- code固定为200
- LISTag需要转换为listag和idSeverelevel两个字段
- units可能为空，需要处理空值

### 步骤6：处理LIS标记符转换

**重要**：LIS标记符（LISTag）的转换是关键

确认LIS的标记符含义：

| 常见标记 | 含义 |
|---------|------|
| M | 正常 |
| P | 阳性 |
| H | 偏高 |
| L | 偏低 |
| Q | 阳性 |

**转换规则**：
- listag：用于前端显示（↑/↓/阳性等）
- idSeverelevel：用于严重程度判断（0=正常，3=异常）

