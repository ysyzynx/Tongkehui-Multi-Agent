# API 使用示例

## 前端使用示例

### 1. 基础配置

```typescript
import { apiClient } from '@/lib/api-client';

// 健康检查
try {
  const health = await apiClient.healthCheck();
  console.log('API 状态:', health.status);
} catch (error) {
  console.error('API 不可用:', error);
}
```

### 2. 标题建议

```typescript
import { apiClient } from '@/lib/api-client';

// 生成标题建议
try {
  const suggestions = await apiClient.suggestTitles({
    theme: '宇宙黑洞',
    target_audience: '青少幼年儿童',
    age_group: '6-12岁'
  });

  console.log('标题建议:', suggestions);
  suggestions.forEach(suggestion => {
    console.log(`- ${suggestion.title} (${suggestion.category})`);
  });
} catch (error) {
  console.error('生成标题失败:', error);
}
```

### 3. 创建故事

```typescript
import { apiClient } from '@/lib/api-client';

try {
  const story = await apiClient.createStory({
    project_title: '探索黑洞',
    theme: '宇宙黑洞',
    style: '趣味科普',
    age_group: '6-12岁',
    target_audience: '青少幼年儿童',
    extra_requirements: '主角是一只戴眼镜的小猫',
    word_count: 1200,
    use_rag: true,
    rag_doc_type: 'CREATOR_STYLE',
    rag_top_k: 4,
    selected_rag_ids: [1, 2, 3]
  });

  console.log('故事标题:', story.title);
  console.log('故事内容:', story.content);
  console.log('术语表:', story.glossary);
} catch (error) {
  console.error('创建故事失败:', error);
}
```

### 4. RAG 预检索

```typescript
import { apiClient } from '@/lib/api-client';

try {
  const result = await apiClient.preretrieveKnowledge({
    query: '黑洞',
    top_k: 5,
    doc_type: 'CREATOR_STYLE'
  });

  console.log(`找到 ${result.total} 条参考材料`);
  result.results.forEach(ref => {
    console.log(`- [${ref.source_name}] ${ref.snippet}`);
  });
} catch (error) {
  console.error('检索失败:', error);
}
```

### 5. 科学审核

```typescript
import { apiClient } from '@/lib/api-client';

try {
  const result = await apiClient.scienceCheck({
    story_id: 1,
    title: '探索黑洞',
    content: '故事内容...',
    target_audience: '青少幼年儿童',
    use_fact_rag: true,
    use_deepsearch: true
  });

  console.log('审核通过:', result.passed);
  console.log('建议:', result.suggestions);
  if (result.revised_content) {
    console.log('修正内容:', result.revised_content);
  }
} catch (error) {
  console.error('审核失败:', error);
}
```

### 6. 文学审核

```typescript
import { apiClient } from '@/lib/api-client';

try {
  const result = await apiClient.literatureReview({
    story_id: 1,
    title: '探索黑洞',
    content: '故事内容...',
    target_audience: '青少幼年儿童',
    age_group: '6-12岁'
  });

  console.log('润色建议:', result.feedback);
  console.log('润色后内容:', result.revised_content);
} catch (error) {
  console.error('文学审核失败:', error);
}
```

### 7. 读者评估

```typescript
import { apiClient } from '@/lib/api-client';

try {
  const result = await apiClient.readerEvaluate({
    story_id: 1,
    title: '探索黑洞',
    content: '故事内容...',
    target_audience: '青少幼年儿童',
    age_group: '6-12岁'
  });

  console.log('评分:', result.score);
  console.log('反馈:', result.reader_feedback);
} catch (error) {
  console.error('评估失败:', error);
}
```

### 8. 插画建议

```typescript
import { apiClient } from '@/lib/api-client';

try {
  const result = await apiClient.suggestIllustrations({
    story_id: 1,
    content: '故事内容...',
    image_count: 4,
    art_style: '卡通',
    extra_requirements: '色彩明亮'
  });

  console.log(`生成 ${result.scenes.length} 个插画场景`);
  result.scenes.forEach(scene => {
    console.log(`场景 ${scene.scene_id}:`, scene.image_prompt);
  });
} catch (error) {
  console.error('生成插画建议失败:', error);
}
```

### 9. 重新生成插画

```typescript
import { apiClient } from '@/lib/api-client';

try {
  const result = await apiClient.regenerateIllustration({
    story_id: 1,
    scene_id: 1,
    image_prompt: '原提示词...',
    feedback: '背景颜色改为蓝色',
    art_style: '卡通'
  });

  console.log('新提示词:', result.image_prompt);
  console.log('图片链接:', result.image_url);
} catch (error) {
  console.error('重绘失败:', error);
}
```

### 10. 导出 PDF

```typescript
import { apiClient } from '@/lib/api-client';

try {
  const result = await apiClient.exportPdf({
    title: '探索黑洞',
    content: '故事内容...',
    glossary: [
      { term: '黑洞', explanation: '...' }
    ],
    illustrations: [
      {
        image_url: '图片链接...',
        summary: '图片说明...'
      }
    ],
    highlight_terms: ['黑洞', '引力']
  });

  console.log('PDF 文件名:', result.filename);
  console.log('下载链接:', result.download_url);

  // 自动下载
  const downloadUrl = apiClient.getPdfDownloadUrl(result.filename);
  window.open(downloadUrl, '_blank');
} catch (error) {
  console.error('导出 PDF 失败:', error);
}
```

