# 童科绘（TongKeHui Multi-Agent）

童科绘是一个面向科普内容创作的多智能体协作平台。它把一篇科普绘本或科普文章的生产过程拆成多个可控阶段：选题、故事生成、文学润色、科学审查、读者反馈、插画生成、插画审核、排版导出，并通过 RAG 知识库和知识图谱能力提升内容的事实可靠性与知识组织能力。

本仓库采用前后端分离架构：

- 后端：FastAPI、SQLAlchemy、Pydantic
- 前端：React、TypeScript、Vite
- 数据库：SQLite 本地回退，PostgreSQL 可作为生产主库
- AI 能力：多智能体协作、LLM 生成、视觉模型分析、文生图、RAG、知识图谱

---

## 中文说明

### 项目背景

科普内容创作通常需要同时满足三个要求：

- 内容要有趣，适合目标年龄段和目标受众阅读。
- 科学事实要准确，不能只依赖大模型自由生成。
- 图文表达要统一，插画既要好看，也要符合科学常识和故事情节。

童科绘的目标是把这些要求拆解成一条可检查、可回退、可继续优化的 AI 辅助工作流，让创作者可以在每个阶段查看结果、采纳建议并继续推进。

### 核心功能

- 故事创作：根据主题、标题、受众、风格和字数要求生成科普故事。
- 标题建议：根据主题自动生成多个差异化标题灵感。
- 文学审核：优化叙事节奏、语言风格、可读性和受众适配。
- 科学审核：检查事实准确性、术语使用、科学逻辑和引用来源建议。
- 自反馈科学审核：支持迭代式科学审查流程，用于更深入的事实校验。
- 读者反馈：模拟目标读者阅读体验，并根据反馈生成微调版本。
- 插画生成：将故事拆分为分镜，生成绘画提示词和图片结果。
- 插画审核：检查插画的科学准确性、人物一致性和画面逻辑。
- 知识库：支持权威资料入库、分块索引、关键词/向量混合检索。
- 知识图谱：支持实体抽取、关系抽取、邻居查询、子图展示和路径查询。
- 发布导出：支持将最终内容导出为 PDF 或长图。
- 用户系统：支持注册、登录、Bearer Token 鉴权和用户级 LLM 配置。

### 系统流程

```text
用户输入主题、受众、风格、字数
        |
        v
故事生成 StoryCreatorAgent
        |
        v
文学审核 LiteratureCheckerAgent
        |
        v
科学审核 ScienceCheckerAgent + RAG / DeepSearch
        |
        v
读者反馈 ReaderAgent
        |
        v
绘画设定与插画生成 IllustratorAgent
        |
        v
插画审核 IllustrationReviewerAgent
        |
        v
排版导出 Publisher
```

前端编辑器按照上述流程组织页面，用户可以逐步完成创作，也可以查看每个阶段的结果并继续调整。

### 技术架构

```text
.
├─ main.py                  # FastAPI 应用入口
├─ pipeline_runner.py        # 早期/离线交互式流水线脚本
├─ agent/                   # 多智能体业务逻辑
├─ router/                  # 后端 API 路由
├─ models/                  # SQLAlchemy ORM 与 Pydantic Schema
├─ utils/                   # 数据库、LLM、RAG、鉴权、知识图谱、导出工具
├─ prompts/                 # 各 Agent 使用的提示词模板
├─ config/                  # 配置、CORS、标签体系
├─ scripts/                 # 数据初始化、迁移、部署打包脚本
├─ doc/                     # 项目文档
├─ tk-frontend/             # React + TypeScript + Vite 前端
├─ requirements.txt         # Python 后端依赖
├─ start-dev.ps1            # Windows 开发环境一键启动脚本
└─ start-all.ps1            # 启动指引脚本
```

### 后端模块

后端入口是 `main.py`，负责初始化 FastAPI 应用、创建数据库表、注册路由和执行启动自检。

主要目录说明：

- `router/`：API 层，按业务模块拆分，例如 `story_router.py`、`check_router.py`、`knowledge_router.py`、`kg_router.py`。
- `agent/`：智能体层，每个创作阶段对应一个 Agent。
- `utils/llm_client.py`：统一封装文本模型、视觉模型和文生图模型调用。
- `utils/fact_rag.py`：知识库文档分块、索引和检索。
- `utils/kg_builder.py`：从文本、知识库或维基百科中抽取知识图谱实体与关系。
- `utils/auth.py`：用户注册登录、Token 签发、Token 校验与撤销。
- `models/models.py`：数据库表结构，包括用户、故事、反馈、知识库、知识图谱等。
- `models/schemas.py`：API 请求与响应数据结构。

