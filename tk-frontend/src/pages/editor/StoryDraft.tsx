import { useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Loader2, BookOpen, ChevronDown, ChevronUp, Pencil, Save, X } from 'lucide-react';
import { RefreshCw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import apiClient, { API_BASE, type StoryData } from '../../lib/api-client';
import { getModelVersionBadge } from '../../lib/workHistory';

function resolveTargetAudience(formData: any) {
  const targetMap: Record<string, string> = {
    '1': '青少幼年儿童',
    '2': '产业工人',
    '3': '老年人',
    '4': '领导干部和公务员',
    '5': '农民',
  };

  if (formData?.targetAudience) {
    return targetMap[formData.targetAudience] || '大众';
  }
  return '大众';
}

function normalizeArticleStyle(style?: string) {
  const raw = String(style || '').trim();
  if (!raw) return '趣味故事型';
  if (raw.includes('百科')) return '百科全书型';
  if (raw.includes('趣味') || raw.includes('童话') || raw.includes('问答') || raw.includes('科普')) {
    return '趣味故事型';
  }
  return raw;
}

function resolveAgeGroup(formData: any) {
  if (formData?.targetAudience === '1') {
    const subMap: Record<string, string> = {
      '1_1': '3-6岁',
      '1_2': '6-12岁',
      '1_3': '12-28岁',
    };
    return subMap[formData?.subAudience] || '6-12岁';
  }
  return resolveTargetAudience(formData);
}

function formatChapterHeadings(content: string) {
  return content.replace(
    /^(?!\s*#)\s*(第[一二三四五六七八九十百千万零两〇0-9]+(?:章|节|部分|幕|回)\s*[：:：]?\s*.*)$/gm,
    '## $1'
  );
}

export default function StoryDraft() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state || {}) as any;
  const formData = state?.formData || {};

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [storyData, setStoryData] = useState<StoryData | null>(null);
  const [showRagReferences, setShowRagReferences] = useState(false);
  const [isEditingDraft, setIsEditingDraft] = useState(false);
  const [editableContent, setEditableContent] = useState('');
  const [useDeepSearch, setUseDeepSearch] = useState<boolean>(state?.useDeepSearch ?? false);
  const [useFactRag, setUseFactRag] = useState<boolean>(state?.useFactRag ?? false);
  const storyVersionBadge = getModelVersionBadge('/editor/draft', state);
  const displayedContent = String(storyData?.content || '');

  const handleStartEditDraft = () => {
    setEditableContent(displayedContent);
    setIsEditingDraft(true);
  };

  const handleCancelEditDraft = () => {
    setIsEditingDraft(false);
    setEditableContent('');
  };

  const handleSaveEditedDraft = () => {
    const nextContent = editableContent.trim();
    if (!nextContent || !storyData) return;

    const nextStoryData: StoryData = {
      ...storyData,
      content: nextContent,
    };

    setStoryData(nextStoryData);
    setIsEditingDraft(false);

    navigate(location.pathname, {
      replace: true,
      state: {
        ...(state || {}),
        storyData: nextStoryData,
        storyTitle: nextStoryData?.title || '',
      },
    });
  };

  const generateStory = useCallback(async () => {
      setIsLoading(true);
      setError('');
      try {
        const payload = {
          project_title: formData.projectTitle || '',
          theme: formData.theme || '令人惊奇的科学现象',
          style: normalizeArticleStyle(formData.articleStyle),
          age_group: resolveAgeGroup(formData),
          target_audience: resolveTargetAudience(formData),
          extra_requirements: formData.extraStoryReq || '',
          word_count: Number(formData.wordCount) || 1200,
          use_rag: useFactRag,
          use_fact_rag: useFactRag,
          use_deepsearch: useDeepSearch,
          deepsearch_top_k: 6,
          rag_doc_type: formData.ragDocType || 'SCIENCE_FACT',
          rag_top_k: Number(formData.ragTopK) || 4,
          selected_rag_ids: formData.selected_rag_ids || null,
        };

        const data = await apiClient.createStory(payload);

        setStoryData(data);

        navigate(location.pathname, {
          replace: true,
          state: {
            ...(state || {}),
            useDeepSearch,
            useFactRag,
            storyData: data,
            storyTitle: data?.title || '',
          },
        });
      } catch (err: any) {
        const message = String(err?.message || '').trim();
        if (message.toLowerCase().includes('failed to fetch')) {
          setError(`无法连接后端接口。请先确认 ${API_BASE}/docs 可访问，再重试；若不可访问请重新启动后端服务。`);
        } else {
          setError(message || '网络请求失败，请确保后端服务已启动');
        }
      } finally {
        setIsLoading(false);
      }
    }, [formData, useFactRag, useDeepSearch, location.pathname, navigate, state]);

  useEffect(() => {
    if (state?.storyData || storyData) {
      if (state?.storyData) setStoryData(state.storyData);
      return;
    }

    generateStory();
  }, [generateStory, state?.storyData, storyData]);

  return (
    <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.06)] border border-gray-100 p-6 min-h-[500px]">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">
          1.
        </div>
        <div>
          <h3 className="text-xl font-bold text-gray-900">故事草稿</h3>
          <p className="text-sm text-gray-500">生成出的故事内容在这里展示。</p>
        </div>
      </div>

      <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[350px] bg-gray-50/50 flex flex-col pt-8">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center flex-1 text-gray-400 gap-3">
            <Loader2 className="animate-spin text-[#FF9F45]" size={36} />
            <p>AI 智能体正在奋笔疾书创作中，请稍候...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center flex-1 text-red-400 gap-3">
            <p>{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 mt-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition"
            >
              重试
            </button>
          </div>
        ) : storyData ? (
          <>
            <div className="mb-4 flex items-center justify-end gap-3 flex-wrap">
              <label className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 select-none">
                <input
                  type="checkbox"
                  checked={useFactRag}
                  onChange={(e) => setUseFactRag(e.target.checked)}
                  className="h-4 w-4 accent-[#FF9F45]"
                />
                使用 RAG 知识库
              </label>
              <label className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 select-none">
                <input
                  type="checkbox"
                  checked={useDeepSearch}
                  onChange={(e) => setUseDeepSearch(e.target.checked)}
                  className="h-4 w-4 accent-[#FF9F45]"
                />
                使用 DeepSearch
              </label>
              <button
                onClick={generateStory}
                disabled={isLoading}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-orange-200 text-[#FF9F45] bg-orange-50 hover:bg-orange-100 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                重新生成草稿
              </button>
            </div>

            <div className="prose prose-orange max-w-none w-full">
              <div className="mb-6 flex items-center justify-between gap-3">
                <h2 className="text-2xl font-bold text-center text-gray-800 flex-1">{storyData.title}</h2>
                <div className="flex items-center gap-2">
                  <span className="shrink-0 inline-flex items-center rounded-full border border-orange-200 bg-orange-50 px-3 py-1 text-[12px] font-bold text-[#B75A00]">
                    {storyVersionBadge}
                  </span>
                  {!isEditingDraft ? (
                    <button
                      onClick={handleStartEditDraft}
                      className="inline-flex items-center gap-1 rounded-md border border-orange-200 bg-white px-2.5 py-1 text-xs font-semibold text-[#B75A00] hover:bg-orange-50"
                    >
                      <Pencil size={13} /> 编辑
                    </button>
                  ) : null}
                </div>
              </div>

              {isEditingDraft ? (
                <div className="space-y-3">
                  <textarea
                    value={editableContent}
                    onChange={(e) => setEditableContent(e.target.value)}
                    className="min-h-[320px] w-full rounded-lg border border-gray-300 px-3 py-2 text-sm leading-7 text-gray-700 outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={handleCancelEditDraft}
                      className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-50"
                    >
                      <X size={13} /> 取消
                    </button>
                    <button
                      onClick={handleSaveEditedDraft}
                      className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
                    >
                      <Save size={13} /> 保存
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-gray-700 leading-relaxed text-[15px]">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      h2: ({ children }) => (
                        <h2 className="mt-7 mb-3 text-xl font-bold text-gray-900 border-l-4 border-orange-400 pl-3">
                          {children}
                        </h2>
                      ),
                      h3: ({ children }) => (
                        <h3 className="mt-6 mb-3 text-xl font-bold text-gray-900">{children}</h3>
                      ),
                      p: ({ children }) => <p className="mb-2 leading-8">{children}</p>,
                    }}
                  >
                    {formatChapterHeadings(displayedContent)}
                  </ReactMarkdown>
                </div>
              )}
            </div>

            {storyData.rag_enabled && storyData.rag_evidence_used && storyData.rag_evidence_used.length > 0 && (
              <div className="mt-8 border-t border-gray-200 pt-6">
                <button
                  onClick={() => setShowRagReferences(!showRagReferences)}
                  className="flex items-center gap-2 text-[#FF9F45] hover:text-[#FF8C1A] transition-colors"
                >
                  <BookOpen size={18} />
                  <span className="font-medium">知识库参考材料 ({storyData.rag_evidence_used.length} 条)</span>
                  {showRagReferences ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>

                {showRagReferences && (
                  <div className="mt-4 space-y-3">
                    {storyData.rag_evidence_used.map((evidence: any, idx: number) => (
                      <div key={idx} className="bg-[#FFF9EA] border border-[#FFE4C2] rounded-lg p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-semibold text-[#B75A00] bg-orange-100 px-2 py-0.5 rounded-full">
                                来源: {evidence.source_name}
                              </span>
                              <span className="text-xs text-gray-500">权威度: {evidence.authority_level}</span>
                              <span className="text-xs text-gray-400">匹配度: {(evidence.score * 100).toFixed(0)}%</span>
                            </div>
                            <p className="text-sm text-gray-700 leading-relaxed">{evidence.snippet}</p>
                            {evidence.source_url && (
                              <a
                                href={evidence.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-[#FF9F45] hover:text-[#FF8C1A] mt-2 inline-block"
                              >
                                查看原文 →
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center justify-center flex-1 text-gray-400">
            等待生成...
          </div>
        )}
      </div>
    </div>
  );
}
