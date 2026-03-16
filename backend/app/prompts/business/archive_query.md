---
trigger: model_decision
description: 
---
# 查询档案接口配置指南

> **业务专用指南**：提供查询档案场景的完整配置示例和步骤

---

## 目的

通过身份证号或卡号在HIS系统查询患者档案信息，获取HIS档案号和就诊号。

---

## 场景识别

当客户提到「查询档案」「查询患者」「档案查询」「获取HIS档案」时，明确为查询档案场景。

---

## 业务要点

### 1. 节点关键字配置

**keywordField**：`patientCode`

用于日志检索和问题排查，框架会从Jarvis入参中提取此字段值作为业务关键字记录到调用日志中。

**配置位置**：节点配置的 `keywordField` 字段

### 2. 查询条件

三方厂商通常支持多种查询条件，建议优先级：

1. **身份证号** - 首选查询条件
2. **手机号** - 身份证为空时使用

**AI处理**：根据HIS接口文档确定具体查询字段名和逻辑。

### 3. 响应数据

HIS通常返回**对象**，如果是数组的话无非映射类型为数组，框架默认会使用数组的首个元素，包含患者基本信息：

```json
{
  "returnCode": "1",
  "errorMessage": "",
  "data": {
    "patientId": "20251211173345329428",
    "clinicId": "727933",
    "name": "肖文涛",
    "idCard": "420116199410140010"
  }
}
```

**关键字段映射**：

| HIS字段 | Jarvis字段 | 说明 |
|---------|-----------|------|
| patientId | rsp.outPatientCode | 档案号 |
| clinicId | rsp.visitNo | 就诊号 |

---

## Jarvis入参

```json
{
  "sex": "1",
  "age": 31,
  "marriage": "1",
  "identitycard": "420116199410140010",
  "cardType": "1",
  "phone": "18898563674",
  "birthday": "1994-10-14",
  "patientName": "肖文涛",
  "patientCode": "26011300006",
  "nation": "01",
  "nationName": "汉族",
  "archivesCode": "10000001",
  "archivalNo": "10000001",
  "userType": 0,
  "patientInfo": {
    "sex": "1",
    "age": 31,
    "marriage": "1",
    "identitycard": "420116199410140010",
    "cardType": "1",
    "patientLevelName": "普通体检人",
    "phone": "18898563674",
    "birthday": "1994-10-14",
    "patientName": "肖文涛",
    "patientCode": "26011300006",
    "userType": 0,
    "orgName": "",
    "registertime": "2026-01-13 17:09:08",
    "physicalTypes": "physical:types:A",
    "physicalTypeName": "健康体检",
    "nation": "01",
    "nationName": "汉族"
  },
  "doctorInfo": {
    "idUser": 625,
    "userName": "谢德才",
    "number": "2541"
  }
}
```


---

## Jarvis出参

```json
{
  "code": "200",
  "message": "",
  "rsp": {
    "outPatientCode": "20251211173345329428",
    "visitNo": "727933"
  }
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| code | 状态码，200成功 |
| message | 响应消息 |
| rsp.outPatientCode | HIS档案号 |
| rsp.visitNo | HIS就诊号 |

---

## 映射配置示例

> **重要说明**：以下示例仅用于说明映射配置方法，实际HIS接口的入参、出参字段必须以客户提供的接口文档或实际出入参为准。

### HIS入参示例

```json
{
  "filterContent": "420116199410140010",
  "filterType": "1"
}
```

### HIS响应示例

```json
{
  "returnCode": "1",
  "errorMessage": "",
  "data": {
    "patientId": "20251211173345329428",
    "clinicId": "727933",
    "name": "肖文涛",
    "idCard": "420116199410140010"
  }
}
```

### 前置处理映射（Jarvis → HIS）

| Jarvis字段 | 源参数类型 | HIS字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| identitycard/phone | STRING | filterContent | STRING | EXPRESSION | `(#data['identitycard'] != null && #data['identitycard'] != '') ? #data['identitycard'] : #data['phone']` |
| - | NONE | filterType | STRING | EXPRESSION | `(#data['identitycard'] != null && #data['identitycard'] != '') ? '1' : '2'` |

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
1. HIS查询接口的入参字段及格式
2. HIS查询接口的响应字段及格式

### 步骤2：生成前置映射（Jarvis → HIS）

参考上述前置处理映射表

### 步骤3：生成后置映射（HIS → Jarvis）

参考上述后置处理映射表
