import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Brush,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  AlertTriangle,
  Clock3,
  Users,
  Loader2,
  RefreshCw,
  Wand2,
  XCircle,
  Zap,
  AlertCircle,
  Eye,
  Cpu,
  Palette,
} from 'lucide-react';
import { fetchApi } from '../../lib/api';

type Scene = {
  scene_id: number;
  text_chunk?: string;
  summary?: string;
  image_prompt?: string;
  image_url?: string;
};

function resolveArtStyle(formData: any) {
  const map: Record<string, string> = {
    '1': '卡通风格',
    '2': '儿童绘画风格',
    '3': '水彩画风格',
    '4': '写真风格',
    '5': '3D渲染风格',
  };

  if (!formData?.artStyle) return '卡通风格';
  return map[formData.artStyle] || formData.artStyle;
}

type CharacterDescription = {
  gender: 'male' | 'female' | 'neutral';
  ageRange: string;
  hairStyle: string;
  clothing: string;
  features: string[];
};

type CharacterConfig = {
  referenceImage?: string;
  description: CharacterDescription;
  consistencyLevel: 'high' | 'medium' | 'low';
};

type ReviewStatus = 'pending' | 'needs_fix' | 'passed';
type CharacterConsistencyStatus = 'consistent' | 'minor_diff' | 'inconsistent' | 'pending';
type FinalStatus = 'approved' | 'needs_revision' | 'rejected';

type CharacterSummary = {
  appearance?: string;
  clothing?: string;
  style?: string;
};

type CharacterConsistencyIssue = {
  type?: string;
  description?: string;
  scene_ids?: number[];
};

type IllogicalIssueItem = {
  category?: string;
  severity?: 'critical' | 'major' | 'minor';
  description?: string;
  location?: string;
  suggestion?: string;
};

type IllogicalSceneCheck = {
  has_illogical_issues?: boolean;
  issues?: IllogicalIssueItem[];
  overall_assessment?: string;
  fix_priority?: string[];
};

type CharacterConsistency = {
  status: CharacterConsistencyStatus;
  score: number;
  issues: CharacterConsistencyIssue[];
  character_summary: CharacterSummary;
  suggestion: string;
  priority_fixes: string[];
};

type SceneReview = {
  scene_id: number;
  science_status: ReviewStatus;
  science_reason: string;
  science_suggestion: string;
  logic_issues: string[];
  visual_suggestions: string;
  illogical_check?: IllogicalSceneCheck;
  character_consistency: CharacterConsistency;
};

type OverallSummary = {
  science_pass_rate: number;
  character_consistency_score: number;
  total_scenes: number;
  passed_science: number;
  needs_fix_science: number;
  warning_science: number;
};

type ComprehensiveReview = {
  final_status: FinalStatus;
  overall_score: number;
  science_score: number;
  consistency_score: number;
  logic_score: number;
  summary: string;
  required_fixes: string[];
  optional_improvements: string[];
  estimated_rework_effort: 'low' | 'medium' | 'high';
};

type ReviewResponse = {
  code: number;
  msg?: string;
  data: {
    reviews: SceneReview[];
    overall_summary: OverallSummary;
    character_consistency_overall?: CharacterConsistency;
    comprehensive_review?: ComprehensiveReview;
  };
};

type CollapsibleBlockProps = {
  expanded: boolean;
  onToggle: () => void;
  children: any;
  collapsedLines?: number;
  lineHeightPx?: number;
};

function CollapsibleBlock({
  expanded,
  onToggle,
  children,
  collapsedLines = 3,
  lineHeightPx = 28,
}: CollapsibleBlockProps) {
  const collapsedMaxHeight = collapsedLines * lineHeightPx;
  const contentRef = useRef<HTMLDivElement | null>(null);
  const [hasOverflow, setHasOverflow] = useState(false);

  useEffect(() => {
    const node = contentRef.current;
    if (!node) return;

    const updateOverflow = () => {
      setHasOverflow(node.scrollHeight > collapsedMaxHeight + 1);
    };

    updateOverflow();

    const observer = new ResizeObserver(() => updateOverflow());
    observer.observe(node);

    return () => {
      observer.disconnect();
    };
  }, [children, collapsedMaxHeight]);

  return (
    <div>
      <div
        ref={contentRef}
        style={
          expanded || !hasOverflow
            ? undefined
            : {
                maxHeight: `${collapsedMaxHeight}px`,
                overflow: 'hidden',
              }
        }
      >
        {children}
      </div>
      {hasOverflow && (
        <button
          type="button"
          onClick={onToggle}
          className="mt-2 inline-flex items-center gap-1 rounded-md border border-orange-300 bg-orange-100 px-2.5 py-1 text-xs font-semibold text-orange-800 hover:bg-orange-200"
        >
          {expanded ? (
            <>
              <ChevronUp size={14} /> 收起
            </>
          ) : (
            <>
              <ChevronDown size={14} /> 展开
            </>
          )}
        </button>
      )}
    </div>
  );
}

