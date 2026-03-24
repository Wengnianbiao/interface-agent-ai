---
name: spi-extension
description: 为无法配置化的接口场景生成 SPI 扩展代码，支持动态签名、动态Token、特殊加密等场景
---

# SPI 扩展 Skill

> 为无法配置化的接口场景生成 SPI 扩展代码

---

## 使用场景

- 可行性评估结果为"需要 SPI 扩展"
- 用户要求编写扩展代码
- 常见场景：动态签名、动态 Token、特殊加密、参数转换

---

## SPI 扩展机制

### 核心接口

```java
@AgentSPI("default")
public interface InterfaceRemoteInvoker {
    @AgentAdaptive("remoteExtension")
    Map<String, Object> remoteInvoke(WorkflowNode flowNode, Invocation invocation);
}
```

### 扩展方式

1. **直接实现接口**：`implements InterfaceRemoteInvoker`
2. **实现 remoteInvoke 方法**：完整控制调用流程
3. **节点配置**：`remoteExtension` 字段指定扩展名

---

## 标准流程

SPI 扩展的本质：**转换上游入参 → 封装三方接口入参 → 调用 → 接收响应 → 记录日志 → 转换响应 → 记录调用时间**

```
┌─────────────────────────────────────────────────────────────┐
│  1. 获取上游入参 invocation.getBusinessData()               │
│  2. 记录开始时间 startTime                                  │
│  3. 转换入参为下游格式 convertToDownstreamParam()           │
│  4. 收集调用前日志 LogCollector.collectParamBeforeInvoke()  │
│  5. 发起 HTTP 请求 HttpUtils.post(url, requestJson)         │
│  6. 收集响应日志 LogCollector.collectRemoteInvokeResponse() │
│  7. 转换响应为上游格式                                      │
│  8. 异常处理 catch → LogCollector.collectError()            │
│  9. finally 记录调用时间 LogCollector.collectInvokeTime()   │
└─────────────────────────────────────────────────────────────┘
```

---

## 框架工具类

| 工具类 | 用途 | 常用方法 |
|--------|------|----------|
| `HttpUtils` | HTTP 请求 | `post(url, body)`, `get(url)`, `postForm(url, params)` |
| `JsonUtils` | JSON 处理 | `toJsonString(obj)`, `fromJsonStringToObjectMap(json)`, `parseMetaInfo(str)` |
| `LogCollector` | 日志收集 | `collectParamBeforeInvoke()`, `collectRemoteInvokeResponse()`, `collectInvokeTime()`, `collectError()` |

---

## 代码模板

### 基础模板（参数转换场景）

