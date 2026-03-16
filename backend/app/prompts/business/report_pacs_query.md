---
trigger: model_decision
description: 
---
# PACS报告获取接口配置指南

> **业务专用指南**：提供PACS报告获取场景的完整配置示例和步骤

---

## 目的

主动从PACS系统查询并获取检查报告详细信息（如CT、DR、超声等影像检查报告）。

---

## 场景识别

当客户提到「PACS报告获取」「PACS报告查询」「影像报告查询」「获取检查报告详情」「查询检查报告内容」时，明确为PACS报告获取场景。

**注意**：LIS检验报告获取是另外的业务场景，请使用对应的LIS报告获取配置指南。

---

## 业务要点

### 1. 节点关键字配置

**keywordField**：`PatientCode`

用于日志检索和问题排查，框架会从Jarvis入参中提取此字段值作为业务关键字记录到调用日志中。

**配置位置**：节点配置的 `keywordField` 字段

### 2. 数据流向

**标准查询场景**：Jarvis → PACS

- **上游接口**：Jarvis（主动查询方）
- **下游接口**：PACS系统（被动响应方）

### 3. 查询条件

**支持三种查询方式**（3选1）：

| 查询方式 | 字段 | 说明 | paramType |
|---------|------|------|----------|
| 方式1 | outFeeItemId | 通过收费项外部编码查询 | 1 |
| 方式2 | applyNo | 通过申请单号查询 | 2 |
| 方式3 | barCode | 通过条码号查询 | 3 |

**必填字段**：
- `serviceProviderType` - 厂商类型（固定为PACS）
- `patientCode` - 患者编号
- `outFeeItemId` / `applyNo` / `barCode` - 三选一，根据paramType决定
- `paramType` - 指定使用哪种查询方式（1/2/3）

**注意**：
- 查询字段支持数组格式，可同时查询多条报告
- 三方系统根据指定的查询方式返回对应的报告数据

### 4. 响应数据结构

三方通常返回**数组**，包含多条报告记录：

```json
{
  "returnCode": "1",
  "errorMessage": "",
  "data": [
    {
      "sourceId": "DJ20260113170908000006",
      "examTime": "2026-01-13 17:09:08",
      "reportTime": "2026-01-13 17:30:00",
      "reportDoctor": "张医生",
      "reportContent": "检查结果正常",
      "reportUrl": "http://pacs.example.com/report/123456"
    }
  ]
}
```

### 5. 关键字段映射

**Jarvis → 三方（前置）**：

| Jarvis字段 | 三方字段 | 说明 |
|-----------|---------|------|
| ServiceProviderType | serviceProviderType | 厂商类型 |
| PatientCode | patientCode | 患者编号 |
| OutFeeItemIdList / ApplyNoList / BarCodeList | outFeeItemIds / sourceIds / barCodes | 根据paramType决定 |
| ParamType | paramType | 查询方式（1/2/3） |

**三方 → Jarvis（后置）**：

| 三方字段 | Jarvis字段 | 说明 |
|---------|-----------|------|
| returnCode | code | 状态码转换 |
| errorMessage | message | 错误消息 |
| data | rsp | 报告数据数组 |
| data[].patientCode | rsp[].patientCode | 体检编号 |
| data[].sourceId | rsp[].applyNo | 申请单号 |
| data[].examinationDate | rsp[].examTime | 检查时间 |
| data[].examiner | rsp[].examDoctor | 检查人 |
| data[].audit | rsp[].auditDoctor | 审核人 |
| data[].auditDate | rsp[].auditTime | 审核时间 |
| data[].reportFind | rsp[].impressionValue | 检查所见值 |
| data[].reportOpinion | rsp[].examItemValue | 检测结果 |
| data[].imagePath | rsp[].fileUrl | 报告文件URL |
| - | rsp[].fileProtocol | 文件协议（固定值http） |
| - | rsp[].fileType | 文件类型（固定值pdf） |
| data[].isPositive | rsp[].idSeverelevel | 阳性标识转严重级别 |
| - | rsp[].serviceProviderType | 厂商类型（固定值PACS） |

---

## Jarvis入参

**示例1：通过申请单号查询（最常见）**

```json
{
  "BusinessMethod": "query_pacs_report",
  "ServiceProviderType": "PACS",
  "PatientCode": "26011300006",
  "ApplyNoList": [
    "DJ20260113170908000006"
  ],
  "ParamType": 2
}
```

**示例2：通过条码号查询**

```json
{
  "BusinessMethod": "query_pacs_report",
  "ServiceProviderType": "PACS",
  "PatientCode": "26011300006",
  "BarCodeList": [
    "BC202601130001"
  ],
  "ParamType": 3
}
```