### 前端模块

前端入口位于 `tk-frontend/src`。

主要页面：

- `AuthPage.tsx`：登录与注册。
- `CreationPage.tsx`：创作参数填写、标题建议和项目入口。
- `Layout.tsx`：编辑器主布局和工作流导航。
- `editor/StoryDraft.tsx`：故事初稿。
- `editor/LiteratureReview.tsx`：文学审核。
- `editor/ScienceReview.tsx`：科学审核。
- `editor/ReaderFeedback.tsx`：读者反馈。
- `editor/DrawingSettings.tsx`：绘画设定。
- `editor/Illustration.tsx`：插画生成与重绘。
- `editor/IllustrationReview.tsx`：插画审核。
- `editor/PublishLayout.tsx`：排版与导出。
- `KnowledgeGraphPage.tsx`、`editor/KnowledgeGraph.tsx`：知识图谱展示与检索。

前端 API 封装：

- `tk-frontend/src/lib/api-client.ts`：主要业务 API 客户端。
- `tk-frontend/src/lib/api.ts`：基础 fetch 封装与鉴权头处理。
- `tk-frontend/src/lib/kg-api.ts`：知识图谱相关接口。
- `tk-frontend/src/lib/workHistory.ts`：本地作品快照与版本记录。

### 技术栈

| 类别 | 技术 |
| --- | --- |
| 后端框架 | FastAPI, Uvicorn |
| 数据库与 ORM | SQLite, PostgreSQL, SQLAlchemy |
| 数据校验 | Pydantic, pydantic-settings |
| 前端框架 | React, TypeScript, Vite |
| 路由与状态 | React Router, localStorage-based work history |
| UI 与交互 | Tailwind CSS, Lucide React, Framer Motion |
| 大模型 | 通义千问、火山引擎、腾讯混元、DeepSeek、百度文心等可配置供应商 |
| 图像生成 | 火山引擎、通义万相 |
| RAG | 文档分块、关键词检索、向量检索、证据增强生成 |
| 知识图谱 | 实体抽取、关系抽取、NetworkX 图计算 |
| 外部知识源 | Wikipedia, DeepSearch, Google Scholar / SerpAPI |
| 导出能力 | HTML, PDF, 长图 |
| 鉴权 | Bearer Token, token hash storage |

### 环境要求

- Python 3.10+
- Node.js 18+
- npm 9+
- Windows、macOS 或 Linux

Windows 下可以直接使用 PowerShell 脚本启动开发环境。

### 快速开始

#### 1. 克隆仓库

```bash
git clone https://github.com/ysyzynx/Tongkehui-Multi-Agent.git
cd Tongkehui-Multi-Agent
```

#### 2. 配置后端环境

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

#### 3. 配置环境变量

复制示例配置：

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

常用配置项：

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` / `DB_URL` | 数据库连接串 |
| `LOCAL_FALLBACK_DB_URL` | 主数据库不可用时的本地回退数据库 |
| `DB_AUTO_FALLBACK` | 是否启用数据库自动回退 |
| `HOST` / `PORT` | 后端监听地址与端口 |
| `OPENAI_API_KEY` | OpenAI 兼容接口 Key，文本模型默认读取项之一 |
| `LLM_MODEL` / `VISION_MODEL` | 文本与视觉模型配置 |
| `DEEPSEARCH_API_KEY` | DeepSearch 检索增强 Key |
| `VOLCENGINE_API_KEY` | 火山引擎文生图 Key |
| `VOLCENGINE_IMAGE_MODEL` | 火山引擎图片模型 |
| `SERPAPI_API_KEY` | Google Scholar / SerpAPI 检索 Key |

请不要将真实密钥提交到 Git 仓库。

#### 4. 启动后端

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端地址：

- API 健康检查：http://localhost:8000/
- Swagger 文档：http://localhost:8000/docs

#### 5. 启动前端

```bash
cd tk-frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

前端地址：

- http://localhost:5173

#### 6. Windows 一键启动

```powershell
.\start-dev.ps1
```

