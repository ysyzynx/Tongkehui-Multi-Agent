# 童科绘技术文档（详细版）

## 1. 项目定位

童科绘是一个“多智能体协作 + RAG 增强”的科普创作系统，目标是把“内容创作质量、科学准确性、受众适配性、视觉一致性”整合为统一工作流。

系统核心关注点：
- 质量闭环：生成 -> 多轮审核 -> 微调 -> 发布
- 科学可靠：事实检索、术语解释、逻辑审查
- 受众匹配：按年龄段和目标人群优化表达
- 生产效率：自动化生成分镜、插画审核和导出

---

## 2. 总体架构

### 2.1 架构分层

- 展示层（Frontend）
  - React + TypeScript + Vite
  - 页面工作流：创作 -> 文学 -> 科学 -> 读者 -> 插画 -> 插画审核 -> 排版
- 接口层（Router）
  - FastAPI 路由按领域拆分（story/check/reader/...）
- 业务层（Agent）
  - 文学审核、科学审核、读者反馈、插画生成、插画审核等 Agent
- 能力层（Utils）
  - 鉴权、数据库、RAG 检索、维基百科/SerpAPI/DeepSearch 客户端
- 数据层（Models）
  - SQLAlchemy 表模型（故事、反馈、用户、知识文档、分块）

### 2.2 技术栈

后端：
- FastAPI
- SQLAlchemy
- Pydantic / pydantic-settings
- Uvicorn

前端：
- React 19
- TypeScript
- Vite
- React Router
- Tailwind（含 typography）

外部能力：
- LLM API（OpenAI 兼容接口）
- DeepSearch（可选）
- Wikipedia API
- SerpAPI（默认可关闭）

---

## 3. 关键流程

### 3.1 文本创作与审核流程

1. 故事生成（/api/story/create）
2. 文学审核（/api/literature/review）
3. 科学审核（/api/check/verify 或 verify-self-feedback）
4. 读者评估（/api/reader/evaluate）
5. 基于反馈微调（/api/reader/refine，产出 4.0）
6. 排版导出（/api/publisher/export-pdf）

### 3.2 插画流程

1. 生成插画建议（/api/illustrator/suggest）
2. 单图重绘（/api/illustrator/regenerate）
3. 插画审核（/api/illustration-review/review）
   - 科学准确性
   - 逻辑问题检测
   - 人物一致性
4. 不通过项修复后复审

### 3.3 词条增强流程

- 科学审核阶段输出 highlight_terms + glossary
- 读者反馈页对高亮词条进行文末解释展示
- 可按词条调用维基接口补充解释和来源

---

## 4. 后端设计

### 4.1 启动与中间件

入口：main.py

- 应用初始化：FastAPI(title/description/version)
- CORS：当前 allow_origins 为 *（开发友好，生产需收敛）
- 全局异常处理：返回 code/msg/error/traceback
- 健康检查：GET /
- 数据表自动创建：Base.metadata.create_all(bind=engine)

### 4.2 鉴权体系

