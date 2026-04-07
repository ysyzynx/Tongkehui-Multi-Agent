import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Loader2, RefreshCw, Pencil, Save, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ReviewProgress, { type ReviewStepKey } from '../../components/ReviewProgress';
import { fetchApi } from '../../lib/api';
import { getLatestSnapshotState, getModelVersionBadge } from '../../lib/workHistory';

type LiteratureData = {
  passed?: boolean;
  feedback?: string;
  revised_content?: string;
};

function formatLiteratureContent(content: string) {
  let formatted = content;

  // Promote lines like "【标题】：xxx" to a markdown h1.
  formatted = formatted.replace(
    /^\s*【标题】\s*[：:]\s*(.+)$/m,
    '# $1'
  );

  // Promote chapter-like lines to markdown h2.
  formatted = formatted.replace(
    /^(?!\s*#)\s*(第[一二三四五六七八九十百千万零两〇0-9]+(?:章|节|部分|幕|回)\s*[：:]?\s*.*)$/gm,
    '## $1'
  );

  return formatted;
}

export default function LiteratureReview() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = ((location.state as any) || getLatestSnapshotState() || {}) as any;
  const storyData = state?.storyData;
  const storyVersionBadge = getModelVersionBadge('/editor/literature-review', state);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [reviewData, setReviewData] = useState<LiteratureData | null>(state?.literatureData || null);
  const [isEditingVersion, setIsEditingVersion] = useState(false);
  const [editableContent, setEditableContent] = useState('');

  const displayedVersionContent = String(reviewData?.revised_content || storyData?.content || '');

  const jumpToStep = (step: ReviewStepKey) => {
    const routeMap: Record<ReviewStepKey, string> = {
      literature: '/editor/literature-review',
      science: '/editor/science-review',
      audience: '/editor/reader-feedback',
    };
    navigate(routeMap[step], { state });
  };

  const runReview = async () => {
    if (!storyData?.id || !storyData?.content) {
      return;
    }

    setIsLoading(true);
    setError('');
    try {
      const response = await fetchApi('/api/literature/review', {
        method: 'POST',
        body: JSON.stringify({
          story_id: storyData.id,
          title: storyData.title || '未命名故事',
          content: storyData.content,
        }),
      });

      const data = await response.json();
      if (data.code !== 200) {
        throw new Error(data.msg || '文学审核失败');
      }

      const result: LiteratureData = data.data || {};
      setReviewData(result);

      navigate(location.pathname, {
        replace: true,
        state: {
          ...(state || {}),
          literatureData: result,
          storyData: {
            ...(storyData || {}),
            content: result.revised_content || storyData.content,
          },
        },
      });
    } catch (err: any) {
      setError(err.message || '请求失败，请确认后端服务状态');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartEditVersion = () => {
    setEditableContent(displayedVersionContent);
    setIsEditingVersion(true);
  };

  const handleCancelEditVersion = () => {
    setIsEditingVersion(false);
    setEditableContent('');
  };

  const handleSaveEditedVersion = () => {
    const nextContent = editableContent.trim();
    if (!nextContent) {
      return;
    }

    const nextReviewData: LiteratureData = {
      ...(reviewData || {}),
      revised_content: nextContent,
    };
    setReviewData(nextReviewData);
    setIsEditingVersion(false);

    navigate(location.pathname, {
      replace: true,
      state: {
        ...(state || {}),
        literatureData: nextReviewData,
        storyData: {
          ...(storyData || {}),
          content: nextContent,
        },
      },
    });
  };

  useEffect(() => {
    if (reviewData) return;
    if (!storyData?.id || !storyData?.content) return;
    runReview();
  }, []);

  if (!storyData?.id || !storyData?.content) {
    return (
      <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.06)] border border-gray-100 p-6 min-h-[500px]">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">2.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">文学性检查</h3>
            <p className="text-sm text-gray-500">需要先完成故事草稿生成，再进行文学审查。</p>
          </div>
        </div>

        <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[320px] bg-gray-50/50 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-500 mb-4">暂未检测到故事初稿，请先回到第 1 步生成故事。</p>
            <button
              onClick={() => navigate('/editor/draft', { state })}
              className="px-5 py-2.5 bg-[#FF9F45] text-white rounded-[12px] font-medium hover:bg-[#FF8C1A] transition-all"
            >
              前往故事草稿
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.06)] border border-gray-100 p-6 min-h-[500px]">
      <ReviewProgress
        currentStep="literature"
        literatureDone={!!reviewData}
        scienceDone={!!state?.scienceData}
        audienceDone={!!state?.readerData}
        onStepClick={jumpToStep}
      />

      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">2.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">文学性检查</h3>
            <p className="text-sm text-gray-500">展示文学审查 Agent 的评价建议与润色后的正文版本。</p>
          </div>
        </div>

        <button
          onClick={runReview}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-orange-200 text-[#FF9F45] bg-orange-50 hover:bg-orange-100 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
          重新审查
        </button>
      </div>

      <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[350px] bg-gray-50/50">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center min-h-[260px] text-gray-400 gap-3">
            <Loader2 className="animate-spin text-[#FF9F45]" size={36} />
            <p>文学评审 Agent 正在审读并润色，请稍候...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center min-h-[260px] text-red-400 gap-3">
            <p>{error}</p>
            <button
              onClick={runReview}
              className="px-4 py-2 mt-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition"
            >
              重试
            </button>
          </div>
        ) : reviewData ? (
          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-base font-bold text-gray-900">审查结论</h4>
                <span className={
                  reviewData.passed
                    ? 'text-xs px-2.5 py-1 rounded-full bg-green-50 text-green-700 border border-green-200'
                    : 'text-xs px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200'
                }>
                  {reviewData.passed ? '通过' : '需优化'}
                </span>
              </div>
              <p className="text-sm leading-7 text-gray-700 whitespace-pre-wrap">
                {reviewData.feedback || '暂无评价内容'}
              </p>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h4 className="text-base font-bold text-gray-900">润色后版本</h4>
                <div className="flex items-center gap-2">
                  <span className="shrink-0 inline-flex items-center rounded-full border border-orange-200 bg-orange-50 px-3 py-1 text-[12px] font-bold text-[#B75A00]">
                    {storyVersionBadge}
                  </span>
                  {!isEditingVersion ? (
                    <button
                      onClick={handleStartEditVersion}
                      className="inline-flex items-center gap-1 rounded-md border border-orange-200 bg-white px-2.5 py-1 text-xs font-semibold text-[#B75A00] hover:bg-orange-50"
                    >
                      <Pencil size={13} /> 编辑
                    </button>
                  ) : null}
                </div>
              </div>
              {isEditingVersion ? (
                <div className="space-y-3">
                  <textarea
                    value={editableContent}
                    onChange={(e) => setEditableContent(e.target.value)}
                    className="min-h-[320px] w-full rounded-lg border border-gray-300 px-3 py-2 text-sm leading-7 text-gray-700 outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={handleCancelEditVersion}
                      className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-50"
                    >
                      <X size={13} /> 取消
                    </button>
                    <button
                      onClick={handleSaveEditedVersion}
                      className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100"
                    >
                      <Save size={13} /> 保存
                    </button>
                  </div>
                </div>
              ) : (
                <div className="prose prose-orange max-w-none text-[15px] leading-relaxed text-gray-700">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      h1: ({ children }) => (
                        <h1 className="mt-2 mb-6 text-3xl font-extrabold text-gray-900 tracking-tight">
                          {children}
                        </h1>
                      ),
                      h2: ({ children }) => (
                        <h2 className="mt-7 mb-3 text-xl font-bold text-gray-900 border-l-4 border-orange-400 pl-3">
                          {children}
                        </h2>
                      ),
                      h3: ({ children }) => (
                        <h3 className="mt-6 mb-3 text-lg font-bold text-gray-900">{children}</h3>
                      ),
                      p: ({ children }) => <p className="mb-2 leading-8">{children}</p>,
                    }}
                  >
                    {formatLiteratureContent(displayedVersionContent)}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center min-h-[260px] text-gray-400">等待文学审查结果...</div>
        )}
      </div>
    </div>
  );
}