该脚本会清理默认端口并同时启动后端和前端。

### 主要 API

| 模块 | 路径 |
| --- | --- |
| 认证 | `/api/auth/*` |
| LLM 配置 | `/api/llm-config/*` |
| 故事创作 | `/api/story/*` |
| 文学审核 | `/api/literature/*` |
| 科学审核 | `/api/check/*` |
| 读者反馈 | `/api/reader/*` |
| 插画生成 | `/api/illustrator/*` |
| 插画审核 | `/api/illustration-review/*` |
| 发布导出 | `/api/publisher/*` |
| 知识库 | `/api/knowledge/*` |
| 事实检索 | `/api/fact/*` |
| 知识图谱 | `/api/kg/*` |

除认证相关接口外，主要工作流接口默认需要在请求头中携带 Bearer Token：

```http
Authorization: Bearer <token>
```

### 数据模型概览

核心数据表包括：

- `users`：用户账号与用户级 LLM 配置。
- `user_tokens`：登录 token 哈希与过期时间。
- `stories`：故事记录、主题、受众、正文、术语表和状态。
- `agent_feedbacks`：各 Agent 的审查、反馈和生成结果。
- `knowledge_documents`：知识库文档。
- `knowledge_chunks`：知识库分块与向量/关键词索引。
- `kg_entities`：知识图谱实体。
- `kg_relations`：知识图谱关系。
- `kg_entity_embeddings`：实体向量，用于语义搜索。

### 文档索引

更多文档位于 `doc/`：

- `doc/API.md`
- `doc/TECHNICAL_DOCUMENTATION.md`
- `doc/API_USAGE_EXAMPLES.md`
- `doc/TROUBLESHOOTING.md`
- `doc/RAG库完整使用指南.md`
- `doc/知识图谱功能使用说明.md`
- `doc/童科绘服务器部署.md`

### 部署建议

生产环境建议：

- 使用 PostgreSQL 作为主数据库。
- 使用 Linux + Uvicorn/Gunicorn 运行后端服务。
- 使用 Nginx 反向代理前端静态资源和后端 API。
- 配置 HTTPS、CORS 白名单、日志轮转和密钥管理。
- 将耗时生成任务逐步迁移到异步任务队列，提升长流程稳定性。

### 常见问题

#### 后端启动时 PostgreSQL 连接失败

如果开启了 `DB_AUTO_FALLBACK=true`，系统会在主库不可用时回退到 `LOCAL_FALLBACK_DB_URL`，默认是本地 SQLite：

```text
sqlite:///./tongkehui.db
```

#### 前端无法访问后端

检查：

- 后端是否运行在 `http://localhost:8000`
- 前端 `vite.config.ts` 中的 `/api` 代理是否指向正确后端地址
- 请求是否携带有效 Bearer Token

#### 大模型调用失败

检查：

- `.env` 中 API Key 是否存在
- 用户个人 LLM 配置是否已填写
- 模型供应商和模型名称是否匹配
- 网络是否可以访问对应模型服务

### 许可证

当前仓库暂未声明开源许可证。如需公开发布或商业使用，请先补充 `LICENSE` 文件并确认依赖许可证要求。

---

## English Guide

### Overview

TongKeHui Multi-Agent is a multi-agent platform for science communication content creation. It turns the production of a children's science story, illustrated article, or science picture book into a staged workflow: topic planning, story generation, literary review, scientific review, reader feedback, illustration generation, illustration review, and final export.

The project combines LLM agents, RAG-based evidence retrieval, knowledge graph extraction, image generation, and a React workflow editor to make AI-assisted science content creation more controllable and traceable.

### Why This Project

Science content creation has to balance several requirements:

- The story should be engaging and readable for the target audience.
- Scientific facts and terminology must be checked carefully.
- Illustrations should match both the story and the underlying science.
- The final result should be exportable as a readable publication.

TongKeHui addresses these requirements with a multi-step AI workflow instead of relying on a single one-shot generation prompt.

### Key Features