- 用户表：users
- 会话表：user_tokens（存 token_hash + 过期时间 + 撤销时间）
- 路由权限：除 /api/auth/* 外，其余路由通过 Depends(get_current_user) 保护

鉴权接口：
- POST /api/auth/register
- POST /api/auth/login
- GET /api/auth/me
- POST /api/auth/logout

### 4.3 路由模块

- story_router：故事生成、标题建议
- literature_router：文学审核
- check_router：科学审核（含自反馈链路）
- reader_router：受众评估 + 反馈微调
- illustrator_router：插画生成与重绘
- illustration_review_router：插画科学审核与一致性检查
- publisher_router：导出 PDF / 下载
- fact_router：FACT 入库检索、维基与学术检索
- knowledge_router：知识库 CRUD、搜索、统计、采集
- llm_config_router：模型配置查询与更新

### 4.4 Agent 模块职责

- StoryCreator：内容初稿生成
- LiteratureChecker：文学表达优化
- ScienceChecker：科学事实与术语核验
- ReaderAgent：受众反馈和版本微调
- Illustrator：分镜与插画提示词/重绘
- IllustrationReviewer：插画科学审核 + 逻辑检测 + 人物一致性
- Publisher：内容排版输出

### 4.5 数据模型（核心）

- stories：故事主表
- agent_feedbacks：各阶段反馈记录
- users / user_tokens：账号与会话
- knowledge_documents：知识文档
- knowledge_chunks：知识分块（关键词/向量）

### 4.6 RAG 与知识库

能力包括：
- 文档入库（source 元数据 + content）
- 自动分块与索引
- 混合检索（关键词 + 其他策略）
- 主题搜索与站点采集
- 统计分析（doc_type、topic、authority 等）

维基流程：
- /api/fact/wikipedia/search
- /api/fact/wikipedia/page
- /api/fact/wikipedia/ingest

---

## 5. 前端设计

### 5.1 应用结构

前端目录：tk-frontend

关键能力：
- 路由驱动多步骤编辑器
- 统一 API 客户端与 token 注入
- 审核状态与版本标签展示
- Markdown 内容呈现与词条交互

### 5.2 网络与会话

- API 基础地址：VITE_API_BASE_URL
- 默认走同源（window.location.origin）
- 请求自动附带 Authorization: Bearer <token>
- 401 自动清理会话并提示重新登录

### 5.3 关键页面

- AuthPage：注册/登录
- LandingPage：项目入口与退出
- Story/Literature/Science/Reader 页面：逐步生产内容
- Illustration 页面：插画生成与重绘
- IllustrationReview 页面：插画审核与问题定位
- PublishLayout 页面：排版和导出

---

## 6. 接口契约（摘要）

响应统一格式：

```json
{
  "code": 200,
  "msg": "ok",
  "data": {}
}
```

常用状态：
- 200：业务成功
- 4xx：请求错误/鉴权失败
- 500：服务内部错误（含 traceback）

建议：生产环境关闭 traceback 返回，改为日志侧采集。

---

## 7. 配置与环境变量

配置文件：config/settings.py（从 .env 读取）

主要变量：
- DB_URL（默认 sqlite:///./tongkehui.db）
- HOST / PORT / DEBUG
- OPENAI_API_KEY / OPENAI_API_BASE
- LLM_MODEL / VISION_MODEL
- DEEPSEARCH_API_KEY / DEEPSEARCH_API_BASE / DEEPSEARCH_MODEL
- SERPAPI_API_KEY
- VOLCENGINE_API_KEY / VOLCENGINE_IMAGE_MODEL

生产建议：
- 所有密钥仅保留在部署环境变量
- 禁止将真实密钥写入代码仓库
- 按环境拆分 dev/staging/prod 配置

---

## 8. 部署建议

### 8.1 开发环境

- 后端：uvicorn --reload
- 前端：vite dev
- 数据库：SQLite

### 8.2 生产环境建议

- 应用：Gunicorn + Uvicorn worker（Linux）
- 数据库：PostgreSQL（替换 SQLite）
- 反向代理：Nginx
- 静态资源：CDN 或反向代理缓存
- 日志：结构化日志 + 错误告警

### 8.3 安全建议

- 收敛 CORS 白名单
- 关闭 traceback 对外返回
- 限制上传内容体积和类型
- 增加接口限流与审计
- Token 轮换与会话失效策略

---

## 9. 质量保障

### 9.1 现有测试脚本

- test_backend.py
- test_integration.py
- test_story_creator.py
- test_science_checker.py
- test_reader.py
- test_publisher.py
- 及其他专项测试脚本

### 9.2 推荐补充

- API 契约测试（鉴权、错误码、边界值）
- Agent 输出稳定性回归测试
- 前端核心流程 E2E（登录到导出）
- 词条高亮与文末解释一致性测试

---

## 10. 已知风险与改进方向

1. 配置安全
- 需移除代码中的默认明文密钥

2. 可维护性
- 部分页面存在历史 TS 未使用变量告警

3. 一致性
- 建议将“词条解释策略”沉淀为共享模块，避免页面逻辑漂移

4. 可观测性
- 增加请求链路日志、性能指标与 Agent 执行耗时监控

5. 可扩展性
- 将长链路任务异步化（任务队列 + 状态轮询）

---

## 11. 运维排查手册（简版）

### 11.1 服务不可达

- 检查后端进程是否启动
- 检查端口 8000/5173 是否冲突
- 检查防火墙策略

### 11.2 鉴权异常（401）

- 检查 token 是否过期/被撤销
- 检查前端是否携带 Authorization
- 检查 /api/auth/me 返回

### 11.3 词条解释未更新

- 检查 /api/fact/wikipedia/search 与 /page 响应
- 检查网络可达性
- 检查前端缓存与回填逻辑

### 11.4 插画审核结论不符合预期

- 当前策略已收敛为二值：passed / needs_fix
- 未通过项应在分镜卡片中看到“具体问题列表”
- 若无列表，检查后端返回 science_reason / logic_issues

---

## 12. 文档索引

- API 详细：docs/API.md
- API 示例：docs/API_USAGE_EXAMPLES.md
- RAG 指南：docs/RAG库完整使用指南.md
- 故障排查：docs/TROUBLESHOOTING.md
- 插画审核专项：docs/插画科学审核解决方案.md

