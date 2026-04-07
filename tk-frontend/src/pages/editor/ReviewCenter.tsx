import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Baby, BookOpen, ChevronRight, Loader2, Microscope, RefreshCw } from 'lucide-react';
import { Fragment } from 'react';
import { fetchApi } from '../../lib/api';

type LiteratureData = {
  passed?: boolean;
  feedback?: string;
  revised_content?: string;
};

type GlossaryItem = {
  term?: string;
  explanation?: string;
};

type ScienceData = {
  passed?: boolean;
  issues?: string[];
  modifications_made?: string[];
  suggestions?: string;
  revised_content?: string;
  glossary?: GlossaryItem[];
  revised_glossary?: GlossaryItem[];
};

type ReaderData = {
  reader_feedback?: string;
  audience_feedback?: string;
  feedback?: string;
  comment?: string;
};

type StepKey = 'literature' | 'science' | 'reader';

function resolveTargetAudience(formData: any) {
  const targetMap: Record<string, string> = {
    '1': '青少幼年儿童',
    '2': '产业工人',
    '3': '老年人',
    '4': '领导干部和公务员',
    '5': '农民',
  };

  const subMap: Record<string, string> = {
    '1_1': '幼年儿童（3-6岁）',
    '1_2': '少儿群体（6-12岁）',
    '1_3': '青少年群体（12-28岁）',
  };

  if (formData?.targetAudience === '1' && formData?.subAudience) {
    return subMap[formData.subAudience] || '青少幼年儿童';
  }
  if (formData?.targetAudience) {
    return targetMap[formData.targetAudience] || '大众';
  }
  return '大众';
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

function shortText(text: string, maxLength = 140) {
  const value = (text || '').replace(/\s+/g, ' ').trim();
  if (!value) return '暂无结果';
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
}

function resolveReaderFeedbackText(data: ReaderData | null) {
  if (!data) return '';
  return data.reader_feedback || data.audience_feedback || data.feedback || data.comment || '';
}

export default function ReviewCenter() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state || {}) as any;
  const stateRef = useRef<any>(state);

  useEffect(() => {
    stateRef.current = (location.state || {}) as any;
  }, [location.state]);

  const formData = state?.formData || {};
  const storyData = state?.storyData;

  const [literatureData, setLiteratureData] = useState<LiteratureData | null>(state?.literatureData || null);
  const [scienceData, setScienceData] = useState<ScienceData | null>(state?.scienceData || null);
  const [readerData, setReaderData] = useState<ReaderData | null>(state?.readerData || null);

  const [runningStep, setRunningStep] = useState<StepKey | null>(null);
  const [error, setError] = useState('');

  const persistState = (patch: Record<string, any>) => {
    const merged = {
      ...(stateRef.current || {}),
      ...patch,
    };
    stateRef.current = merged;
    navigate(location.pathname, {
      replace: true,
      state: merged,
    });
  };

  const runLiterature = async (content: string) => {
    if (!storyData?.id || !storyData?.title || !content) return null;

    setRunningStep('literature');
    setError('');

    const response = await fetchApi('/api/literature/review', {
      method: 'POST',
      body: JSON.stringify({
        story_id: storyData.id,
        title: storyData.title,
        content,
        target_audience: resolveTargetAudience(formData),
        age_group: resolveAgeGroup(formData),
      }),
    });

    const data = await response.json();
    if (data.code !== 200) {
      throw new Error(data.msg || '文学审查失败');
    }

    const result: LiteratureData = data.data || {};
    setLiteratureData(result);

    const nextStory = {
      ...(storyData || {}),
      content: result.revised_content || content,
    };

    persistState({
      literatureData: result,
      storyData: nextStory,
    });

    return nextStory.content;
  };

  const runScience = async (content: string) => {
    if (!storyData?.id || !content) return null;

    setRunningStep('science');
    setError('');

    const response = await fetchApi('/api/check/verify', {
      method: 'POST',
      body: JSON.stringify({
        story_id: storyData.id,
        title: storyData.title || '未命名故事',
        content,
        target_audience: resolveTargetAudience(formData),
      }),
    });

    const data = await response.json();
    if (data.code !== 200) {
      throw new Error(data.msg || '科学审查失败');
    }

    const result: ScienceData = data.data || {};
    setScienceData(result);

    const nextStory = {
      ...(storyData || {}),
      content: result.revised_content || content,
      glossary: result.glossary || result.revised_glossary || storyData?.glossary || [],
    };

    persistState({
      scienceData: result,
      storyData: nextStory,
    });

    return nextStory.content;
  };

  const runReader = async (content: string) => {
    if (!storyData?.id || !content) return;

    setRunningStep('reader');
    setError('');

    const response = await fetchApi('/api/reader/evaluate', {
      method: 'POST',
      body: JSON.stringify({
        story_id: storyData.id,
        title: storyData.title || '未命名故事',
        content,
        target_audience: resolveTargetAudience(formData),
        age_group: resolveAgeGroup(formData),
      }),
    });

    const data = await response.json();
    if (data.code !== 200) {
      throw new Error(data.msg || '读者反馈生成失败');
    }

    const rawResult = (data.data || {}) as ReaderData;
    const result: ReaderData = {
      ...rawResult,
      reader_feedback:
        rawResult.reader_feedback ||
        rawResult.audience_feedback ||
        rawResult.feedback ||
        rawResult.comment ||
        '',
    };
    setReaderData(result);
    persistState({ readerData: result });
  };

  const runAll = async () => {
    if (!storyData?.id || !storyData?.content || runningStep) return;

    try {
      let content = storyData.content;

      if (!literatureData) {
        const next = await runLiterature(content);
        if (!next) return;
        content = next;
      } else {
        content = literatureData.revised_content || content;
      }

      if (!scienceData) {
        const next = await runScience(content);
        if (!next) return;
        content = next;
      } else {
        content = scienceData.revised_content || content;
      }

      if (!readerData) {
        await runReader(content);
      }
    } catch (err: any) {
      setError(err.message || '审查流程执行失败');
    } finally {
      setRunningStep(null);
    }
  };

  useEffect(() => {
    if (!storyData?.id || !storyData?.content) return;
    if (readerData && scienceData && literatureData) return;
    if (runningStep) return;
    runAll();
  }, [storyData?.id, storyData?.content, literatureData, scienceData, readerData, runningStep]);

  const modules = useMemo(() => {
    const finished = {
      literature: !!literatureData,
      science: !!scienceData,
      reader: !!readerData,
    };

    return [
      {
        key: 'literature' as StepKey,
        title: '文学家审核',
        desc: '审核文学性、语言表达和叙事结构',
        icon: BookOpen,
        activeColor: 'bg-[#FF9F45] text-white',
        done: finished.literature,
      },
      {
        key: 'science' as StepKey,
        title: '科学家审核',
        desc: '审核科学准确性和知识点正确性',
        icon: Microscope,
        activeColor: 'bg-[#8BB7F0] text-white',
        done: finished.science,
      },
      {
        key: 'reader' as StepKey,
        title: '儿童视角审核',
        desc: '审核是否适合目标年龄段儿童理解',
        icon: Baby,
        activeColor: 'bg-[#F6B66D] text-white',
        done: finished.reader,
      },
    ];
  }, [literatureData, scienceData, readerData]);

  if (!storyData?.id || !storyData?.content) {
    return (
      <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.06)] border border-gray-100 p-6 min-h-[500px]">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">2.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">审查</h3>
            <p className="text-sm text-gray-500">需要先完成故事草稿，再进行审查流程。</p>
          </div>
        </div>

        <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[320px] bg-gray-50/50 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-500 mb-4">暂未检测到故事正文，请先完成第 1 步。</p>
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
      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">2.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">审查进度</h3>
            <p className="text-sm text-gray-500">顺序审核模式：文学家 → 科学家 → 儿童视角</p>
          </div>
        </div>

        <button
          onClick={() => {
            setLiteratureData(null);
            setScienceData(null);
            setReaderData(null);
            persistState({ literatureData: null, scienceData: null, readerData: null });
            setTimeout(() => runAll(), 0);
          }}
          disabled={!!runningStep}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-orange-200 text-[#FF9F45] bg-orange-50 hover:bg-orange-100 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          {runningStep ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
          重新审查
        </button>
      </div>

      <div className="border border-gray-200 rounded-xl p-6 bg-[#FFFEFB]">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-center">
          {modules.map((item, idx) => {
            const Icon = item.icon;
            const isRunning = runningStep === item.key;
            const isDone = item.done;

            return (
              <Fragment key={item.key}>
                <div className="md:col-span-1 flex flex-col items-center text-center">
                  <div
                    className={
                      'w-16 h-16 rounded-full flex items-center justify-center mb-3 ' +
                      (isRunning || isDone ? item.activeColor : 'bg-gray-100 text-gray-400')
                    }
                  >
                    {isRunning ? <Loader2 size={24} className="animate-spin" /> : <Icon size={24} />}
                  </div>
                  <p className="text-lg font-semibold text-gray-900">{item.title}</p>
                  <p className="text-xs text-gray-500 mt-1">{item.desc}</p>
                </div>
                {idx < modules.length - 1 ? (
                  <div className="hidden md:flex md:col-span-1 justify-center text-gray-400">
                    <ChevronRight size={24} />
                  </div>
                ) : null}
              </Fragment>
            );
          })}
        </div>
      </div>

      {error ? (
        <div className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : null}

      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-lg border border-gray-200 p-4 bg-gray-50">
          <h4 className="text-sm font-bold text-gray-900 mb-2">文学家审核结果</h4>
          <p className="text-sm text-gray-700 leading-7">{shortText(literatureData?.feedback || '')}</p>
        </div>

        <div className="rounded-lg border border-gray-200 p-4 bg-gray-50">
          <h4 className="text-sm font-bold text-gray-900 mb-2">科学家审核结果</h4>
          <p className="text-sm text-gray-700 leading-7">{shortText(scienceData?.suggestions || '')}</p>
        </div>

        <div className="rounded-lg border border-gray-200 p-4 bg-gray-50">
          <h4 className="text-sm font-bold text-gray-900 mb-2">儿童视角反馈</h4>
          <p className="text-sm text-gray-700 leading-7">{shortText(resolveReaderFeedbackText(readerData))}</p>
        </div>
      </div>
    </div>
  );
}
