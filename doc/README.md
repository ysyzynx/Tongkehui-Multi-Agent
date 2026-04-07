# 童科绘（TongKeHui）

童科绘是一个面向科普内容生产的多智能体协作平台，覆盖从故事创作、文学润色、科学审查、观众反馈微调、插画生成与审核到排版导出的完整链路。

项目采用前后端分离架构：
- 后端：FastAPI + SQLAlchemy + 多 Agent 协作
- 前端：React + TypeScript + Vite
- 数据层：SQLite（默认）
- 能力扩展：RAG 知识库、维基百科接入、DeepSearch/SerpAPI 可选

## 功能概览

- 故事创作：根据主题和受众自动生成科普故事
- 文学审核：语言风格、可读性和表达润色
- 科学审核：事实校验、术语检查、逻辑验证、来源建议
- 读者反馈：模拟受众反馈并产出 4.0 微调版本
- 插画生成：自动分镜并生成插图提示词/图像
- 插画审核：科学准确性 + 逻辑合理性 + 人物一致性
- 词条增强：正文高亮词条与文末科学解释联动，支持维基补充
- 排版导出：HTML/PDF 发布
- 鉴权体系：服务端用户注册、登录、Token 会话
- 知识库：文档入库、分块索引、检索、统计、批量导入

## 仓库结构

```text
.
├─ main.py                         # FastAPI 应用入口
├─ config/                         # 系统配置
├─ models/                         # SQLAlchemy 模型与 Pydantic schema
├─ router/                         # API 路由层
├─ agent/                          # 各业务 Agent 实现
├─ prompts/                        # Prompt 模板
├─ utils/                          # 通用能力（DB、RAG、外部检索、鉴权等）
├─ tk-frontend/                    # React 前端工程
├─ docs/                           # 文档
├─ requirements.txt                # Python 依赖
├─ start-dev.ps1                   # 一键启动脚本（Windows）
└─ tongkehui.db                    # 默认 SQLite 数据库
```

## 环境要求

- Python 3.10+
- Node.js 18+
- npm 或 pnpm（前端）
- Windows PowerShell（使用 start-dev.ps1 时）

## 快速启动

### 方式一：一键启动（推荐，Windows）

在项目根目录执行：

```powershell
./start-dev.ps1
```

脚本会自动：
1. 清理 8000/5173 端口占用
2. 启动后端（FastAPI）
3. 启动前端（Vite）
4. 打开前端页面和 Swagger 文档

默认地址：
- 前端：http://localhost:5173
- 后端文档：http://localhost:8000/docs

### 方式二：手动启动

后端：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```powershell
cd tk-frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## 核心配置

配置来源：.env（默认由 config/settings.py 读取）

常用配置项：
- DB_URL：数据库连接（默认 sqlite:///./tongkehui.db）
- HOST / PORT：后端监听地址与端口
- DEBUG：开发模式开关
- OPENAI_API_KEY / OPENAI_API_BASE：模型 API
- LLM_MODEL / VISION_MODEL：文本与视觉模型
- DEEPSEARCH_API_KEY / DEEPSEARCH_*：DeepSearch 检索增强
- SERPAPI_API_KEY：Google Scholar 检索（可选）

注意：仓库不提供任何可直接使用的默认密钥，请在本地 .env 中自行填写 OPENAI、DEEPSEARCH、VOLCENGINE、SERPAPI 等密钥。

## 鉴权说明

后端除 /api/auth/* 外默认需要 Bearer Token。

标准流程：
1. 调用 /api/auth/register 注册
2. 调用 /api/auth/login 获取 token
3. 后续请求在 Authorization 头中携带：Bearer <token>
4. 调用 /api/auth/logout 退出并撤销会话

## 主要 API 分组

- 认证：/api/auth/*
- 故事：/api/story/*
- 文学审核：/api/literature/review
- 科学审核：/api/check/verify、/api/check/verify-self-feedback
- 读者反馈：/api/reader/evaluate、/api/reader/refine
- 插画：/api/illustrator/*、/api/illustration-review/review
- 知识库：/api/knowledge/*
- 事实检索与维基：/api/fact/*
- 发布导出：/api/publisher/export-pdf

详细接口可查看：
- docs/API.md
- http://localhost:8000/docs

## 研发与测试

项目包含多组后端测试脚本，示例：

```powershell
python test_backend.py
python test_integration.py
python test_story_creator.py
python test_science_checker.py
python test_reader.py
python test_publisher.py
```

## 常见问题

1. 前端 build 报 TS 未使用变量错误
- 原因：项目中部分页面已有历史告警
- 处理：按报错文件逐步清理未使用导入/变量

2. 无法连接后端
- 检查 8000 端口是否被占用
- 检查虚拟环境和依赖是否安装完整

3. 维基词条未更新
- 检查 /api/fact/wikipedia/search 与 /api/fact/wikipedia/page 是否可用
- 检查网络可达性和 API 超时

## 文档导航

- 综合技术文档：docs/TECHNICAL_DOCUMENTATION.md
- API 文档：docs/API.md
- RAG 使用指南：docs/RAG库完整使用指南.md
- 故障排查：docs/TROUBLESHOOTING.md

## 许可证

当前仓库未声明开源许可证。如需开源，请补充 LICENSE 文件并明确第三方依赖协议。