**示例3：通过收费项外部编码查询**

```json
{
  "BusinessMethod": "query_pacs_report",
  "ServiceProviderType": "PACS",
  "PatientCode": "26011300006",
  "OutFeeItemIdList": [
    "CT001"
  ],
  "ParamType": 1
}
```

**字段说明**：

| 字段 | 说明 | 必填 | 备注 |
|------|------|------|------|
| BusinessMethod | 业务方法标识 | 是 | 固定值query_pacs_report |
| ServiceProviderType | 厂商类型 | 是 | 固定值PACS |
| PatientCode | 患者编号 | 是 | - |
| OutFeeItemIdList | 收费项外部编码列表 | 3选1 | ParamType=1时使用 |
| ApplyNoList | 申请单号列表 | 3选1 | ParamType=2时使用 |
| BarCodeList | 条码号列表 | 3选1 | ParamType=3时使用 |
| ParamType | 查询方式 | 是 | 1=收费项编码, 2=申请单号, 3=条码号 |

---

## Jarvis出参

```json
{
  "code": "200",
  "message": "成功",
  "rsp": [
    {
      "serviceProviderType": "PACS",
      "patientCode": "26011900017",
      "applyNo": "80000268970",
      "examTime": "2026-01-19 09:11:33",
      "examDoctor": "施秋霞",
      "auditDoctor": "施秋霞",
      "auditTime": "",
      "impressionValue": "肝脏：体积正常...",
      "examItemValue": "肝内脂质沉积。",
      "fileUrl": "http://10.192.50.204:8083/uisimages/20260119/509410/509410.PDF",
      "fileProtocol": "http",
      "fileType": "pdf",
      "idSeverelevel": "3"
    }
  ]
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| code | 状态码，200成功 |
| message | 响应消息 |
| rsp | 报告数据数组 |
| rsp[].serviceProviderType | 厂商类型（固定值PACS） |
| rsp[].patientCode | 体检编号 |
| rsp[].applyNo | 申请单号 |
| rsp[].examTime | 检查时间 |
| rsp[].examDoctor | 检查人 |
| rsp[].auditDoctor | 审核人 |
| rsp[].auditTime | 审核时间 |
| rsp[].impressionValue | 检查所见值（报告描述） |
| rsp[].examItemValue | 检测结果（诊断结论） |
| rsp[].fileUrl | 报告文件URL（存在文件时必填） |
| rsp[].fileProtocol | 文件协议（存在文件时必填）：ftp/http/https/smb/base64/html |
| rsp[].fileType | 文件类型（存在文件时必填）：pdf/jpg等（html类型可不传） |
| rsp[].idSeverelevel | 严重级别（0=阴性，3=阳性） |

---

## 映射配置示例

> **重要说明**：以下示例仅用于说明映射配置方法，实际三方接口的入参、出参字段必须以客户提供的接口文档或实际出入参为准。

### 三方入参示例

**示例1：通过申请单号查询**

```json
{
  "serviceProviderType": "PACS",
  "patientCode": "26011300006",
  "sourceIds": [
    "DJ20260113170908000006"
  ],
  "paramType": 2
}
```

**示例2：通过条码号查询**

```json
{
  "serviceProviderType": "PACS",
  "patientCode": "26011300006",
  "barCodes": [
    "BC202601130001"
  ],
  "paramType": 3
}
```

**示例3：通过收费项外部编码查询**

```json
{
  "serviceProviderType": "PACS",
  "patientCode": "26011300006",
  "outFeeItemIds": [
    "CT001"
  ],
  "paramType": 1
}
```

### 三方响应示例

```json
{
  "returnCode": "1",
  "errorMessage": "成功",
  "data": [
    {
      "patientCode": "26011900017",
      "sourceId": "80000268970",
      "ordersName": "腹部",
      "doctorId": "",
      "examinationDate": "2026-01-19 09:11:33",
      "examiner": "施秋霞",
      "auditDate": "",
      "audit": "施秋霞",
      "isPositive": "1",
      "reportFind": "肝脏：体积正常，包膜光整...",
      "reportOpinion": "肝内脂质沉积。",
      "reportAdvise": "",
      "imagePath": "http://10.192.50.204:8083/uisimages/20260119/509410/509410.PDF"
    }
  ]
}
```

### 前置处理映射（Jarvis → 三方）

**方式1：通过申请单号查询**

| Jarvis字段 | 源参数类型 | 三方字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| ServiceProviderType | STRING | serviceProviderType | STRING | NAME | - |
| PatientCode | STRING | patientCode | STRING | NAME | - |
| ApplyNoList | ARRAY | sourceIds | ARRAY | NAME | - |
| ParamType | INTEGER | paramType | INTEGER | NAME | - |

**方式2：通过条码号查询**

| Jarvis字段 | 源参数类型 | 三方字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| ServiceProviderType | STRING | serviceProviderType | STRING | NAME | - |
| PatientCode | STRING | patientCode | STRING | NAME | - |
| BarCodeList | ARRAY | barCodes | ARRAY | NAME | - |
| ParamType | INTEGER | paramType | INTEGER | NAME | - |

**方式3：通过收费项外部编码查询**

| Jarvis字段 | 源参数类型 | 三方字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| ServiceProviderType | STRING | serviceProviderType | STRING | NAME | - |
| PatientCode | STRING | patientCode | STRING | NAME | - |
| OutFeeItemIdList | ARRAY | outFeeItemIds | ARRAY | NAME | - |
| ParamType | INTEGER | paramType | INTEGER | NAME | - |

### 后置处理映射（三方 → Jarvis）

| 三方字段 | 源参数类型 | Jarvis字段 | 目标参数类型 | 映射类型 | 映射数据源 | 映射规则 |
|---------|-----------|-------------|-------------|----------|-----------|----------|
| returnCode | STRING | code | STRING | EXPRESSION | RESPONSE | `#data == "1" ? "200" : "-1"` |
| errorMessage | STRING | message | STRING | NAME | RESPONSE | - |
| data | ARRAY | rsp | ARRAY | NAME | RESPONSE | 嵌套映射 |
| └─ patientCode | STRING | └─ patientCode | STRING | NAME | RESPONSE | - |
| └─ sourceId | STRING | └─ applyNo | STRING | NAME | RESPONSE | - |
| └─ examinationDate | STRING | └─ examTime | STRING | NAME | RESPONSE | - |
| └─ examiner | STRING | └─ examDoctor | STRING | NAME | RESPONSE | - |
| └─ audit | STRING | └─ auditDoctor | STRING | NAME | RESPONSE | - |
| └─ auditDate | STRING | └─ auditTime | STRING | NAME | RESPONSE | - |
| └─ reportFind | STRING | └─ impressionValue | STRING | NAME | RESPONSE | - |
| └─ reportOpinion | STRING | └─ examItemValue | STRING | NAME | RESPONSE | - |
| └─ imagePath | STRING | └─ fileUrl | STRING | NAME | RESPONSE | - |
| - | NONE | └─ serviceProviderType | STRING | CONSTANT | RESPONSE | `PACS` |
| - | NONE | └─ fileProtocol | STRING | EXPRESSION | RESPONSE | 根据fileUrl解析协议 |
| - | NONE | └─ fileType | STRING | EXPRESSION | RESPONSE | 根据fileUrl解析文件类型 |
| └─ isPositive | STRING | └─ idSeverelevel | STRING | EXPRESSION | RESPONSE | `#data == '1' ? '3' : '0'` |