function getScienceStatusBadge(status: ReviewStatus) {
  switch (status) {
    case 'passed':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-green-50 text-green-700 border border-green-200 px-2.5 py-1 text-xs font-bold">
          <CheckCircle2 size={14} />
          科学通过
        </span>
      );
    case 'needs_fix':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-50 text-red-700 border border-red-200 px-2.5 py-1 text-xs font-bold">
          <XCircle size={14} />
          需修改
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-gray-50 text-gray-600 border border-gray-200 px-2.5 py-1 text-xs font-bold">
          <Clock3 size={14} />
          待审核
        </span>
      );
  }
}

function extractConcreteIssues(review?: SceneReview): string[] {
  if (!review || review.science_status !== 'needs_fix') return [];

  const issues: string[] = [];
  const reason = String(review.science_reason || '').trim();
  if (reason) {
    const reasonParts = reason
      .split(/[；;。\n]/)
      .map((part) => part.trim())
      .filter(Boolean);
    issues.push(...reasonParts);
  }

  if (Array.isArray(review.logic_issues)) {
    review.logic_issues.forEach((item) => {
      const text = String(item || '').trim();
      if (text) issues.push(text);
    });
  }

  const suggestion = String(review.science_suggestion || '').trim();
  if (suggestion) {
    issues.push(suggestion);
  }

  return Array.from(new Set(issues)).slice(0, 5);
}

function getCharacterStatusBadge(status: CharacterConsistencyStatus, score?: number) {
  switch (status) {
    case 'consistent':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-green-50 text-green-700 border border-green-200 px-2.5 py-1 text-xs font-bold">
          <CheckCircle2 size={14} />
          人物一致
          {typeof score === 'number' && <span className="ml-1">({score}%)</span>}
        </span>
      );
    case 'minor_diff':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-yellow-50 text-yellow-700 border border-yellow-200 px-2.5 py-1 text-xs font-bold">
          <AlertTriangle size={14} />
          轻微差异
          {typeof score === 'number' && <span className="ml-1">({score}%)</span>}
        </span>
      );
    case 'inconsistent':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-50 text-red-700 border border-red-200 px-2.5 py-1 text-xs font-bold">
          <XCircle size={14} />
          不一致
          {typeof score === 'number' && <span className="ml-1">({score}%)</span>}
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-gray-50 text-gray-600 border border-gray-200 px-2.5 py-1 text-xs font-bold">
          <Clock3 size={14} />
          待检测
        </span>
      );
  }
}

function getFinalStatusBadge(status: FinalStatus) {
  switch (status) {
    case 'approved':
      return (
        <span className="inline-flex items-center gap-2 rounded-full bg-green-100 text-green-800 px-4 py-2 text-sm font-bold">
          <CheckCircle2 size={18} />
          审核通过
        </span>
      );
    case 'needs_revision':
      return (
        <span className="inline-flex items-center gap-2 rounded-full bg-yellow-100 text-yellow-800 px-4 py-2 text-sm font-bold">
          <RefreshCw size={18} />
          需要修改
        </span>
      );
    case 'rejected':
      return (
        <span className="inline-flex items-center gap-2 rounded-full bg-red-100 text-red-800 px-4 py-2 text-sm font-bold">
          <XCircle size={18} />
          建议重绘
        </span>
      );
  }
}

function getSeverityBadge(severity?: string) {
  switch (severity) {
    case 'critical':
      return <span className="inline-flex items-center rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs font-bold">严重</span>;
    case 'major':
      return <span className="inline-flex items-center rounded-full bg-orange-100 text-orange-700 px-2 py-0.5 text-xs font-bold">主要</span>;
    case 'minor':
      return <span className="inline-flex items-center rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-xs font-bold">轻微</span>;
    default:
      return null;
  }
}

function createInitialReviews(scenes: Scene[]): SceneReview[] {
  return scenes.map((scene) => ({
    scene_id: scene.scene_id,
    science_status: 'pending',
    science_reason: '待审核',
    science_suggestion: '点击"开始审核所有插画"后生成审核结果。',
    logic_issues: [],
    visual_suggestions: '',
    character_consistency: {
      status: 'pending',
      score: 0,
      issues: [],
      character_summary: {},
      suggestion: '',
      priority_fixes: [],
    },
  }));
}