- Story generation from topic, title, audience, style, and word count.
- Title suggestions for creative topic exploration.
- Literary review for readability, tone, pacing, and audience fit.
- Scientific review for factual accuracy, terminology, logic, and source suggestions.
- Optional iterative self-feedback science review.
- Reader simulation and feedback-based content refinement.
- Illustration storyboard extraction, prompt generation, and image generation.
- Illustration review for scientific accuracy, character consistency, and visual logic.
- Knowledge base ingestion, chunking, indexing, and hybrid retrieval.
- Knowledge graph extraction from text, documents, topics, and Wikipedia pages.
- PDF and long-image export.
- User authentication with Bearer Token support.
- Runtime LLM provider configuration per user.

### Workflow

```text
User input: topic, audience, style, word count
        |
        v
StoryCreatorAgent
        |
        v
LiteratureCheckerAgent
        |
        v
ScienceCheckerAgent + RAG / DeepSearch
        |
        v
ReaderAgent
        |
        v
IllustratorAgent
        |
        v
IllustrationReviewerAgent
        |
        v
Publisher export
```

### Architecture

```text
.
├─ main.py                  # FastAPI application entry
├─ pipeline_runner.py        # Offline interactive pipeline script
├─ agent/                   # Multi-agent business logic
├─ router/                  # API routers
├─ models/                  # SQLAlchemy ORM models and Pydantic schemas
├─ utils/                   # Database, LLM, RAG, auth, graph, export utilities
├─ prompts/                 # Prompt templates
├─ config/                  # Configuration and taxonomy files
├─ scripts/                 # Migration, initialization, and packaging scripts
├─ doc/                     # Documentation
├─ tk-frontend/             # React + TypeScript + Vite frontend
├─ requirements.txt         # Backend dependencies
├─ start-dev.ps1            # Windows one-command development launcher
└─ start-all.ps1            # Startup helper script
```

### Backend Structure

The backend is built with FastAPI and SQLAlchemy. `main.py` creates the app, registers routers, initializes tables, and runs startup self-checks.

Main backend areas:

- `router/`: API layer grouped by feature.
- `agent/`: AI agents for each workflow stage.
- `utils/llm_client.py`: unified wrapper for text, vision, and image model calls.
- `utils/fact_rag.py`: document chunking, indexing, and evidence retrieval.
- `utils/kg_builder.py`: knowledge graph entity and relation extraction.
- `utils/auth.py`: registration, login, token issuing, validation, and logout.
- `models/models.py`: database table definitions.
- `models/schemas.py`: request and response schemas.

### Frontend Structure

The frontend is built with React, TypeScript, and Vite.

Main frontend areas:

- `AuthPage.tsx`: login and registration.
- `CreationPage.tsx`: creation form and title suggestions.
- `Layout.tsx`: workflow editor shell and navigation.
- `editor/StoryDraft.tsx`: story draft generation.
- `editor/LiteratureReview.tsx`: literary review.
- `editor/ScienceReview.tsx`: scientific review.
- `editor/ReaderFeedback.tsx`: reader feedback and refinement.
- `editor/DrawingSettings.tsx`: drawing configuration.
- `editor/Illustration.tsx`: illustration generation and regeneration.
- `editor/IllustrationReview.tsx`: illustration review.
- `editor/PublishLayout.tsx`: export and publishing.
- `KnowledgeGraphPage.tsx`: knowledge graph view.

API and state helpers:

- `tk-frontend/src/lib/api-client.ts`: typed business API client.
- `tk-frontend/src/lib/api.ts`: shared fetch wrapper.
- `tk-frontend/src/lib/kg-api.ts`: knowledge graph API helper.
- `tk-frontend/src/lib/workHistory.ts`: local work snapshots and version history.

### Tech Stack

| Area | Technologies |
| --- | --- |
| Backend | FastAPI, Uvicorn |
| Database | SQLite, PostgreSQL, SQLAlchemy |
| Validation | Pydantic, pydantic-settings |
| Frontend | React, TypeScript, Vite |
| Routing and State | React Router, localStorage-based work history |
| UI | Tailwind CSS, Lucide React, Framer Motion |
| LLM Providers | Qwen, Volcengine, Tencent Hunyuan, DeepSeek, Baidu Wenxin |
| Image Generation | Volcengine, Qwen Wanxiang |
| RAG | Document chunking, keyword retrieval, embedding retrieval |
| Knowledge Graph | Entity extraction, relation extraction, NetworkX |
| External Sources | Wikipedia, DeepSearch, Google Scholar / SerpAPI |
| Export | HTML, PDF, long image |
| Authentication | Bearer Token, token hash storage |

