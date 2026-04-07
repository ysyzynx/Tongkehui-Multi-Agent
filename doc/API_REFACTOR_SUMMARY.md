# API 接口重构总结

## 概述

本次重构对童科绘项目的前端和后端 API 接口进行了全面梳理和统一设计，提供了更好的开发体验和代码可维护性。

## 文件结构

### 新增文件

#### 前端
- `tk-frontend/src/lib/api-client.ts` - 统一的 TypeScript API 客户端

#### 文档
- `docs/API.md` - 完整的 API 接口文档
- `docs/API_USAGE_EXAMPLES.md` - API 使用示例
- `docs/API_REFACTOR_SUMMARY.md` - 本文档

#### 后端
- `router/__init__.py` - 路由模块统一导出

## 主要改进

### 1. 统一的 API 客户端 (`api-client.ts`)

**特性：**
- 完整的 TypeScript 类型定义
- Promise 化的 API 调用
- 内置错误处理
- 单例模式，全局共享

**主要功能分类：**

#### 创作相关
- `suggestTitles()` - 生成标题建议
- `createStory()` - 创建故事

#### 审核相关
- `scienceCheck()` - 科学审核
- `scienceCheckSelfFeedback()` - 自反馈科学审核
- `literatureReview()` - 文学审核
- `readerEvaluate()` - 读者评估

#### 插画相关
- `suggestIllustrations()` - 生成插画建议
- `regenerateIllustration()` - 重新生成插画

#### 知识库相关
- `listDocuments()` - 获取文档列表
- `getDocument()` - 获取单个文档
- `createDocument()` - 创建文档
- `searchKnowledge()` - 搜索知识库
- `preretrieveKnowledge()` - RAG 预检索
- `searchTopic()` - 按主题搜索科普网站
- `getKnowledgeStats()` - 获取知识库统计

#### 发布相关
- `exportPdf()` - 导出 PDF
- `getPdfDownloadUrl()` - 获取 PDF 下载链接

### 2. 类型安全

所有 API 都有完整的 TypeScript 类型定义：

```typescript
// 输入参数类型
interface CreateStoryParams {
  project_title?: string;
  theme: string;
  style?: string;
  age_group: string;
  target_audience: string;
  // ...
}

// 响应数据类型
interface StoryData {
  id?: number;
  title: string;
  content: string;
  glossary: Array<{ term: string; explanation: string }>;
  rag_enabled: boolean;
  // ...
}
```

### 3. 使用示例

提供了详细的使用文档，包括：
- 基础使用示例
- React Hook 集成示例
- 后端 Python 调用示例

### 4. API 文档

完整的 REST API 文档，包含：
- 端点说明
- 请求/响应示例
- 查询参数说明
- 错误码说明

## 迁移指南

### 从旧 API 迁移到新客户端

#### 旧方式（使用 fetchApi）
```typescript
import { fetchApi } from '../lib/api';

// 生成标题建议
const response = await fetchApi('/api/story/suggest-titles', {
  method: 'POST',
  body: JSON.stringify({ theme, target_audience, age_group }),
});
const data = await response.json();
const suggestions = data.data.suggestions;
```

#### 新方式（使用 apiClient）
```typescript
import apiClient from '../lib/api-client';

// 生成标题建议
const suggestions = await apiClient.suggestTitles({
  theme,
  target_audience,
  age_group
});
```

### 已更新的文件

1. `tk-frontend/src/pages/CreationPage.tsx`
   - 使用 `apiClient.suggestTitles()` 替代 `fetchApi('/api/story/suggest-titles')`
   - 使用 `apiClient.preretrieveKnowledge()` 替代 `fetchApi('/api/knowledge/preretrieve')`
   - 使用 `apiClient.searchTopic()` 替代 `fetchApi('/api/knowledge/search-topic')`

2. `tk-frontend/src/pages/editor/StoryDraft.tsx`
   - 使用 `apiClient.createStory()` 替代 `fetchApi('/api/story/create')`

## 优势

### 开发体验
- **类型提示**：IDE 提供完整的代码补全和类型检查
- **减少样板代码**：无需手动处理 JSON 解析和响应检查
- **统一错误处理**：所有 API 调用使用相同的错误处理逻辑

### 可维护性
- **集中管理**：所有 API 定义在一个文件中
- **易于扩展**：添加新 API 只需在类中添加方法
- **类型安全**：编译时即可发现类型错误

### 可测试性
- **易于 mock**：可以轻松 mock 整个 API 客户端进行测试
- **依赖注入**：可以注入自定义的 baseUrl 进行测试

## 后续工作建议

1. **其他页面迁移**：将其他使用 API 的页面也迁移到新的客户端
2. **React Query 集成**：添加 React Query / TanStack Query 支持缓存和状态管理
3. **错误边界**：添加全局错误边界处理 API 错误
4. **加载状态**：统一的加载状态管理
5. **请求取消**：添加 AbortController 支持取消请求

## 注意事项

- 旧的 `fetchApi` 仍然可用，可以逐步迁移
- 新客户端保持了向后兼容的 API 端点
- 所有类型定义都可以从 `api-client.ts` 导入使用
