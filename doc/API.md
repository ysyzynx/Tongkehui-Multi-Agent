# 童科绘 API 接口文档

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API Prefix**: `/api`
- **响应格式**: 统一 JSON 格式

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": { ... }
}
```

## 目录

1. [健康检查](#健康检查)
2. [创作中心](#创作中心)
3. [科学审核中心](#科学审核中心)
4. [文学审核中心](#文学审核中心)
5. [读者评估中心](#读者评估中心)
6. [插画建议中心](#插画建议中心)
7. [排版发布中心](#排版发布中心)
8. [知识库管理](#知识库管理)

---

## 健康检查

### GET /

基础健康检查接口

**响应示例**:
```json
{
  "code": 200,
  "msg": "API is running normally.",
  "data": { "status": "ok" }
}
```

---

## 创作中心

### POST /api/story/suggest-titles

根据主题生成标题建议

**请求体**:
```json
{
  "theme": "宇宙黑洞",
  "target_audience": "青少幼年儿童",
  "age_group": "6-12岁"
}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "标题建议生成成功",
  "data": {
    "suggestions": [
      {
        "title": "黑洞的秘密",
        "category": "航空航天",
        "clue": "探索黑洞的奥秘"
      }
    ]
  }
}
```

---

### POST /api/story/create

提交创作参数并生成科普故事

**请求体**:
```json
{
  "project_title": "探索黑洞",
  "theme": "宇宙黑洞",
  "style": "趣味科普",
  "age_group": "6-12岁",
  "target_audience": "青少幼年儿童",
  "extra_requirements": "主角是一只戴眼镜的小猫",
  "word_count": 1200,
  "use_rag": true,
  "rag_doc_type": "CREATOR_STYLE",
  "rag_top_k": 4,
  "selected_rag_ids": [1, 2, 3]
}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "故事生成成功",
  "data": {
    "id": 1,
    "title": "探索黑洞",
    "content": "故事内容...",
    "glossary": [
      { "term": "黑洞", "explanation": "一种天体..." }
    ],
    "rag_enabled": true,
    "rag_evidence_used": [
      {
        "id": 1,
        "source_name": "科普中国",
        "snippet": "相关内容...",
        "score": 0.95,
        "authority_level": 95
      }
    ]
  }
}
```

---

## 科学审核中心

### POST /api/check/verify

科学审核与事实校验

**请求体**:
```json
{
  "story_id": 1,
  "title": "探索黑洞",
  "content": "故事内容...",
  "target_audience": "青少幼年儿童",
  "use_fact_rag": true,
  "evidence_top_k": 6,
  "rag_doc_type": "SCIENCE_FACT",
  "use_deepsearch": true,
  "deepsearch_top_k": 6
}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "科学审核完成",
  "data": {
    "passed": true,
    "issues": [],
    "suggestions": "审核通过",
    "revised_content": "修正后的内容...",
    "glossary": [...],
    "evidence_used": [...]
  }
}
```

---

### POST /api/check/verify-self-feedback

自反馈科学审核（OpenScholar 技术）

**请求体**: 同上

**响应示例**: 同上

---

## 文学审核中心

### POST /api/literature/review

文学性审核与润色

**请求体**:
```json
{
  "story_id": 1,
  "title": "探索黑洞",
  "content": "故事内容...",
  "target_audience": "青少幼年儿童",
  "age_group": "6-12岁"
}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "文学审核完成",
  "data": {
    "passed": true,
    "feedback": "润色建议...",
    "revised_content": "润色后的内容..."
  }
}
```

---

## 读者评估中心

### POST /api/reader/evaluate

模拟目标受众打分与反馈

**请求体**:
```json
{
  "story_id": 1,
  "title": "探索黑洞",
  "content": "故事内容...",
  "age_group": "6-12岁",
  "target_audience": "青少幼年儿童"
}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "读者评估完成",
  "data": {
    "score": 85,
    "reader_feedback": "读者反馈内容..."
  }
}
```

---

## 插画建议中心

### POST /api/illustrator/suggest

生成配图建议 (Prompt)

**请求体**:
```json
{
  "story_id": 1,
  "content": "故事内容...",
  "image_count": 4,
  "art_style": "卡通",
  "extra_requirements": "色彩明亮"
}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "插画建议提取完成",
  "data": {
    "scenes": [
      {
        "scene_id": 1,
        "image_prompt": "插画提示词...",
        "summary": "场景描述...",
        "text_chunk": "对应文本片段..."
      }
    ]
  }
}
```

---

### POST /api/illustrator/regenerate

根据用户意见重绘单张图片

**请求体**:
```json
{
  "story_id": 1,
  "scene_id": 1,
  "image_prompt": "原提示词...",
  "feedback": "修改意见...",
  "art_style": "卡通",
  "extra_requirements": ""
}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "分镜重绘完成",
  "data": {
    "scene_id": 1,
    "image_prompt": "新提示词...",
    "image_url": "图片链接..."
  }
}
```

---

## 排版发布中心

### POST /api/publisher/export-pdf

导出排版后的 PDF

**请求体**:
```json
{
  "story_id": 1,
  "title": "探索黑洞",
  "content": "故事内容...",
  "glossary": [
    { "term": "黑洞", "explanation": "..." }
  ],
  "illustrations": [
    {
      "image_url": "图片链接...",
      "summary": "图片说明..."
    }
  ],
  "highlight_terms": ["黑洞", "引力"],
  "layout_type": "paragraph_image"
}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "PDF 导出成功",
  "data": {
    "filename": "探索黑洞-1234567890.pdf",
    "download_url": "/api/publisher/download/探索黑洞-1234567890.pdf"
  }
}
```

---

### GET /api/publisher/download/{filename}

查看或下载已导出的 PDF

**路径参数**:
- `filename`: PDF 文件名

**响应**: PDF 文件流

---

## 知识库管理

### GET /api/knowledge/documents

列出知识库文档（支持分页和筛选）

**查询参数**:
- `page`: 页码 (默认 1)
- `page_size`: 每页数量 (默认 20)
- `doc_type`: 文档类型筛选
- `topic_tag`: 主题标签筛选
- `audience_tag`: 受众标签筛选
- `min_authority`: 最低权威度
- `search`: 搜索关键词

**响应示例**:
```json
{
  "code": 200,
  "msg": "Success",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

---

### GET /api/knowledge/documents/{document_id}

获取单个文档详情

**路径参数**:
- `document_id`: 文档 ID

---

### POST /api/knowledge/documents

创建新文档并自动索引

**请求体**:
```json
{
  "source_name": "来源名称",
  "source_url": "https://...",
  "publisher": "出版社",
  "author": "作者",
  "publish_year": 2024,
  "authority_level": 80,
  "doc_type": "CREATOR_STYLE",
  "topic_tags": ["天文学", "物理学"],
  "audience_tags": ["6-12岁"],
  "style_tags": ["故事型"],
  "award_tags": [],
  "content": "文档内容..."
}
```

---

### POST /api/knowledge/search

检索知识库（混合检索：向量 + 关键词）

**请求体**:
```json
{
  "query": "黑洞",
  "top_k": 5,
  "doc_type": "SCIENCE_FACT",
  "min_authority_level": 80
}
```

---

### POST /api/knowledge/preretrieve

RAG 预检索：在创作前预览相关参考材料

**请求体**: 同上

---

### POST /api/knowledge/search-topic

按主题搜索科普网站并可选地自动入库到知识库

**请求体**:
```json
{
  "topic": "黑洞",
  "sites": ["kepu_gov_cn", "guokr_com"],
  "limit_per_site": 3,
  "doc_type": "SCIENCE_FACT",
  "auto_ingest": true
}
```

---

### GET /api/knowledge/stats

获取知识库统计信息

**响应示例**:
```json
{
  "code": 200,
  "msg": "Success",
  "data": {
    "total_documents": 100,
    "total_chunks": 500,
    "doc_type_counts": {
      "CREATOR_STYLE": 30,
      "SCIENCE_FACT": 70
    },
    "avg_authority_level": 85.5,
    "recent_documents": [...]
  }
}
```

---

### GET /api/knowledge/collector/sites

列出支持的科普网站

**响应示例**:
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

---

## 错误响应

所有接口在出错时返回统一格式：

```json
{
  "code": 400,
  "msg": "错误信息",
  "data": null,
  "error": "详细错误信息",
  "traceback": "堆栈跟踪（开发环境）"
}
```

常见错误码：
- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误