export default function IllustrationReview() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state || {}) as any;

  const scenes: Scene[] = Array.isArray(state.illustrations) ? state.illustrations : [];
  const characterConfig: CharacterConfig | undefined = state.formData?.characterConfig;

  const [reviewing, setReviewing] = useState(false);
  const [previewScene, setPreviewScene] = useState<Scene | null>(null);
  const [error, setError] = useState('');
  const [reviews, setReviews] = useState<SceneReview[]>(
    Array.isArray(state?.illustrationReview) && state.illustrationReview.length === scenes.length
      ? state.illustrationReview
      : createInitialReviews(scenes),
  );
  const [overallSummary, setOverallSummary] = useState<OverallSummary | null>(
    state?.illustrationReviewSummary || null,
  );
  const [comprehensiveReview, setComprehensiveReview] = useState<ComprehensiveReview | null>(
    state?.comprehensiveReview || null,
  );
  const [characterConsistencyOverall, setCharacterConsistencyOverall] = useState<CharacterConsistency | null>(
    state?.characterConsistencyOverall || null,
  );
  const [regeneratingIds, setRegeneratingIds] = useState<Record<number, boolean>>({});
  const [manualFixInputs, setManualFixInputs] = useState<Record<number, string>>({});
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  const isExpanded = useCallback(
    (key: string) => !!expandedSections[key],
    [expandedSections],
  );

  const toggleExpanded = useCallback((key: string) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);
  const [bulkFixing, setBulkFixing] = useState(false);

  const artStyle = useMemo(() => resolveArtStyle(state?.formData || {}), [state?.formData]);
  const extraDrawReq = String(state?.formData?.extraDrawReq || '');

  const pendingCount = useMemo(() => reviews.filter((item) => item.science_status === 'pending').length, [reviews]);
  const needFixCount = useMemo(() => reviews.filter((item) => item.science_status === 'needs_fix').length, [reviews]);
  const passedCount = useMemo(() => reviews.filter((item) => item.science_status === 'passed').length, [reviews]);

  const inconsistentScenes = useMemo(() => {
    return reviews.filter(
      (r) => r.character_consistency.status === 'inconsistent' || r.character_consistency.status === 'minor_diff',
    );
  }, [reviews]);

  const failedScenes = useMemo(() => {
    return reviews.filter((r) => r.science_status === 'needs_fix');
  }, [reviews]);

  useEffect(() => {
    const onEsc = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setPreviewScene(null);
      }
    };

    window.addEventListener('keydown', onEsc);
    return () => {
      window.removeEventListener('keydown', onEsc);
    };
  }, []);

  const handleRunReview = useCallback(async () => {
    setReviewing(true);
    setError('');
    try {
      const requestBody: any = {
        story_id: state.storyData?.id,
        scenes: scenes.map((s) => ({
          scene_id: s.scene_id,
          image_url: s.image_url,
          summary: s.summary,
          image_prompt: s.image_prompt,
          text_chunk: s.text_chunk,
        })),
      };

      if (characterConfig) {
        requestBody.character_config = characterConfig;
      }

      console.log('发送审核请求:', requestBody);

      const response = await fetchApi('/api/illustration-review/review', {
        method: 'POST',
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`HTTP错误: ${response.status} ${response.statusText}`);
      }

      const data: ReviewResponse = await response.json();
      console.log('收到审核响应:', data);

      if (data.code !== 200) {
        throw new Error(data.msg || '审核失败');
      }

      if (!data.data || !Array.isArray(data.data.reviews)) {
        throw new Error('返回数据格式不正确');
      }

      setReviews(data.data.reviews);
      setOverallSummary(data.data.overall_summary);
      setComprehensiveReview(data.data.comprehensive_review || null);
      setCharacterConsistencyOverall(data.data.character_consistency_overall || null);

      // 保存到 state 以便页面刷新后还能看到
      navigate(location.pathname, {
        replace: true,
        state: {
          ...(state || {}),
          illustrationReview: data.data.reviews,
          illustrationReviewSummary: data.data.overall_summary,
          comprehensiveReview: data.data.comprehensive_review,
          characterConsistencyOverall: data.data.character_consistency_overall,
        },
      });
    } catch (err: any) {
      console.error('审核失败:', err);
      setError(err.message || '请求失败，请确认后端服务已启动');
    } finally {
      setReviewing(false);
    }
  }, [scenes, characterConfig, state, location.pathname, navigate]);

  const regenerateInconsistent = useCallback(async () => {
    const targetScenes = inconsistentScenes.map((r) => scenes.find((s) => s.scene_id === r.scene_id)).filter(Boolean) as Scene[];

    for (const scene of targetScenes) {
      setRegeneratingIds((prev) => ({ ...prev, [scene.scene_id]: true }));

      try {
        const requestBody: any = {
          story_id: state.storyData?.id,
          scene_id: scene.scene_id,
          image_prompt: scene.image_prompt || '',
          feedback: '请确保人物形象与之前的插画保持一致',
          art_style: artStyle,
          extra_requirements: state.formData?.extraDrawReq || '',
        };

        if (characterConfig) {
          requestBody.character_config = characterConfig;
        }

        const response = await fetchApi('/api/illustrator/regenerate', {
          method: 'POST',
          body: JSON.stringify(requestBody),
        });

        const data = await response.json();
        if (data.code !== 200) {
          console.error(`分镜 ${scene.scene_id} 重绘失败:`, data.msg);
          continue;
        }

        const updated = data.data || {};
        const nextScenes = scenes.map((item) => {
          if (item.scene_id !== scene.scene_id) return item;
          return {
            ...item,
            image_url: updated.image_url || item.image_url,
            image_prompt: updated.image_prompt || item.image_prompt,
          };
        });

        scenes.splice(0, scenes.length, ...nextScenes);

        setReviews((prev) =>
          prev.map((r) => {
            if (r.scene_id !== scene.scene_id) return r;
            return {
              ...r,
              science_status: 'pending',
              character_consistency: { ...r.character_consistency, status: 'pending' },
            };
          }),
        );

        navigate(location.pathname, {
          replace: true,
          state: {
            ...(state || {}),
            illustrations: nextScenes,
          },
        });
      } catch (err) {
        console.error(`分镜 ${scene.scene_id} 重绘失败:`, err);
      } finally {
        setRegeneratingIds((prev) => ({ ...prev, [scene.scene_id]: false }));
      }
    }
  }, [inconsistentScenes, scenes, characterConfig, state, artStyle, location.pathname, navigate]);

  const buildAutoFixFeedback = useCallback((scene: Scene, review?: SceneReview) => {
    const lines: string[] = [];
    lines.push('请根据以下审核意见修正当前分镜插画，保持原剧情不变，并提升科学准确性与逻辑合理性。');

    const scienceReason = String(review?.science_reason || '').trim();
    if (scienceReason) {
      lines.push(`科学审查结论：${scienceReason}`);
    }

    const concreteIssues = extractConcreteIssues(review);
    if (concreteIssues.length > 0) {
      lines.push(`未通过问题：${concreteIssues.join('；')}`);
    }

    const logicIssues = Array.isArray(review?.illogical_check?.issues) ? review!.illogical_check!.issues! : [];
    if (logicIssues.length > 0) {
      const logicTexts = logicIssues
        .map((item) => {
          const category = String(item?.category || '').trim();
          const desc = String(item?.description || '').trim();
          const sug = String(item?.suggestion || '').trim();
          return [category ? `[${category}]` : '', desc, sug ? `建议:${sug}` : '']
            .filter(Boolean)
            .join(' ');
        })
        .filter(Boolean);
      if (logicTexts.length > 0) {
        lines.push(`逻辑问题：${logicTexts.join('；')}`);
      }
    }

    const scienceSuggestion = String(review?.science_suggestion || '').trim();
    if (scienceSuggestion) {
      lines.push(`审核建议：${scienceSuggestion}`);
    }

    if (scene.summary) {
      lines.push(`分镜摘要：${scene.summary}`);
    }

    lines.push('输出要求：保持人物与画风一致；修复错误细节；避免新增与原文冲突的元素。');
    return lines.join('\n');
  }, []);

  const regenerateSceneByFeedback = useCallback(async (scene: Scene, feedback: string) => {
    const cleanFeedback = String(feedback || '').trim();
    if (!cleanFeedback) return;

    setRegeneratingIds((prev) => ({ ...prev, [scene.scene_id]: true }));
    setError('');
    try {
      const requestBody: any = {
        story_id: state.storyData?.id,
        scene_id: scene.scene_id,
        image_prompt: scene.image_prompt || '',
        feedback: cleanFeedback,
        art_style: artStyle,
        extra_requirements: extraDrawReq,
      };

      if (characterConfig) {
        requestBody.character_config = characterConfig;
      }

      const response = await fetchApi('/api/illustrator/regenerate', {
        method: 'POST',
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();
      if (data.code !== 200) {
        throw new Error(data.msg || `分镜 ${scene.scene_id} 重绘失败`);
      }

      const updated = data.data || {};
      const nextScenes = scenes.map((item) => {
        if (item.scene_id !== scene.scene_id) return item;
        return {
          ...item,
          image_url: updated.image_url || item.image_url,
          image_prompt: updated.image_prompt || item.image_prompt,
        };
      });

      scenes.splice(0, scenes.length, ...nextScenes);
      setManualFixInputs((prev) => ({ ...prev, [scene.scene_id]: '' }));

      setReviews((prev) =>
        prev.map((r) => {
          if (r.scene_id !== scene.scene_id) return r;
          return {
            ...r,
            science_status: 'pending',
            science_reason: '已按建议重绘，建议重新审核确认。',
            logic_issues: [],
            illogical_check: {
              ...(r.illogical_check || {}),
              has_illogical_issues: false,
              issues: [],
            },
            character_consistency: {
              ...r.character_consistency,
              status: 'pending',
            },
          };
        }),
      );

      navigate(location.pathname, {
        replace: true,
        state: {
          ...(state || {}),
          illustrations: nextScenes,
        },
      });
    } catch (err: any) {
      setError(err.message || `分镜 ${scene.scene_id} 重绘失败`);
    } finally {
      setRegeneratingIds((prev) => ({ ...prev, [scene.scene_id]: false }));
    }
  }, [state, artStyle, extraDrawReq, characterConfig, scenes, location.pathname, navigate]);

  const regenerateByAutoSuggestion = useCallback(async (scene: Scene) => {
    const review = reviews.find((r) => r.scene_id === scene.scene_id);
    const feedback = buildAutoFixFeedback(scene, review);
    await regenerateSceneByFeedback(scene, feedback);
  }, [reviews, buildAutoFixFeedback, regenerateSceneByFeedback]);

  const regenerateByManualSuggestion = useCallback(async (scene: Scene) => {
    const feedback = String(manualFixInputs[scene.scene_id] || '').trim();
    if (!feedback) return;
    await regenerateSceneByFeedback(scene, feedback);
  }, [manualFixInputs, regenerateSceneByFeedback]);

  const bulkAutoFixFailedScenes = useCallback(async () => {
    if (bulkFixing) return;

    const targets = failedScenes
      .map((review) => ({
        scene: scenes.find((s) => s.scene_id === review.scene_id),
        review,
      }))
      .filter((item): item is { scene: Scene; review: SceneReview } => !!item.scene);

    if (targets.length === 0) {
      return;
    }

    setBulkFixing(true);
    setError('');
    try {
      for (const item of targets) {
        const feedback = buildAutoFixFeedback(item.scene, item.review);
        await regenerateSceneByFeedback(item.scene, feedback);
      }
    } finally {
      setBulkFixing(false);
    }
  }, [bulkFixing, failedScenes, scenes, buildAutoFixFeedback, regenerateSceneByFeedback]);

  if (!scenes.length) {
    return (
      <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.06)] border border-gray-100 p-6 min-h-[500px]">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">7.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">插画科学审核</h3>
            <p className="text-sm text-gray-500">需要先完成插画生成，再进行插画科学审核。</p>
          </div>
        </div>

        <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[320px] bg-gray-50/50 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-500 mb-4">暂未检测到插画内容，请先完成插画步骤。</p>
            <button
              onClick={() => navigate('/editor/illustration', { state })}
              className="px-5 py-2.5 bg-[#FF9F45] text-white rounded-[12px] font-medium hover:bg-[#FF8C1A] transition-all"
            >
              前往插画生成
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.06)] border border-gray-100 p-6 min-h-[500px]">
      <button
        onClick={() => navigate('/editor/illustration', { state })}
        className="mb-5 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
      >
        <ArrowLeft size={14} />
        返回插画
      </button>

      <div className="mb-6">
        <h2 className="text-[50px] leading-none font-extrabold text-[#F27D2F] inline-flex items-center gap-2">
          <Brush size={36} />
          插画科学审核
        </h2>
        <p className="mt-2 text-[30px] font-bold text-[#6B625A]">确保所有插画内容符合科学原理，准确传达科普知识</p>
      </div>

      <div className="mb-6 rounded-[24px] border border-[#E7E2DB] bg-[#FAF9F6] p-6">
        <h3 className="text-[30px] font-extrabold text-[#2D2A26]">审核进度</h3>
        <p className="text-[26px] text-[#6D665F] mt-1">
          插画科学准确性审核
          {characterConfig && (
            <span className="ml-3 text-lg text-[#FF9F45] inline-flex items-center gap-1">
              <Users size={18} />
              已启用人物一致性检查
            </span>
          )}
        </p>

        {comprehensiveReview && (
          <div className="mt-4 p-4 bg-white rounded-xl border-2 border-orange-200">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <span className="text-sm font-semibold text-gray-700">综合结论：</span>
                {getFinalStatusBadge(comprehensiveReview.final_status)}
              </div>
              <div className="flex flex-wrap gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <span className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                    <CheckCircle2 size={16} className="text-green-600" />
                  </span>
                  <span className="text-gray-600">科学</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center">
                    <Users size={16} className="text-orange-600" />
                  </span>
                  <span className="text-gray-600">一致</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                    <Zap size={16} className="text-blue-600" />
                  </span>
                  <span className="text-gray-600">逻辑</span>
                </div>
              </div>
            </div>
            {comprehensiveReview.required_fixes?.length > 0 && (
              <div className="mt-3">
                <p className="text-sm font-semibold text-red-700 mb-1">必须修复：</p>
                <ul className="text-sm text-red-600 list-disc list-inside">
                  {comprehensiveReview.required_fixes.slice(0, 3).map((fix, i) => (
                    <li key={i}>{fix}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {overallSummary && !comprehensiveReview && (
          <div className="mt-4 p-4 bg-white rounded-xl border border-orange-100">
            <p className="text-sm font-semibold text-gray-700 mb-2">总体审核结果</p>
            <div className="flex flex-wrap gap-4 text-sm">
              <span className="text-gray-600">
                科学通过率: <span className="font-bold text-green-600">{Math.round(overallSummary.science_pass_rate)}%</span>
              </span>
              {characterConfig && (
                <span className="text-gray-600">
                  人物一致性平均分: <span className="font-bold text-[#FF9F45]">{Math.round(overallSummary.character_consistency_score)}%</span>
                </span>
              )}
            </div>
          </div>
        )}

        <div className="mt-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="rounded-xl p-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center rounded-full bg-[#B79AE9] text-white px-4 py-2 text-[18px] font-bold">
                待审核: {pendingCount}
              </span>
              <span className="inline-flex items-center rounded-full bg-[#F35252] text-white px-4 py-2 text-[18px] font-bold">
                需修改: {needFixCount}
              </span>
              <span className="inline-flex items-center rounded-full bg-[#2DBF64] text-white px-4 py-2 text-[18px] font-bold">
                已通过: {passedCount}
              </span>
            </div>
          </div>

          <div className="ml-auto flex flex-wrap items-center justify-end gap-3">
            {characterConfig && inconsistentScenes.length > 0 && (
              <button
                onClick={regenerateInconsistent}
                disabled={reviewing || Object.values(regeneratingIds).some(Boolean)}
                className="inline-flex items-center gap-2 rounded-full bg-yellow-500 text-white px-6 py-3 text-[16px] font-extrabold hover:bg-yellow-600 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                <Wand2 size={20} />
                {Object.values(regeneratingIds).some(Boolean) ? '重绘中...' : '重新生成不一致插画'}
              </button>
            )}

            {failedScenes.length > 0 && (
              <button
                onClick={bulkAutoFixFailedScenes}
                disabled={reviewing || bulkFixing || Object.values(regeneratingIds).some(Boolean)}
                className="inline-flex items-center gap-2 rounded-full bg-emerald-500 text-white px-6 py-3 text-[16px] font-extrabold hover:bg-emerald-600 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                {bulkFixing ? <Loader2 size={20} className="animate-spin" /> : <Wand2 size={20} />}
                {bulkFixing ? '批量修复中...' : `一键批量自动修复（${failedScenes.length}）`}
              </button>
            )}

            <button
              onClick={handleRunReview}
              disabled={reviewing}
              className="inline-flex items-center gap-2 rounded-full bg-[#F7933A] px-6 py-3 text-[16px] font-extrabold text-white hover:bg-[#EC8427] disabled:opacity-60"
            >
              <Sparkles size={20} />
              {reviewing ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  审核中...
                </>
              ) : (
                '开始审核所有插画'
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
            <button
              onClick={handleRunReview}
              className="ml-3 underline hover:text-red-900"
            >
              重试
            </button>
          </div>
        )}
      </div>

      {characterConsistencyOverall && characterConsistencyOverall.status !== 'pending' && (
        <div className="mb-6 rounded-2xl border border-orange-200 bg-orange-50/50 p-5">
          <h3 className="text-lg font-bold text-orange-900 mb-3 flex items-center gap-2">
            <Users size={20} />
            人物一致性总体分析
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            {characterConsistencyOverall.character_summary?.appearance && (
              <div className="bg-white rounded-xl p-3 border border-orange-100">
                <p className="text-xs font-semibold text-orange-700 mb-1 flex items-center gap-1">
                  <Eye size={14} /> 外貌特征
                </p>
                <p className="text-sm text-gray-700">{characterConsistencyOverall.character_summary.appearance}</p>
              </div>
            )}
            {characterConsistencyOverall.character_summary?.clothing && (
              <div className="bg-white rounded-xl p-3 border border-orange-100">
                <p className="text-xs font-semibold text-orange-700 mb-1 flex items-center gap-1">
                  <Palette size={14} /> 服装特征
                </p>
                <p className="text-sm text-gray-700">{characterConsistencyOverall.character_summary.clothing}</p>
              </div>
            )}
            {characterConsistencyOverall.character_summary?.style && (
              <div className="bg-white rounded-xl p-3 border border-orange-100">
                <p className="text-xs font-semibold text-orange-700 mb-1 flex items-center gap-1">
                  <Cpu size={14} /> 画风特征
                </p>
                <p className="text-sm text-gray-700">{characterConsistencyOverall.character_summary.style}</p>
              </div>
            )}
          </div>
          {characterConsistencyOverall.priority_fixes?.length > 0 && (
            <div className="mt-3">
              <p className="text-sm font-semibold text-red-700 mb-1">优先修复：</p>
              <ul className="text-sm text-red-600 list-disc list-inside">
                {characterConsistencyOverall.priority_fixes.map((fix, i) => (
                  <li key={i}>{fix}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 gap-5">
        {scenes.map((scene) => {
          const review = reviews.find((item) => item.scene_id === scene.scene_id);
          const isRegenerating = regeneratingIds[scene.scene_id];
          const concreteIssues = extractConcreteIssues(review);
          const scienceKey = `scene-${scene.scene_id}-science`;
          const issuesKey = `scene-${scene.scene_id}-issues`;
          const logicKey = `scene-${scene.scene_id}-logic`;

          return (
            <div key={scene.scene_id} className="rounded-2xl border border-[#E6E1DA] bg-[#F9F8F5] overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#ECE7DF] px-5 py-4">
                <h4 className="text-[36px] font-extrabold text-[#2C2925]">插画 #{scene.scene_id}</h4>
                <div className="flex flex-wrap items-center gap-2">
                  {getScienceStatusBadge(review?.science_status || 'pending')}
                  {characterConfig &&
                    review?.character_consistency &&
                    getCharacterStatusBadge(
                      review.character_consistency.status,
                      review.character_consistency.score,
                    )}
                  {isRegenerating && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-1 text-xs font-bold">
                      <Loader2 size={14} className="animate-spin" />
                      重绘中...
                    </span>
                  )}
                </div>
              </div>

              <div className="p-4">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div>
                    <div className="rounded-xl border border-[#E6E1DA] bg-[#F4F7FB] overflow-hidden h-[280px] mb-3 flex items-center justify-center p-2">
                      {scene.image_url ? (
                        <img
                          src={scene.image_url}
                          alt={`scene-${scene.scene_id}`}
                          className="h-full w-full object-contain cursor-zoom-in"
                          onClick={() => setPreviewScene(scene)}
                        />
                      ) : (
                        <div className="text-gray-400 text-sm">暂无图片</div>
                      )}
                    </div>
                    {scene.summary && (
                      <div className="text-sm text-gray-600">
                        <span className="font-semibold">画面摘要：</span>
                        {scene.summary}
                      </div>
                    )}
                  </div>

                  <div className="space-y-4">
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                      <h5 className="text-sm font-bold text-gray-800 mb-2 flex items-center gap-2">
                        <Zap size={16} className="text-green-600" />
                        科学审核结论
                      </h5>
                      <CollapsibleBlock
                        expanded={isExpanded(scienceKey)}
                        onToggle={() => toggleExpanded(scienceKey)}
                        collapsedLines={3}
                        lineHeightPx={28}
                      >
                        <p className="text-sm leading-7 text-gray-700">{review?.science_reason || '待审核'}</p>
                      </CollapsibleBlock>
                      {review?.science_status === 'needs_fix' && concreteIssues.length > 0 && (
                        <div className="mt-2 rounded-lg border border-red-200 bg-red-50 p-3">
                          <p className="text-sm font-semibold text-red-700 mb-1">未通过具体问题：</p>
                          <CollapsibleBlock
                            expanded={isExpanded(issuesKey)}
                            onToggle={() => toggleExpanded(issuesKey)}
                            collapsedLines={3}
                            lineHeightPx={24}
                          >
                            <ul className="list-disc pl-5 text-sm text-red-700 space-y-1">
                              {concreteIssues.map((item, idx) => (
                                <li key={idx}>{item}</li>
                              ))}
                            </ul>
                          </CollapsibleBlock>
                        </div>
                      )}
                      {review?.science_status === 'passed' && review?.science_suggestion && review.science_suggestion !== '点击"开始审核所有插画"后生成审核结果。' && (
                        <p className="mt-2 text-sm leading-7 text-gray-500">
                          <span className="font-semibold">建议：</span>
                          {review.science_suggestion}
                        </p>
                      )}
                    </div>

                    {review?.illogical_check && review.illogical_check.has_illogical_issues && (
                      <div className="bg-white rounded-xl border border-red-200 p-4">
                        <h5 className="text-sm font-bold text-red-800 mb-2 flex items-center gap-2">
                          <AlertCircle size={16} />
                          逻辑问题检测
                        </h5>
                        <CollapsibleBlock
                          expanded={isExpanded(logicKey)}
                          onToggle={() => toggleExpanded(logicKey)}
                          collapsedLines={3}
                          lineHeightPx={24}
                        >
                          <ul className="space-y-2">
                            {review.illogical_check.issues?.map((issue, idx) => (
                              <li key={idx} className="text-sm">
                                <div className="flex items-start gap-2">
                                  {getSeverityBadge(issue.severity)}
                                  <div>
                                    <span className="text-gray-500 text-xs">[{issue.category}]</span>{' '}
                                    <span className="text-gray-700">{issue.description}</span>
                                    {issue.location && <span className="text-gray-500 text-xs"> ({issue.location})</span>}
                                    {issue.suggestion && (
                                      <p className="text-gray-500 text-xs mt-1">建议：{issue.suggestion}</p>
                                    )}
                                  </div>
                                </div>
                              </li>
                            ))}
                          </ul>
                        </CollapsibleBlock>
                      </div>
                    )}

                    {characterConfig && review?.character_consistency && (
                      <div className="bg-white rounded-xl border border-orange-200 p-4">
                        <h5 className="text-sm font-bold text-orange-800 mb-2 inline-flex items-center gap-1">
                          <Users size={14} />
                          人物一致性审核
                        </h5>
                        {review.character_consistency.issues?.length > 0 ? (
                          <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                            {review.character_consistency.issues.slice(0, 3).map((issue, idx) => (
                              <li key={idx}>
                                {typeof issue === 'object' ? (
                                  <>
                                    <span className="text-xs text-orange-600">[{issue.type}]</span>{' '}
                                    {issue.description}
                                    {issue.scene_ids && <span className="text-gray-500 text-xs"> (分镜{issue.scene_ids.join(',')})</span>}
                                  </>
                                ) : (
                                  String(issue)
                                )}
                              </li>
                            ))}
                          </ul>
                        ) : review.character_consistency.status === 'consistent' ? (
                          <p className="text-sm text-green-700">人物形象保持一致</p>
                        ) : (
                          <p className="text-sm text-gray-500">暂无人物一致性问题</p>
                        )}
                        {review.character_consistency.suggestion && (
                          <p className="mt-2 text-sm text-gray-500">
                            <span className="font-semibold">建议：</span>
                            {review.character_consistency.suggestion}
                          </p>
                        )}
                      </div>
                    )}

                    <div className="bg-white rounded-xl border border-emerald-200 p-4">
                      <h5 className="text-sm font-bold text-emerald-800 mb-2 flex items-center gap-2">
                        <Wand2 size={16} />
                        根据审核建议改图
                      </h5>
                      <p className="text-xs text-gray-600 mb-3 leading-6">
                        可直接按审核问题自动改图，或输入手动修改意见后重绘。
                      </p>

                      <div className="flex flex-wrap items-center gap-2 mb-3">
                        <button
                          onClick={() => regenerateByAutoSuggestion(scene)}
                          disabled={!!regeneratingIds[scene.scene_id]}
                          className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-3 py-2 text-xs font-bold text-white hover:bg-emerald-600 disabled:opacity-60"
                        >
                          {regeneratingIds[scene.scene_id] ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                          自动按建议改图
                        </button>
                      </div>

                      <textarea
                        value={manualFixInputs[scene.scene_id] || ''}
                        onChange={(e) => setManualFixInputs((prev) => ({ ...prev, [scene.scene_id]: e.target.value }))}
                        placeholder="手动输入修改要求，例如：把毛细管结构画成纤维束剖面，并标出液体上升方向与反光。"
                        className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all shadow-sm resize-none h-24"
                      />
                      <div className="mt-2">
                        <button
                          onClick={() => regenerateByManualSuggestion(scene)}
                          disabled={!!regeneratingIds[scene.scene_id] || !(manualFixInputs[scene.scene_id] || '').trim()}
                          className="inline-flex items-center gap-2 rounded-lg bg-[#FF9F45] px-3 py-2 text-xs font-bold text-white hover:bg-[#FF8C1A] disabled:opacity-60"
                        >
                          {regeneratingIds[scene.scene_id] ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
                          按手动意见改图
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {previewScene?.image_url ? (
        <div
          className="fixed inset-0 z-[80] bg-black/70 backdrop-blur-[1px] flex items-center justify-center p-4"
          onClick={() => setPreviewScene(null)}
        >
          <div
            className="w-full max-w-5xl rounded-2xl bg-white p-3 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-2 flex items-center justify-between px-1">
              <p className="text-sm font-semibold text-gray-700">插画 #{previewScene.scene_id} 预览</p>
              <button
                onClick={() => setPreviewScene(null)}
                className="text-sm px-3 py-1.5 rounded-md bg-gray-100 hover:bg-gray-200 text-gray-700"
              >
                关闭
              </button>
            </div>
            <div className="rounded-xl border border-gray-200 bg-[#F4F7FB] h-[78vh] flex items-center justify-center p-3">
              <img
                src={previewScene.image_url}
                alt={`scene-preview-${previewScene.scene_id}`}
                className="h-full w-full object-contain"
              />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