### Requirements

- Python 3.10+
- Node.js 18+
- npm 9+
- Windows, macOS, or Linux

### Quick Start

#### 1. Clone the repository

```bash
git clone https://github.com/ysyzynx/Tongkehui-Multi-Agent.git
cd Tongkehui-Multi-Agent
```

#### 2. Set up the backend

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

#### 3. Configure environment variables

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Common variables:

| Variable | Description |
| --- | --- |
| `DATABASE_URL` / `DB_URL` | Database URL |
| `LOCAL_FALLBACK_DB_URL` | Local fallback database URL |
| `DB_AUTO_FALLBACK` | Whether to fallback when primary DB is unavailable |
| `HOST` / `PORT` | Backend host and port |
| `OPENAI_API_KEY` | API key for OpenAI-compatible text model calls |
| `LLM_MODEL` / `VISION_MODEL` | Text and vision model settings |
| `DEEPSEARCH_API_KEY` | DeepSearch key |
| `VOLCENGINE_API_KEY` | Volcengine image generation key |
| `VOLCENGINE_IMAGE_MODEL` | Volcengine image model |
| `SERPAPI_API_KEY` | Google Scholar / SerpAPI key |

Do not commit real API keys to the repository.

#### 4. Start the backend

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:

- Health check: http://localhost:8000/
- Swagger docs: http://localhost:8000/docs

#### 5. Start the frontend

```bash
cd tk-frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Frontend URL:

- http://localhost:5173

#### 6. Windows one-command launcher

```powershell
.\start-dev.ps1
```

This script cleans the default ports and starts both backend and frontend services.

### Main API Modules

| Module | Path |
| --- | --- |
| Auth | `/api/auth/*` |
| LLM Config | `/api/llm-config/*` |
| Story | `/api/story/*` |
| Literature Review | `/api/literature/*` |
| Science Review | `/api/check/*` |
| Reader Feedback | `/api/reader/*` |
| Illustration | `/api/illustrator/*` |
| Illustration Review | `/api/illustration-review/*` |
| Publisher | `/api/publisher/*` |
| Knowledge Base | `/api/knowledge/*` |
| Fact Retrieval | `/api/fact/*` |
| Knowledge Graph | `/api/kg/*` |

Most workflow APIs require a Bearer Token:

```http
Authorization: Bearer <token>
```

### Data Model Overview

Core tables:

- `users`: user accounts and user-level LLM settings.
- `user_tokens`: hashed login tokens and expiration timestamps.
- `stories`: story metadata, content, glossary, and status.
- `agent_feedbacks`: review and feedback records from agents.
- `knowledge_documents`: knowledge base documents.
- `knowledge_chunks`: indexed document chunks.
- `kg_entities`: knowledge graph entities.
- `kg_relations`: knowledge graph relations.
- `kg_entity_embeddings`: entity embeddings for semantic search.

### Documentation

Additional documents are available in `doc/`:

- `doc/API.md`
- `doc/TECHNICAL_DOCUMENTATION.md`
- `doc/API_USAGE_EXAMPLES.md`
- `doc/TROUBLESHOOTING.md`
- `doc/RAG库完整使用指南.md`
- `doc/知识图谱功能使用说明.md`
- `doc/童科绘服务器部署.md`

### Deployment Notes

Recommended production setup:

- Use PostgreSQL as the primary database.
- Run the backend on Linux with Uvicorn or Gunicorn.
- Use Nginx as a reverse proxy for frontend assets and backend APIs.
- Configure HTTPS, CORS allowlists, log rotation, and secret management.
- Move long-running generation tasks to a background queue for better reliability.

### Troubleshooting

#### PostgreSQL connection fails during startup

If `DB_AUTO_FALLBACK=true`, the app falls back to `LOCAL_FALLBACK_DB_URL`, which defaults to:

```text
sqlite:///./tongkehui.db
```

#### Frontend cannot reach backend

Check that:

- The backend is running at `http://localhost:8000`.
- The Vite proxy in `vite.config.ts` points to the correct backend.
- Requests include a valid Bearer Token when required.

#### LLM calls fail

Check that:

- API keys are configured in `.env` or user-level LLM settings.
- The selected provider and model are valid.
- The network can reach the selected provider.

### License

No open-source license has been declared yet. Add a `LICENSE` file before public redistribution or commercial use.