```java
package com.helianhealth.agent.extension;

import com.helianhealth.agent.common.utils.JsonUtils;
import com.helianhealth.agent.invocation.context.LogCollector;
import com.helianhealth.agent.invocation.remote.InterfaceRemoteInvoker;
import com.helianhealth.agent.invocation.utils.HttpUtils;
import com.helianhealth.agent.repository.model.domain.WorkflowNode;
import com.helianhealth.agent.invocation.remote.model.Invocation;
import lombok.extern.slf4j.Slf4j;
import org.apache.hc.core5.http.ParseException;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/**
 * SPI 扩展示例
 * 使用方式：节点 remoteExtension 配置为 "example"
 */
@Slf4j
public class ExampleInvoker implements InterfaceRemoteInvoker {

    @Override
    public Map<String, Object> remoteInvoke(WorkflowNode flowNode, Invocation invocation) {
        // 1. 获取上游业务入参
        Map<String, Object> businessData = invocation.getBusinessData();
        long startTime = System.currentTimeMillis();

        try {
            // 2. 转换入参为下游接口格式
            Map<String, Object> request = convertToDownstreamParam(businessData);
            String requestJson = JsonUtils.toJsonString(request);
            
            // 3. 收集调用前日志
            LogCollector.collectParamBeforeInvoke(requestJson);
            
            // 4. 获取节点 URL
            Map<String, Object> metaInfo = JsonUtils.parseMetaInfo(flowNode.getMetaInfo());
            String url = (String) metaInfo.get("url");

            // 5. 发起 HTTP POST 请求
            String responseJson = HttpUtils.post(url, requestJson);
            
            // 6. 收集调用后日志
            LogCollector.collectRemoteInvokeResponse(responseJson);

            // 7. 转换响应为上游格式
            Map<String, Object> response = JsonUtils.fromJsonStringToObjectMap(responseJson);
            return convertToUpstreamResponse(response);

        } catch (IOException | ParseException e) {
            log.error("调用远程接口失败", e);
            LogCollector.collectError(e.getMessage());
            
            Map<String, Object> result = new HashMap<>();
            result.put("code", "500");
            result.put("message", "调用失败：" + e.getMessage());
            return result;
        } finally {
            // 8. 记录调用耗时
            long durationMs = System.currentTimeMillis() - startTime;
            LogCollector.collectInvokeTime(durationMs);
        }
    }

    /**
     * 将上游入参转换为下游接口格式
     */
    private Map<String, Object> convertToDownstreamParam(Map<String, Object> upstreamData) {
        Map<String, Object> downstreamParam = new HashMap<>();
        
        // TODO: 根据实际业务进行字段映射
        // 示例：downstreamParam.put("targetField", upstreamData.get("sourceField"));
        downstreamParam.putAll(upstreamData);
        
        return downstreamParam;
    }

    /**
     * 将下游响应转换为上游格式
     */
    private Map<String, Object> convertToUpstreamResponse(Map<String, Object> downstreamResponse) {
        Map<String, Object> result = new HashMap<>();
        
        // TODO: 根据实际业务提取响应字段
        result.put("code", downstreamResponse.get("code"));
        result.put("message", downstreamResponse.get("message"));
        
        return result;
    }
}
```

### 动态签名扩展

```java
package com.helianhealth.agent.extension;

import com.helianhealth.agent.common.utils.JsonUtils;
import com.helianhealth.agent.invocation.context.LogCollector;
import com.helianhealth.agent.invocation.remote.InterfaceRemoteInvoker;
import com.helianhealth.agent.invocation.utils.HttpUtils;
import com.helianhealth.agent.repository.model.domain.WorkflowNode;
import com.helianhealth.agent.invocation.remote.model.Invocation;
import lombok.extern.slf4j.Slf4j;
import org.apache.hc.core5.http.ParseException;

import java.io.IOException;
import java.security.MessageDigest;
import java.util.HashMap;
import java.util.Map;

/**
 * 动态签名扩展
 * 使用方式：节点 remoteExtension 配置为 "dynamic-sign"
 */
@Slf4j
public class DynamicSignInvoker implements InterfaceRemoteInvoker {

    @Override
    public Map<String, Object> remoteInvoke(WorkflowNode flowNode, Invocation invocation) {
        Map<String, Object> businessData = invocation.getBusinessData();
        long startTime = System.currentTimeMillis();

        try {
            // 1. 获取签名密钥
            Map<String, String> extParams = flowNode.getExtensionParam();
            String secretKey = extParams.getOrDefault("secretKey", "default_secret");
            
            // 2. 转换入参
            Map<String, Object> request = convertToDownstreamParam(businessData);
            String requestJson = JsonUtils.toJsonString(request);
            
            // 3. 生成签名
            long timestamp = System.currentTimeMillis();
            String sign = generateSign(requestJson, timestamp, secretKey);
            
            // 4. 收集调用前日志
            LogCollector.collectParamBeforeInvoke(requestJson);
            
            // 5. 构建带签名的请求头
            Map<String, Object> metaInfo = JsonUtils.parseMetaInfo(flowNode.getMetaInfo());
            String url = (String) metaInfo.get("url");
            Map<String, String> headers = new HashMap<>();
            headers.put("Content-Type", "application/json");
            headers.put("X-Sign", sign);
            headers.put("X-Timestamp", String.valueOf(timestamp));

            // 6. 发起请求
            String responseJson = HttpUtils.post(url, headers, requestJson);
            LogCollector.collectRemoteInvokeResponse(responseJson);

            // 7. 转换响应
            Map<String, Object> response = JsonUtils.fromJsonStringToObjectMap(responseJson);
            return convertToUpstreamResponse(response);

        } catch (IOException | ParseException e) {
            log.error("调用远程接口失败", e);
            LogCollector.collectError(e.getMessage());
            return buildErrorResponse(e.getMessage());
        } finally {
            LogCollector.collectInvokeTime(System.currentTimeMillis() - startTime);
        }
    }
    
    private String generateSign(String body, long timestamp, String secret) {
        try {
            String content = body + timestamp + secret;
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] digest = md.digest(content.getBytes());
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            throw new RuntimeException("签名生成失败", e);
        }
    }
    
    private Map<String, Object> convertToDownstreamParam(Map<String, Object> upstreamData) {
        // TODO: 实现入参转换逻辑
        return new HashMap<>(upstreamData);
    }
    
    private Map<String, Object> convertToUpstreamResponse(Map<String, Object> response) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", response.get("code"));
        result.put("message", response.get("message"));
        return result;
    }
    
    private Map<String, Object> buildErrorResponse(String message) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", "500");
        result.put("message", "调用失败：" + message);
        return result;
    }
}
```

