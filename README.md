# Interface-Agent AI（接口配置化 Agent）

这是一个面向“领域接口配置化交付”的智能 Agent 项目，核心目标不是聊天本身，而是把领域接口对接工作从“写大量定制代码”升级为“可配置、可验证、可复用”的流程化交付。

一句话定位：  
**把上游系统与下游系统之间的接口对接，尽量收敛成标准配置；无法配置时，明确给出 SPI 扩展方案。**

## 典型使用场景

本 Agent 适用于医院信息化等多系统对接场景（如 HIS / LIS / PACS / 统一支付相关）：

- 新增接口时，先判断“是否可配置化”
- 可配置化时，自动生成节点、映射与工作流配置
- 不可配置化时，产出 SPI 扩展建议与实现方向
- 通过 Mock 与日志字段完成结果验证，降低上线风险

已覆盖的业务场景示例包括：

- 档案类：建档、查档、更新档案
- 账单类：账单创建、删除、拟退、支付/退费状态查询
- 通知类：收费通知、退费通知、报告状态通知
- 申请单/报告类：申请单创建、PACS/LIS 报告查询

## Agent 的核心能力

- 统一入口路由：通过 `interfaceUri` 匹配工作流
- 协议适配：支持 `HTTP` / `WEBSERVICE` / `DATABASE`
- 双向映射：支持 `PRE_PROCESS` 与 `POST_PROCESS` 参数转换
- 流程编排：基于工作流组织多节点执行与调度
- 边界判定：给出“可配置化 / 需 SPI / 不支持”的明确结论

## 项目结构

```text
interface-agent-ai/
├── backend/
│   ├── app/
│   │   ├── agents/      # Agent 运行与编排逻辑
│   │   ├── api/         # FastAPI 服务与流式接口
│   │   ├── prompts/     # 规则、场景知识与执行模板
│   │   └── static/      # 前端构建产物目录
│   └── requirements.txt
└── frontend/
    ├── src/
    ├── package.json
    └── vite.config.js
```

## 快速启动

环境要求：

- Python 3.10+
- Node.js 18+

启动后端：

```bash
cd backend
pip install -r requirements.txt
python app/api/main.py
```

后端默认地址：`http://127.0.0.1:8001`

启动前端开发环境：

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：`http://127.0.0.1:5173`

生产构建前端：

```bash
cd frontend
npm run build
```

构建产物输出到：`backend/app/static`

## 接口说明

- `POST /api/chat`：流式返回 Agent 处理结果
- `GET /health`：健康检查
- `GET /`：返回前端页面（已构建时）

## 当前状态说明

- 前端目录已整理为单层 `frontend/`，不再使用重复的 `frontend/frontend/` 结构
