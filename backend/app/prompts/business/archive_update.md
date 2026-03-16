---
trigger: model_decision
description: 
---
# 更新档案接口配置指南

> **业务专用指南**：提供更新档案场景的完整配置示例和步骤

---

## 目的

通过HIS档案号更新患者档案信息，支持更新手机号、地址、婚姻状况等可变信息。

---

## 场景识别

当客户提到「更新档案」「修改档案」「档案更新」「更新患者信息」时，明确为更新档案场景。

---

## 业务要点

### 1. 节点关键字配置

**keywordField**：`patientCode`

用于日志检索和问题排查，框架会从Jarvis入参中提取此字段值作为业务关键字记录到调用日志中。

**配置位置**：节点配置的 `keywordField` 字段

### 2. 更新条件

**必须条件**：HIS档案号 (`hisPatientId`)

更新档案必须使用HIS系统分配的档案号作为唯一标识。

### 3. 常见字段转换

更新档案接口常见的值转换场景：

| 字段 | Jarvis值 | HIS可能要求 | 转换示例 |
|------|----------|-------------|----------|
| 性别 | "1"/"2" | "男"/"女" | `#data == '1' ? '男' : '女'` |
| 婚姻 | "1"/"2"/"3" | "未婚"/"已婚"/"未知" | `#data == '1' ? '未婚' : (#data == '2' ? '已婚' : '未知')` |
| 民族 | nation | nationName | 直接使用 `nationName` 字段 |


---

## Jarvis入参

```json
{
  "sex": "2",
  "age": 68,
  "marriage": "3",
  "identitycard": "332625195709260020",
  "cardType": "1",
  "phone": "13819025286",
  "birthday": "1957-09-26",
  "patientName": "丁丰梅",
  "patientCode": "26011900033",
  "nation": "01",
  "nationName": "汉族",
  "hisPatientId": "12856",
  "visitNo": "22809",
  "archivesCode": "10010130",
  "archivalNo": "10010130",
  "userType": 0,
  "patientInfo": {
    "sex": "2",
    "age": 68,
    "marriage": "3",
    "identitycard": "332625195709260020",
    "cardType": "1",
    "patientLevelName": "普通体检人",
    "phone": "13819025286",
    "birthday": "1957-09-26",
    "patientName": "丁丰梅",
    "patientCode": "26011900033",
    "hisPatientId": "12856",
    "visitNo": "22809",
    "userType": 0,
    "orgName": "",
    "registertime": "2026-01-19 14:28:06",
    "physicalTypes": "physical:types:A",
    "physicalTypeName": "健康体检",
    "nation": "01",
    "nationName": "汉族"
  },
  "doctorInfo": {
    "idUser": 670,
    "userName": "张佳洁",
    "number": "8538"
  }
}
```

**关键字段**：
- `patientCode` - keywordField，体检编号
- `hisPatientId` - HIS档案号（**必填**，更新条件）
- `phone` - 手机号（可更新）
- `address` - 家庭地址（可更新）
- `marriage` - 婚姻状况（可更新）
- `nationName` - 民族名称（可更新）

---

## Jarvis出参

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

## 映射配置示例

> **重要说明**：以下示例仅用于说明映射配置方法，实际HIS接口的入参、出参字段必须以客户提供的接口文档或实际出入参为准。

### HIS入参示例

```json
{
  "patientId": "12856",
  "phone": "13819025286",
  "nation": "汉族",
  "cardId": "332625195709260020",
  "name": "丁丰梅",
  "cardType": "1",
  "birthDate": "1957-09-26",
  "age": 68
}
```

### HIS响应示例

```json
{
  "returnCode": "1",
  "errorMessage": "成功"
}
```

### 前置处理映射（Jarvis → HIS）

| Jarvis字段 | 源参数类型 | HIS字段 | 目标参数类型 | 映射类型 | 映射规则 |
|-------------|-----------|----------|-------------|----------|----------|
| hisPatientId | STRING | patientId | STRING | NAME | - |
| patientName | STRING | name | STRING | NAME | - |
| age | INTEGER | age | INTEGER | NAME | - |
| birthday | STRING | birthDate | STRING | NAME | - |
| cardType | STRING | cardType | STRING | NAME | - |
| identitycard | STRING | cardId | STRING | NAME | - |
| phone | STRING | phone | STRING | NAME | - |
| nationName | STRING | nation | STRING | NAME | - |
| sex | STRING | sex | STRING | EXPRESSION | `(#data[sex] == null \|\| #data[sex] == '') ? '未知' : (#data[sex] == '1' ? '男' : (#data[sex] == '2' ? '女' : '未知'))` |
| marriage | STRING | marital | STRING | EXPRESSION | `(#data[marriage] == null \|\| #data[marriage] == '') ? '未知' : (#data[marriage] == '1' ? '未婚' : (#data[marriage] == '2' ? '已婚' : '未知'))` |

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
1. HIS更新档案接口的入参字段及格式
2. HIS更新档案接口的响应字段及格式
3. 哪些字段可以更新，哪些字段不允许更新

### 步骤2：生成前置映射（Jarvis → HIS）

参考上述前置处理映射表

**关键点**：
- 必须使用 `hisPatientId` 作为更新条件
- 字段转换规则参考常见字段转换表

### 步骤3：生成后置映射（HIS → Jarvis）

参考上述后置处理映射表

**关键点**：
- 状态码转换：`returnCode` 1→200，其他→-1

---