### 动态 Token 扩展

```java
package com.helianhealth.agent.extension;

import com.helianhealth.agent.common.utils.JsonUtils;
import com.helianhealth.agent.invocation.context.LogCollector;
import com.helianhealth.agent.invocation.remote.InterfaceRemoteInvoker;
import com.helianhealth.agent.invocation.utils.HttpUtils;
import com.helianhealth.agent.repository.model.domain.WorkflowNode;
import com.helianhealth.agent.invocation.remote.model.Invocation;
import lombok.extern.slf4j.Slf4j;
import org.apache.hc.core5.http.ParseException;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 动态 Token 扩展
 * 使用方式：节点 remoteExtension 配置为 "dynamic-token"
 */
@Slf4j
public class DynamicTokenInvoker implements InterfaceRemoteInvoker {

    private static final Map<String, TokenInfo> TOKEN_CACHE = new ConcurrentHashMap<>();

    @Override
    public Map<String, Object> remoteInvoke(WorkflowNode flowNode, Invocation invocation) {
        Map<String, Object> businessData = invocation.getBusinessData();
        long startTime = System.currentTimeMillis();

        try {
            // 1. 获取 Token 配置
            Map<String, String> extParams = flowNode.getExtensionParam();
            String tokenUrl = extParams.get("tokenUrl");
            String clientId = extParams.get("clientId");
            String clientSecret = extParams.get("clientSecret");
            
            // 2. 获取有效 Token
            String token = getValidToken(tokenUrl, clientId, clientSecret);
            
            // 3. 转换入参
            Map<String, Object> request = convertToDownstreamParam(businessData);
            String requestJson = JsonUtils.toJsonString(request);
            LogCollector.collectParamBeforeInvoke(requestJson);
            
            // 4. 构建带 Token 的请求头
            Map<String, Object> metaInfo = JsonUtils.parseMetaInfo(flowNode.getMetaInfo());
            String url = (String) metaInfo.get("url");
            Map<String, String> headers = new HashMap<>();
            headers.put("Content-Type", "application/json");
            headers.put("Authorization", "Bearer " + token);

            // 5. 发起请求
            String responseJson = HttpUtils.post(url, headers, requestJson);
            LogCollector.collectRemoteInvokeResponse(responseJson);

            // 6. 转换响应
            Map<String, Object> response = JsonUtils.fromJsonStringToObjectMap(responseJson);
            return convertToUpstreamResponse(response);

        } catch (IOException | ParseException e) {
            log.error("调用远程接口失败", e);
            LogCollector.collectError(e.getMessage());
            return buildErrorResponse(e.getMessage());
        } finally {
            LogCollector.collectInvokeTime(System.currentTimeMillis() - startTime);
        }
    }
    
    private String getValidToken(String tokenUrl, String clientId, String clientSecret) {
        String cacheKey = clientId + "_" + tokenUrl;
        TokenInfo cached = TOKEN_CACHE.get(cacheKey);
        
        if (cached != null && !cached.isExpired()) {
            return cached.token;
        }
        
        try {
            // 请求新 Token
            Map<String, String> params = new HashMap<>();
            params.put("client_id", clientId);
            params.put("client_secret", clientSecret);
            params.put("grant_type", "client_credentials");
            
            String responseStr = HttpUtils.post(tokenUrl, JsonUtils.toJsonString(params));
            Map<String, Object> response = JsonUtils.fromJsonStringToObjectMap(responseStr);
            
            String token = (String) response.get("access_token");
            int expiresIn = response.get("expires_in") != null 
                    ? ((Number) response.get("expires_in")).intValue() : 3600;
            
            TOKEN_CACHE.put(cacheKey, new TokenInfo(token, expiresIn));
            return token;
        } catch (Exception e) {
            log.error("获取 Token 失败, tokenUrl={}", tokenUrl, e);
            throw new RuntimeException("获取 Token 失败", e);
        }
    }
    
    private Map<String, Object> convertToDownstreamParam(Map<String, Object> upstreamData) {
        return new HashMap<>(upstreamData);
    }
    
    private Map<String, Object> convertToUpstreamResponse(Map<String, Object> response) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", response.get("code"));
        result.put("message", response.get("message"));
        return result;
    }
    
    private Map<String, Object> buildErrorResponse(String message) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", "500");
        result.put("message", "调用失败：" + message);
        return result;
    }
    
    private static class TokenInfo {
        final String token;
        final long expireTime;
        
        TokenInfo(String token, int expiresIn) {
            this.token = token;
            this.expireTime = System.currentTimeMillis() + (expiresIn - 60) * 1000L;
        }
        
        boolean isExpired() {
            return System.currentTimeMillis() > expireTime;
        }
    }
}
```