**说明**：
- `serviceProviderType` 固定值为PACS
- `fileProtocol` 根据三方返回的文件地址解析协议类型：
  - 支持的协议：`ftp`、`http`、`https`、`smb`、`base64`、`html`
  - 如果三方返回http开头的URL，设置为`http`
  - 如果是smb网络地址，设置为`smb`（格式：smb://10.10.73.95/C13/xxx.pdf）
  - 存在文件时此字段必填
- `fileType` 根据三方返回的文件扩展名或类型设置：
  - 常见类型：`pdf`、`jpg`、`png`、`html`等
  - 如果文件类型为`html`时可不传
  - 存在文件时此字段必填
- `fileUrl` 报告文件地址：
  - 多个文件URL使用英文逗号分隔
  - 直接从三方响应中获取或拼接完整URL
  - 存在文件时此字段必填
- `idSeverelevel` 从三方的`isPositive`转换：1=阳性（严重级别3），0=阴性（严重级别0）
- `impressionValue` 对应三方的`reportFind`（检查所见）
- `examItemValue` 对应三方的`reportOpinion`（诊断结论）

---

## AI配置步骤

### 步骤1：获取三方接口信息

询问客户提供三方报告查询接口文档，或明确以下信息：

**必须信息**：
1. 三方查询接口的入参字段及格式
2. 三方查询接口的响应字段及格式
3. 报告内容的格式（文本/HTML/PDF）
4. 是否支持批量查询

### 步骤2：确认查询条件和查询方式

**确认查询方式**（3选1）：
- **方式1**：通过收费项外部编码（outFeeItemId）查询
- **方式2**：通过申请单号（applyNo）查询 - 最常见
- **方式3**：通过条码号（barCode）查询

