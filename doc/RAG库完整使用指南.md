# 创作者RAG库完整使用指南

## 📋 目录

- [功能概述](#功能概述)
- [快速开始](#快速开始)
- [API接口文档](#api接口文档)
- [高级用法](#高级用法)

---

## 功能概述

### 已实现的功能

| 模块 | 功能 | 状态 |
|-----|------|------|
| **知识库管理** | 文档的增删改查 | ✅ |
| **内容采集** | 5个国内科普网站采集 | ✅ |
| **混合检索** | 向量+关键词检索 | ✅ |
| **RAG集成** | 创作时的知识增强 | ✅ |
| **批量导入** | 支持批量文档入库 | ✅ |

### 支持的采集网站

1. **科普中国** (kepu_gov_cn) - 官方平台，权威度95
2. **中科院之声** (cas_voice) - 中科院官方，权威度95
3. **中国科普博览** (kepu_net_cn) - 中科院主办，权威度90
4. **科学网博客** (sciencenet_cn) - 科研社区，权威度85
5. **果壳网** (guokr_com) - 趣味科普，权威度85

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化知识库

```bash
# 运行初始化脚本
python scripts/init_knowledge_base.py
```

这个脚本会：
- 添加5篇经典获奖科普作品作为示例
- （可选）从5个科普网站采集内容
- 显示知识库统计信息

### 3. 启动后端服务

```bash
python main.py
```

### 4. 访问API文档

打开浏览器访问：
```
http://localhost:8000/docs
```

---

## API接口文档

### 知识库管理接口

#### 列出文档

```http
GET /api/knowledge/documents?page=1&page_size=20
```

查询参数：
- `page`: 页码
- `page_size`: 每页数量
- `doc_type`: 文档类型筛选（CREATOR_STYLE/SCIENCE_FACT/FACT）
- `min_authority`: 最低权威度
- `search`: 搜索关键词

#### 创建文档

```http
POST /api/knowledge/documents
Content-Type: application/json

{
  "source_name": "作品名称",
  "source_url": "https://...",
  "publisher": "出版社",
  "author": "作者",
  "publish_year": 2023,
  "authority_level": 90,
  "doc_type": "CREATOR_STYLE",
  "topic_tags": ["天文学", "物理学"],
  "audience_tags": ["6-12岁"],
  "style_tags": ["故事型"],
  "award_tags": ["全国优秀科普作品奖"],
  "content": "完整内容..."
}
```

#### 获取文档详情

```http
GET /api/knowledge/documents/{document_id}
```

#### 更新文档

```http
PUT /api/knowledge/documents/{document_id}
```

#### 删除文档

```http
DELETE /api/knowledge/documents/{document_id}
```

#### 重新索引文档

```http
POST /api/knowledge/documents/{document_id}/reindex
```

#### 获取文档分块

```http
GET /api/knowledge/documents/{document_id}/chunks
```

---

### 内容采集接口

#### 列出支持的网站

```http
GET /api/knowledge/collector/sites
```

响应示例：
```json
{
  "code": 200,
  "msg": "Success",
  "data": {
    "sites": [
      {
        "id": "kepu_gov_cn",
        "name": "科普中国",
        "url": "https://www.kepu.gov.cn",
        "description": "官方科普平台",
        "authority_level": 95
      }
    ]
  }
}
```

#### 从指定网站采集

```http
POST /api/knowledge/collector/from-site
Content-Type: application/json

{
  "site_name": "kepu_gov_cn",
  "limit": 10,
  "doc_type": "CREATOR_STYLE",
  "auto_ingest": true
}
```

参数说明：
- `site_name`: 网站ID（必填）
- `limit`: 采集数量，默认10
- `doc_type`: 入库类型，默认CREATOR_STYLE
- `auto_ingest`: 是否自动入库，默认true

#### 一键采集所有网站

```http
POST /api/knowledge/collector/all-sites
Content-Type: application/json

{
  "per_site_limit": 5,
  "doc_type": "CREATOR_STYLE",
  "auto_ingest": true
}
```

---

### 检索接口

#### 混合检索

```http
POST /api/knowledge/search
Content-Type: application/json

{
  "query": "天空为什么是蓝色的",
  "top_k": 5,
  "doc_type": "CREATOR_STYLE",
  "min_authority_level": 80
}
```

---

### 统计接口

#### 获取知识库统计

```http
GET /api/knowledge/stats
```

---

### 批量导入接口

#### 批量导入文档

```http
POST /api/knowledge/batch-import
Content-Type: application/json

{
  "documents": [
    {
      "source_name": "文档1",
      "content": "内容1",
      "authority_level": 90,
      "doc_type": "CREATOR_STYLE"
    },
    {
      "source_name": "文档2",
      "content": "内容2",
      "authority_level": 85,
      "doc_type": "CREATOR_STYLE"
    }
  ],
  "auto_index": true
}
```

---

## 在创作流程中使用RAG

### 创作时启用RAG

在调用故事创作接口时，设置以下参数：

```http
POST /api/story/create
Content-Type: application/json

{
  "theme": "水的循环",
  "age_group": "6-12岁",
  "style": "趣味科普",
  "use_rag": true,
  "rag_doc_type": "CREATOR_STYLE",
  "rag_top_k": 4
}
```

参数说明：
- `use_rag`: 是否使用RAG（true/false）
- `rag_doc_type`: 知识库类型
  - `CREATOR_STYLE`: 创作者风格库（获奖作品等）
  - `SCIENCE_FACT`: 科学事实库（教材等）
  - `FACT`: 通用知识库
- `rag_top_k`: 检索返回的证据数量（默认4）

---

## 高级用法

### 数据库表结构

#### knowledge_documents 表

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | Integer | 主键 |
| source_name | String | 来源名称 |
| source_url | String | 来源URL |
| publisher | String | 出版社 |
| author | String | 作者 |
| publish_year | Integer | 出版年份 |
| authority_level | Integer | 权威度 0-100 |
| doc_type | String | 文档类型 |
| topic_tags | Text | 主题标签（JSON） |
| audience_tags | Text | 受众标签（JSON） |
| style_tags | Text | 风格标签（JSON） |
| award_tags | Text | 奖项标签（JSON） |
| content | Text | 文档内容 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### knowledge_chunks 表

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | Integer | 主键 |
| document_id | Integer | 文档ID（外键） |
| chunk_index | Integer | 分块索引 |
| chunk_text | Text | 分块内容 |
| keywords | Text | 关键词（JSON） |
| embedding | Text | 向量嵌入（JSON） |
| created_at | DateTime | 创建时间 |

---

### Python直接调用示例

#### 初始化采集器

```python
from utils.science_collector import get_science_collector

collector = get_science_collector()

# 从指定网站采集
articles = collector.collect_from_site("kepu_gov_cn", limit=10)

# 从所有网站采集
all_articles = collector.collect_all_sites(per_site_limit=5)
```

#### 直接检索

```python
from utils.fact_rag import search_fact_evidence
from utils.database import SessionLocal

db = SessionLocal()

results = search_fact_evidence(
    db,
    query="天空为什么是蓝色的",
    top_k=5,
    doc_type="CREATOR_STYLE"
)

for item in results:
    print(f"[{item['score']}] {item['source_name']}")
    print(f"  {item['snippet']}")
```

---

## 常见问题

### Q: RSS源连接失败怎么办？

A: 部分网站的RSS可能不稳定或需要更新地址。可以查看 `science_collector.py` 中的RSS配置进行调整。

### Q: 如何添加新的采集网站？

A: 在 `science_collector.py` 中添加新的采集方法，并在 `collect_from_site` 方法中注册。

### Q: 向量检索的速度慢？

A: 可以考虑使用专业的向量数据库（如Chroma、Milvus、Qdrant）替代当前的SQLite存储。

---

## 下一步规划

- [ ] 前端知识库管理界面
- [ ] 知识质量评估系统
- [ ] 使用反馈闭环
- [ ] 向量数据库升级
- [ ] 更多采集网站接入