### AES 加密扩展

```java
package com.helianhealth.agent.extension;

import com.helianhealth.agent.common.utils.JsonUtils;
import com.helianhealth.agent.invocation.context.LogCollector;
import com.helianhealth.agent.invocation.remote.InterfaceRemoteInvoker;
import com.helianhealth.agent.invocation.utils.HttpUtils;
import com.helianhealth.agent.repository.model.domain.WorkflowNode;
import com.helianhealth.agent.invocation.remote.model.Invocation;
import lombok.extern.slf4j.Slf4j;
import org.apache.hc.core5.http.ParseException;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import java.io.IOException;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

/**
 * AES 加密扩展
 * 使用方式：节点 remoteExtension 配置为 "aes-encrypt"
 */
@Slf4j
public class AesEncryptInvoker implements InterfaceRemoteInvoker {

    @Override
    public Map<String, Object> remoteInvoke(WorkflowNode flowNode, Invocation invocation) {
        Map<String, Object> businessData = invocation.getBusinessData();
        long startTime = System.currentTimeMillis();

        try {
            // 1. 获取加密密钥
            Map<String, String> extParams = flowNode.getExtensionParam();
            String aesKey = extParams.get("aesKey");
            
            // 2. 转换并加密入参
            Map<String, Object> request = convertToDownstreamParam(businessData);
            String requestJson = JsonUtils.toJsonString(request);
            String encryptedData = encrypt(requestJson, aesKey);
            
            // 3. 构建加密请求体
            Map<String, Object> encryptedRequest = new HashMap<>();
            encryptedRequest.put("encryptedData", encryptedData);
            String encryptedRequestJson = JsonUtils.toJsonString(encryptedRequest);
            LogCollector.collectParamBeforeInvoke(encryptedRequestJson);
            
            // 4. 发起请求
            Map<String, Object> metaInfo = JsonUtils.parseMetaInfo(flowNode.getMetaInfo());
            String url = (String) metaInfo.get("url");
            String responseJson = HttpUtils.post(url, encryptedRequestJson);
            LogCollector.collectRemoteInvokeResponse(responseJson);

            // 5. 解密响应（如果需要）
            Map<String, Object> response = JsonUtils.fromJsonStringToObjectMap(responseJson);
            if (response.containsKey("encryptedResponse")) {
                String decrypted = decrypt((String) response.get("encryptedResponse"), aesKey);
                response = JsonUtils.fromJsonStringToObjectMap(decrypted);
            }
            
            return convertToUpstreamResponse(response);

        } catch (IOException | ParseException e) {
            log.error("调用远程接口失败", e);
            LogCollector.collectError(e.getMessage());
            return buildErrorResponse(e.getMessage());
        } finally {
            LogCollector.collectInvokeTime(System.currentTimeMillis() - startTime);
        }
    }
    
    private String encrypt(String content, String key) {
        try {
            SecretKeySpec keySpec = new SecretKeySpec(key.getBytes(), "AES");
            Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
            cipher.init(Cipher.ENCRYPT_MODE, keySpec);
            byte[] encrypted = cipher.doFinal(content.getBytes());
            return Base64.getEncoder().encodeToString(encrypted);
        } catch (Exception e) {
            throw new RuntimeException("加密失败", e);
        }
    }
    
    private String decrypt(String content, String key) {
        try {
            SecretKeySpec keySpec = new SecretKeySpec(key.getBytes(), "AES");
            Cipher cipher = Cipher.getInstance("AES/ECB/PKCS5Padding");
            cipher.init(Cipher.DECRYPT_MODE, keySpec);
            byte[] decrypted = cipher.doFinal(Base64.getDecoder().decode(content));
            return new String(decrypted);
        } catch (Exception e) {
            throw new RuntimeException("解密失败", e);
        }
    }
    
    private Map<String, Object> convertToDownstreamParam(Map<String, Object> upstreamData) {
        return new HashMap<>(upstreamData);
    }
    
    private Map<String, Object> convertToUpstreamResponse(Map<String, Object> response) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", response.get("code"));
        result.put("message", response.get("message"));
        return result;
    }
    
    private Map<String, Object> buildErrorResponse(String message) {
        Map<String, Object> result = new HashMap<>();
        result.put("code", "500");
        result.put("message", "调用失败：" + message);
        return result;
    }
}
```