**确认必填字段**：
- `serviceProviderType` - 厂商类型（固定为PACS）
- `patientCode` - 患者编号
- `paramType` - 查询方式标识（1/2/3）
- 对应的查询字段列表（根据paramType决定）

### 步骤3：确认响应数据结构

确认三方响应的数据格式：

- **数据结构**：对象还是数组
- **报告内容格式**：文本、HTML、PDF（Base64）
- **必需字段**：哪些字段是必然返回的
- **可选字段**：哪些字段可能为空

### 步骤4：生成前置映射（Jarvis → 三方）

参考上述前置处理映射表

**关键配置**：

1. **确定查询方式**：根据三方接口支持的查询方式，选择对应的映射方案
   - 如果三方支持申请单号查询，使用ApplyNoList → sourceIds
   - 如果三方支持条码号查询，使用BarCodeList → barCodes
   - 如果三方支持收费项编码查询，使用OutFeeItemIdList → outFeeItemIds

2. **ParamType字段**：
   - 使用NAME映射或CONSTANT固定值
   - 值为1（收费项编码）、2（申请单号）或3（条码号）

3. **数组格式**：
   - 查询字段支持数组格式，可批量查询多条报告
   - 确认三方是否支持批量查询

4. **厂商类型**：
   - ServiceProviderType固定为PACS

### 步骤5：生成后置映射（三方 → Jarvis）

参考上述后置处理映射表

**注意**：
- 三方返回的数组需要映射到Jarvis的rsp数组
- serviceProviderType需要从Jarvis入参中获取
- reportStatus和reportPdf根据实际情况设置固定值或从三方字段映射
- 报告内容格式需要根据三方实际格式进行处理

### 步骤6：处理文件相关字段

**文件协议（fileProtocol）解析规则**：

根据三方返回的文件地址，设置对应的协议类型：

| 三方URL特征 | fileProtocol值 | 示例 |
|-----------|---------------|------|
| http:// 开头 | `http` | http://10.192.50.204:8083/report.pdf |
| https:// 开头 | `https` | https://pacs.example.com/report.pdf |
| ftp:// 开头 | `ftp` | ftp://server/report.pdf |
| smb:// 开头或网络路径 | `smb` | smb://10.10.73.95/C13/xxx.pdf |
| Base64编码内容 | `base64` | data:application/pdf;base64,JVBERi0... |
| HTML内容 | `html` | <html><body>...</body></html> |

**映射表达式示例**：

```javascript
// 根据URL前缀判断协议
#data.startsWith('http://') ? 'http' : (#data.startsWith('https://') ? 'https' : (#data.startsWith('ftp://') ? 'ftp' : (#data.startsWith('smb://') ? 'smb' : 'http')))
```

**文件类型（fileType）解析规则**：

根据文件扩展名或三方返回的文件类型字段设置：

| 文件扩展名 | fileType值 |
|----------|------------|
| .pdf | `pdf` |
| .jpg/.jpeg | `jpg` |
| .png | `png` |
| .html/.htm | `html` |
| .doc/.docx | `doc` |

**映射表达式示例**：

```javascript
// 从URL中提取文件扩展名
#data.substring(#data.lastIndexOf('.') + 1).toLowerCase()

// 或者从三方的文件类型字段直接获取
#data['fileType']
```

**重要说明**：
- 这三个字段（fileUrl、fileProtocol、fileType）存在文件时必填
- 如果三方未提供文件，这三个字段可以为空或不传
- 文件类型为`html`时，fileType可不传
- 多个文件URL使用英文逗号分隔

### 步骤7：处理特殊情况

**情况1：三方返回PDF而非文本**

如果三方返回PDF的Base64编码：

| 三方字段 | Jarvis字段 | 映射类型 |
|---------|-----------|----------|
| pdfContent | reportPdf | NAME |
| - | reportContent | CONSTANT（空字符串） |

**情况2：三方返回图片URL列表**

如果三方返回多个图片URL：

| 三方字段 | Jarvis字段 | 映射类型 |
|---------|-----------|----------|
| imageUrls | reportImages | NAME |

**情况3：需要二次调用获取详情**

如果三方需要先查列表再查详情，需要配置两个节点：
1. 第一个节点：查询报告列表
2. 第二个节点：根据报告ID查询详情

### 步骤7：测试验证

配置完成后，使用Mock功能测试：

1. 准备测试数据（患者编号、申请单号）
2. 调用接口验证映射是否正确
3. 检查返回数据格式是否符合预期
4. 验证特殊字符和中文是否正常显示
