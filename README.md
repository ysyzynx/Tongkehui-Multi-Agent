# 童科绘（TongKeHui）

童科绘是一个面向儿童科普内容生产的多智能体协作平台，覆盖从故事创作、文学润色、科学审查、读者反馈微调、插画生成与审核到发布导出的完整链路。

项目采用前后端分离架构：
- 后端：FastAPI + SQLAlchemy
- 前端：React + TypeScript + Vite
- 数据库：PostgreSQL（主库）/ SQLite（回退）
- 扩展能力：RAG、维基百科检索、学术检索（可选）

## 核心功能

- 故事创作：基于主题与年龄段生成科普故事
- 文学审核：优化可读性、语气与叙事风格
- 科学审核：事实校验、术语核查、逻辑检查
- 读者反馈：模拟读者反馈并输出改进版本
- 插画生成：自动生成分镜和绘图提示
- 插画审核：校验科学准确性与画面一致性
- 词条增强：正文高亮 + 文末术语解释
- 发布导出：支持 HTML/PDF 导出
- 鉴权系统：注册、登录、Token 鉴权
- 知识库：文档入库、检索与图谱能力

## 仓库结构

```text
.
├─ main.py                 # FastAPI 入口
├─ agent/                  # 多智能体实现
├─ router/                 # API 路由
├─ models/                 # ORM 与数据模型
├─ utils/                  # 数据库、LLM、RAG、鉴权等通用能力
├─ prompts/                # 提示词模板
├─ config/                 # 系统配置
├─ tk-frontend/            # 前端工程（Vite）
├─ scripts/                # 数据与迁移脚本
├─ doc/                    # 项目文档（已统一收敛）
├─ requirements.txt        # 后端依赖
├─ start-dev.ps1           # Windows 一键开发启动
└─ start-all.ps1           # 启动指引脚本
```

## 环境要求

- Python 3.10+
- Node.js 18+
- npm 9+
- Windows / macOS / Linux（Windows 下可直接使用 PowerShell 脚本）

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd 童科绘
```

### 2. 启动后端

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端默认地址：
- API 根路径：http://localhost:8000/
- Swagger 文档：http://localhost:8000/docs

### 3. 启动前端

```bash
cd tk-frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

前端地址：
- http://localhost:5173

### 4. Windows 一键启动（可选）

```powershell
./start-dev.ps1
```

说明：该脚本会清理端口并同时拉起前后端服务。

## 配置说明

配置主要来源于环境变量（建议使用 .env）：
- DB_URL：数据库连接串
- HOST / PORT：服务监听配置
- OPENAI_API_KEY / OPENAI_API_BASE：模型接口配置
- LLM_MODEL / VISION_MODEL：文本/视觉模型
- DEEPSEARCH_API_KEY / DEEPSEARCH_API_BASE：检索增强
- VOLCENGINE_API_KEY / VOLCENGINE_IMAGE_MODEL：插画生成配置
- SERPAPI_API_KEY：Scholar 检索（可选）

建议将所有密钥配置放入 .env，不要提交到 Git 仓库。
仓库不包含可直接使用的默认密钥，用户需要在本地环境中自行填写。

推荐步骤：
1. 复制 .env.example 为 .env
2. 按需填写各平台 API Key
3. 启动服务

## 认证机制

除 /api/auth/* 外，大部分接口默认需要 Bearer Token。

标准流程：
1. 调用 /api/auth/register 注册
2. 调用 /api/auth/login 获取 token
3. 在请求头中携带 Authorization: Bearer <token>
4. 调用 /api/auth/logout 退出

## 主要 API 模块

- 认证：/api/auth/*
- 故事：/api/story/*
- 文学审核：/api/literature/*
- 科学审核：/api/check/*
- 读者反馈：/api/reader/*
- 插画：/api/illustrator/*
- 插画审核：/api/illustration-review/*
- 知识库：/api/knowledge/*
- 事实检索：/api/fact/*
- 发布导出：/api/publisher/*

## 文档索引

详细文档请查看 doc 目录：
- doc/API.md
- doc/TECHNICAL_DOCUMENTATION.md
- doc/TROUBLESHOOTING.md
- doc/RAG库完整使用指南.md

## 部署建议

- 生产环境建议使用 Linux + gunicorn/uvicorn
- Nginx 反向代理前后端
- 配置 HTTPS 与跨域白名单
- 使用 PostgreSQL 作为主数据库

## 许可证

当前仓库暂未声明开源许可证。
如需开源发布，请新增 LICENSE 文件并补充依赖许可证说明。