### 11. 知识库操作

```typescript
import { apiClient } from '@/lib/api-client';

// 获取文档列表
try {
  const list = await apiClient.listDocuments({
    page: 1,
    page_size: 20,
    doc_type: 'CREATOR_STYLE'
  });

  console.log(`共 ${list.total} 篇文档`);
  list.items.forEach(doc => {
    console.log(`- ${doc.source_name}`);
  });
} catch (error) {
  console.error('获取文档列表失败:', error);
}

// 搜索知识库
try {
  const result = await apiClient.searchKnowledge({
    query: '黑洞',
    top_k: 5,
    doc_type: 'SCIENCE_FACT'
  });

  console.log(`找到 ${result.total} 条结果`);
} catch (error) {
  console.error('搜索失败:', error);
}

// 按主题搜索科普网站
try {
  const result = await apiClient.searchTopic({
    topic: '黑洞',
    limit_per_site: 3,
    auto_ingest: true
  });

  console.log(`找到 ${result.total_found} 篇文章`);
  console.log(`已入库 ${result.ingested_count} 篇`);
} catch (error) {
  console.error('搜索失败:', error);
}
```

---

## 后端 Python 使用示例

### 使用 requests 库调用 API

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 健康检查
def health_check():
    response = requests.get(f"{BASE_URL}/")
    print(response.json())

# 2. 生成标题建议
def suggest_titles():
    data = {
        "theme": "宇宙黑洞",
        "target_audience": "青少幼年儿童",
        "age_group": "6-12岁"
    }
    response = requests.post(f"{BASE_URL}/api/story/suggest-titles", json=data)
    result = response.json()
    print(result["data"]["suggestions"])

# 3. 创建故事
def create_story():
    data = {
        "project_title": "探索黑洞",
        "theme": "宇宙黑洞",
        "style": "趣味科普",
        "age_group": "6-12岁",
        "target_audience": "青少幼年儿童",
        "word_count": 1200
    }
    response = requests.post(f"{BASE_URL}/api/story/create", json=data)
    result = response.json()
    story = result["data"]
    print(f"标题: {story['title']}")
    print(f"内容长度: {len(story['content'])}")

# 4. 科学审核
def science_check(story_id, title, content):
    data = {
        "story_id": story_id,
        "title": title,
        "content": content,
        "target_audience": "青少幼年儿童",
        "use_fact_rag": True,
        "use_deepsearch": True
    }
    response = requests.post(f"{BASE_URL}/api/check/verify", json=data)
    result = response.json()
    check_result = result["data"]
    print(f"审核通过: {check_result['passed']}")
    print(f"建议: {check_result['suggestions']}")

# 5. 导出 PDF
def export_pdf(title, content):
    data = {
        "title": title,
        "content": content,
        "glossary": [],
        "illustrations": []
    }
    response = requests.post(f"{BASE_URL}/api/publisher/export-pdf", json=data)
    result = response.json()
    filename = result["data"]["filename"]
    print(f"PDF 文件: {filename}")

    # 下载 PDF
    download_url = f"{BASE_URL}/api/publisher/download/{filename}"
    pdf_response = requests.get(download_url)
    with open(filename, "wb") as f:
        f.write(pdf_response.content)
    print(f"已下载: {filename}")

if __name__ == "__main__":
    health_check()
    suggest_titles()
```

---

## React Hook 使用示例

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

// 获取标题建议的 Hook
export function useSuggestTitles(params: {
  theme: string;
  target_audience?: string;
  age_group?: string;
}) {
  return useQuery({
    queryKey: ['suggestTitles', params],
    queryFn: () => apiClient.suggestTitles(params),
    enabled: params.theme.length >= 2,
    staleTime: 5 * 60 * 1000, // 5 分钟
  });
}

// 创建故事的 Hook
export function useCreateStory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: apiClient.createStory,
    onSuccess: (data) => {
      console.log('故事创建成功:', data);
      queryClient.invalidateQueries({ queryKey: ['stories'] });
    },
    onError: (error) => {
      console.error('故事创建失败:', error);
    },
  });
}

// 组件中使用
function CreationForm() {
  const [formData, setFormData] = useState({
    theme: '',
    target_audience: '青少幼年儿童',
    age_group: '6-12岁'
  });

  // 自动获取标题建议
  const { data: suggestions, isLoading: isLoadingSuggestions } = useSuggestTitles({
    theme: formData.theme,
    target_audience: formData.target_audience,
    age_group: formData.age_group
  });

  // 创建故事
  const createStory = useCreateStory();

  const handleSubmit = async () => {
    try {
      const story = await createStory.mutateAsync({
        ...formData,
        style: '趣味科普',
        word_count: 1200
      });
      console.log('故事创建成功:', story);
    } catch (error) {
      console.error('创建失败:', error);
    }
  };

  return (
    <div>
      <input
        value={formData.theme}
        onChange={(e) => setFormData(prev => ({ ...prev, theme: e.target.value }))}
        placeholder="输入主题..."
      />

      {isLoadingSuggestions && <div>加载建议中...</div>}

      {suggestions && suggestions.length > 0 && (
        <div>
          <h3>标题建议</h3>
          {suggestions.map((suggestion, idx) => (
            <button key={idx}>
              {suggestion.title}
            </button>
          ))}
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={createStory.isPending}
      >
        {createStory.isPending ? '创建中...' : '创建故事'}
      </button>
    </div>
  );
}
```
