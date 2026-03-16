---
trigger: model_decision
description: 
---
# 档案创建接口配置指南

> **业务专用指南**：提供档案创建（建档）场景的完整配置示例和步骤

---

## 目的

在HIS系统中创建患者档案信息，获取HIS分配的患者ID（档案号）和就诊号，用于后续业务流程。

---

## 场景识别

当客户提到「建档」「创建档案」「患者登记」「挂号建档」时，明确为档案创建场景。

---

## 业务要点

### 1. 节点关键字配置

**keywordField**：`patientCode`

用于日志检索和问题排查，框架会从Jarvis入参中提取此字段值作为业务关键字记录到调用日志中。

**配置位置**：节点配置的 `keywordField` 字段

### 2. 常见字段转换

建档接口常见的值转换场景：

| 字段 | Jarvis值 | his可能要求 | 转换示例 |
|------|----------|-------------|----------|
| 性别 | "1"/"2" | "男"/"女" | `#data == '1' ? '男' : '女'` |
| 婚姻 | "1"/"2" | "未婚"/"已婚" | `#data == '1' ? '未婚' : '已婚'` |
| 证件类型 | "1" | "0" | `#data == "1" ? "0" : "1"` |
| 体检类型 | 0/1 | "1"/"2" | `#data == 0 ? "1" : "2"` |

### 3. 嵌套字段提取

Jarvis入参中部分字段在嵌套对象内，需用EXPRESSION提取：

| 目标 | 来源 | 映射规则 |
|------|------|----------|
| 操作员ID | `doctorInfo.number` | `#data[number]` |
| 操作员姓名 | `doctorInfo.userName` | `#data[userName]` |
| 登记时间 | `patientInfo.registertime` | `#data[registertime]` |
| 单位ID | `patientInfo.hisOrgId` | `#data[hisOrgId]` |

---

## Jarvis入参

```json
{
  "sex": "2",
  "age": 53,
  "marriage": "2",
  "identitycard": "330511197202254629",
  "cardType": "1",
  "phone": "13059970500",
  "birthday": "1972-02-25",
  "address": "湖州",
  "patientName": "测试账号",
  "patientCode": "2509050001",
  "nation": "01",
  "nationName": "汉族",
  "hisPatientId": null,
  "visitNo": null,
  "archivesCode": "10011081",
  "archivalNo": "10011081",
  "userType": 1,
  "orgName": "测试单位",
  "patientInfo": {
    "sex": "2",
    "vpInvoiceTitle": null,
    "vpSocialCode": null,
    "age": 53,
    "marriage": "2",
    "identitycard": "330511197202254629",
    "cardType": "1",
    "patientLevelName": "普通体检人",
    "phone": "13059970500",
    "birthday": "1972-02-25",
    "hisOrgId": "85330",
    "address": "湖州",
    "patientName": "莫伟文",
    "patientCode": "2508190082",
    "hisPatientId": null,
    "visitNo": null,
    "userType": 1,
    "orgName": "湖州市机关单位",
    "registertime": "2025-08-19 08:28:01",
    "physicalTypes": "physical:types:A",
    "physicalTypeName": "健康体检"
  },
  "doctorInfo": {
    "idUser": 705,
    "userName": "陈元梅",
    "number": "cym0555",
    "loginName": null
  }
}
```

**关键字段**：
- `patientCode` - keywordField，体检编号
- `identitycard` - 身份证号（必填）
- `patientName` - 患者姓名（必填）
- `sex` - 性别（常需转换为中文）
- `marriage` - 婚姻状况（常需转换为中文）
- `doctorInfo.number` - 操作员编号（从嵌套对象提取）
- `patientInfo.hisOrgId` - 单位ID（从嵌套对象提取）
- `hisPatientId` / `visitNo` - 建档前为null，后置映射时回填

---

## Jarvis出参

```json
{
  "code": "200",
  "message": "成功",
  "rsp": {
    "outPatientCode": "his客户ID",
    "visitNo": "就诊卡号"
  }
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| code | 状态码，200成功 |
| message | 响应消息 |
| rsp.outPatientCode | HIS分配的患者档案号 |
| rsp.visitNo | HIS分配的就诊号 |

---

## 映射配置示例

> **重要说明**：以下示例仅用于说明映射配置方法，实际HIS接口的入参、出参字段必须以客户提供的接口文档或实际出入参为准。

### HIS入参示例

```json
{
  "name": "测试账号",
  "sex": "女",
  "idCard": "330511197202254629",
  "phone": "13059970500",
  "birthday": "1972-02-25",
  "marriage": "已婚",
  "address": "湖州",
  "operatorId": "cym0555",
  "operatorName": "陈元梅",
  "orgId": "85330",
  "type": "1"
}
```

### HIS响应示例

```json
{
  "returnCode": "1",
  "errorMessage": "",
  "data": {
    "patientId": "P20250905001",
    "clinicId": "V202509050001",
    "name": "测试账号",
    "idCard": "330511197202254629"
  }
}
```

### 前置处理映射（Jarvis → HIS）

| Jarvis字段 | 源参数类型 | HIS字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| patientName | STRING | name | STRING | NAME | - |
| identitycard | STRING | idCard | STRING | NAME | - |
| phone | STRING | phone | STRING | NAME | - |
| birthday | STRING | birthday | STRING | NAME | - |
| address | STRING | address | STRING | NAME | - |
| sex | STRING | sex | STRING | EXPRESSION | `#data == '1' ? '男' : '女'` |
| marriage | STRING | marriage | STRING | EXPRESSION | `#data == '1' ? '未婚' : '已婚'` |
| doctorInfo | OBJECT | operatorId | STRING | EXPRESSION | `#data['number']` |
| doctorInfo | OBJECT | operatorName | STRING | EXPRESSION | `#data['userName']` |
| patientInfo | OBJECT | orgId | STRING | EXPRESSION | `#data['hisOrgId']` |
| - | NONE | type | STRING | CONSTANT | `"1"` |


### 后置处理映射（HIS → Jarvis）

| HIS字段 | 源参数类型 | Jarvis字段 | 目标参数类型 | 映射类型 | 映射数据源 | 映射规则 |
|---------|-----------|-------------|-------------|----------|-----------|----------|
| returnCode | STRING | code | STRING | EXPRESSION | RESPONSE | `#data == "1" ? "200" : "-1"` |
| errorMessage | STRING | message | STRING | NAME | RESPONSE | - |
| data | OBJECT | rsp | OBJECT | NAME | RESPONSE | 嵌套映射 |
| └─ patientId | STRING | └─ outPatientCode | STRING | NAME | RESPONSE | - |
| └─ clinicId | STRING | └─ visitNo | STRING | NAME | RESPONSE | - |

---

## AI配置步骤

### 步骤1：获取HIS接口信息

询问客户提供HIS接口文档，或明确以下信息：

**必须信息**：
1. HIS建档接口的入参字段及格式
2. HIS建档接口的响应字段及格式

### 步骤2：生成前置映射（Jarvis → HIS）

参考上述前置处理映射表

### 步骤3：生成后置映射（HIS → Jarvis）

参考上述后置处理映射表