---

## 节点配置示例

```json
{
  "nodeName": "需要签名的HIS接口",
  "nodeType": "HTTP",
  "metaInfo": "{\"url\":\"http://his.example.com/api\"}",
  "remoteExtension": "dynamic-sign",
  "extensionParam": "{\"secretKey\":\"your_secret_key\"}"
}
```

---

## 扩展注册

### 方式一：项目代码注册

将扩展类放到 `agent-web/src/main/java/com/helianhealth/agent/extension/` 目录，框架会自动扫描加载。

### 方式二：在线注册（通过控制台）

使用节点扩展配置表 `node_extension_config` 注册：

```sql
INSERT INTO node_extension_config 
(node_id, spi_interface, extension_name, class_name, source_code, enabled, extension_mode)
VALUES 
('[8]', 
 'com.helianhealth.agent.invocation.remote.InterfaceRemoteInvoker',
 'dynamic-sign',
 'com.helianhealth.agent.extension.DynamicSignInvoker',
 '-- Java源码 --',
 1,
 'ONLINE');
```

---

## 生成代码输出

```
✅ SPI 扩展代码已生成！

扩展名称：dynamic-sign
扩展类：DynamicSignInvoker
功能：动态 MD5 签名

使用方式：
1. 将代码放到 agent-web/src/main/java/com/helianhealth/agent/extension/
2. 节点配置 remoteExtension: "dynamic-sign"
3. 节点配置 extensionParam: {"secretKey": "xxx"}
```
