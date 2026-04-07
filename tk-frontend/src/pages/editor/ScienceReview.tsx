import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Loader2, RefreshCw, CheckCircle2, AlertTriangle, BookText, Brain, Link2, BadgeInfo, ChevronDown, ChevronRight, ChevronUp, Pencil, Save, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ReviewProgress, { type ReviewStepKey } from '../../components/ReviewProgress';
import { fetchApi } from '../../lib/api';
import { getModelVersionBadge } from '../../lib/workHistory';

type GlossaryItem = {
  term?: string;
  explanation?: string;
};

type GlossaryEntry = {
  term: string;
  explanation: string;
};

type ScienceData = {
  passed?: boolean;
  issues?: string[];
  modifications_made?: string[];
  suggestions?: string;
  review_sections?: ReviewSection[];
  highlight_terms?: string[];
  revised_content?: string;
  glossary?: GlossaryItem[];
  revised_glossary?: GlossaryItem[];
};

type CanonicalSection = '事实准确性校验' | '专业术语适用性检查' | '科学逻辑验证' | '引用来源建议';

type ReviewSection = {
  section?: string;
  status?: string;
  finding?: string;
  suggestion?: string;
  suggested_revision?: string;
  issue_list?: string[];
  modification_list?: string[];
  adopted?: boolean;
};

type NormalizedSection = {
  section: CanonicalSection;
  status: string;
  finding: string;
  suggestion: string;
  suggested_revision: string;
  issue_list: string[];
  modification_list: string[];
  adopted: boolean;
};

const SECTION_ORDER: CanonicalSection[] = [
  '事实准确性校验',
  '专业术语适用性检查',
  '科学逻辑验证',
  '引用来源建议',
];

const SECTION_ICON_MAP: Record<CanonicalSection, any> = {
  '事实准确性校验': CheckCircle2,
  '专业术语适用性检查': BookText,
  '科学逻辑验证': Brain,
  '引用来源建议': Link2,
};

const SECTION_ALIAS_MAP: Record<CanonicalSection, string[]> = {
  '事实准确性校验': ['事实准确性校验', '科学事实准确性校验'],
  '专业术语适用性检查': ['专业术语适用性检查', '术语适用性检查'],
  '科学逻辑验证': ['科学逻辑验证', '科学逻辑校验'],
  '引用来源建议': ['引用来源建议', '参考来源建议', '来源建议'],
};

const SECTION_KEYWORDS: Record<CanonicalSection, string[]> = {
  '事实准确性校验': ['事实', '错误', '不准确', '数值', '概念', '误导', '定义', '不严谨'],
  '专业术语适用性检查': ['术语', '词', '表达', '比喻', '解释', '理解', '难懂', '通俗', '受众'],
  '科学逻辑验证': ['逻辑', '因果', '推理', '机制', '过程', '关系', '链条', '矛盾'],
  '引用来源建议': ['来源', '引用', '文献', '资料', '数据库', 'NASA', '权威', '出处', '机构'],
};

function normalizeSectionName(name?: string): CanonicalSection | null {
  if (!name) return null;
  for (const key of SECTION_ORDER) {
    if (SECTION_ALIAS_MAP[key].some((alias) => name.includes(alias))) {
      return key;
    }
  }
  return null;
}

function parseSuggestionTextToSections(text: string) {
  const raw = (text || '').trim();
  if (!raw) {
    return new Map<CanonicalSection, string>();
  }

  const headingPattern = /(事实准确性校验|科学事实准确性校验|专业术语适用性检查|术语适用性检查|科学逻辑验证|科学逻辑校验|引用来源建议|参考来源建议|来源建议)/g;
  const matches: Array<{ heading: string; index: number }> = [];
  let match: RegExpExecArray | null;

  while ((match = headingPattern.exec(raw)) !== null) {
    matches.push({ heading: match[1], index: match.index });
  }

  const sectionTextMap = new Map<CanonicalSection, string>();
  if (matches.length === 0) {
    return sectionTextMap;
  }

  for (let i = 0; i < matches.length; i += 1) {
    const current = matches[i];
    const next = matches[i + 1];
    const start = current.index + current.heading.length;
    const end = next ? next.index : raw.length;
    const key = normalizeSectionName(current.heading);
    if (!key) continue;

    const body = raw
      .slice(start, end)
      .replace(/^[\s:：\-\d.、)）]+/, '')
      .trim();

    if (body) {
      sectionTextMap.set(key, body);
    }
  }

  return sectionTextMap;
}

function classifyToSection(text: string): CanonicalSection {
  for (const section of SECTION_ORDER) {
    if (SECTION_KEYWORDS[section].some((keyword) => text.includes(keyword))) {
      return section;
    }
  }
  return '事实准确性校验';
}

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

function groupFromArrays(data: ScienceData | null) {
  const grouped: Record<CanonicalSection, { issues: string[]; modifications: string[] }> = {
    '事实准确性校验': { issues: [], modifications: [] },
    '专业术语适用性检查': { issues: [], modifications: [] },
    '科学逻辑验证': { issues: [], modifications: [] },
    '引用来源建议': { issues: [], modifications: [] },
  };

  const issues = Array.isArray(data?.issues) ? data?.issues : [];
  const modifications = Array.isArray(data?.modifications_made) ? data?.modifications_made : [];

  for (const issue of issues) {
    if (!issue) continue;
    grouped[classifyToSection(issue)].issues.push(issue);
  }

  for (const item of modifications) {
    if (!item) continue;
    grouped[classifyToSection(item)].modifications.push(item);
  }

  return grouped;
}

function buildStructuredSections(data: ScienceData | null): NormalizedSection[] {
  const fromText = parseSuggestionTextToSections(data?.suggestions || '');
  const grouped = groupFromArrays(data);
  const output: NormalizedSection[] = SECTION_ORDER.map((section) => ({
    section,
    status: grouped[section].issues.length > 0 ? '需修正' : '通过',
    finding:
      grouped[section].issues[0] ||
      grouped[section].modifications[0] ||
      fromText.get(section) ||
      '未发现明显问题',
    suggestion:
      grouped[section].issues.length > 0
        ? `建议优先修正：${grouped[section].issues.slice(0, 2).join('；')}`
        : grouped[section].modifications[0]
        ? `建议保持当前修订方向，并复查相关段落：${grouped[section].modifications[0]}`
        : '建议保持当前表达，并在终稿阶段做一次复核。',
    suggested_revision: grouped[section].modifications[0] || '无需改写',
    issue_list: [...grouped[section].issues],
    modification_list: [...grouped[section].modifications],
    adopted: grouped[section].modifications.length > 0,
  }));

  if (!Array.isArray(data?.review_sections)) {
    return output;
  }

  for (const item of data.review_sections) {
    const key = normalizeSectionName(item?.section);
    if (!key) continue;
    const index = SECTION_ORDER.findIndex((s) => s === key);
    if (index < 0) continue;

    output[index] = {
      section: key,
      status: item?.status || output[index].status,
      finding: item?.finding || output[index].finding,
      suggestion: item?.suggestion || output[index].suggestion,
      suggested_revision: item?.suggested_revision || output[index].suggested_revision,
      issue_list: Array.from(new Set([...(output[index].issue_list || []), ...(Array.isArray(item?.issue_list) ? item.issue_list : [])])),
      modification_list: Array.from(new Set([...(output[index].modification_list || []), ...(Array.isArray(item?.modification_list) ? item.modification_list : [])])),
      adopted: typeof item?.adopted === 'boolean' ? item.adopted : output[index].adopted,
    };
  }

  return output;
}

function formatScienceContent(content: string) {
  let formatted = content;

  formatted = formatted.replace(
    /^\s*【标题】\s*[：:]\s*(.+)$/m,
    '# $1'
  );

  formatted = formatted.replace(
    /^(?!\s*#)\s*(第[一二三四五六七八九十百千万零两〇0-9]+(?:章|节|部分|幕|回)\s*[：:]?\s*.*)$/gm,
    '## $1'
  );

  // Remove duplicated title line near the top when content contains both markdown title and plain title.
  const lines = formatted.split('\n');
  if (lines.length > 1) {
    const headingMatch = lines[0].match(/^\s*#\s+(.+)\s*$/);
    if (headingMatch) {
      const title = headingMatch[1].trim();
      for (let i = 1; i < Math.min(lines.length, 8); i += 1) {
        const current = lines[i].trim().replace(/^[“”"'【】\[\]]+|[“”"'【】\[\]]+$/g, '');
        if (current === title) {
          lines.splice(i, 1);
          break;
        }
      }
      formatted = lines.join('\n');
    }
  }

  return formatted;
}

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

function flattenText(children: any): string {
  if (typeof children === 'string') return children;
  if (Array.isArray(children)) return children.map((child) => flattenText(child)).join('');
  if (children && typeof children === 'object' && 'props' in children) {
    return flattenText((children as any).props?.children);
  }
  return '';
}

export default function ScienceReview() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state || {}) as any;
  const storyVersionBadge = getModelVersionBadge('/editor/science-review', state);
  const storyData = state?.storyData;
  const formData = state?.formData || {};
  const hasLiteratureResult = !!state?.literatureData;

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [reviewData, setReviewData] = useState<ScienceData | null>(state?.scienceData || null);
  const [adoptionMap, setAdoptionMap] = useState<Record<CanonicalSection, boolean>>({
    '事实准确性校验': false,
    '专业术语适用性检查': false,
    '科学逻辑验证': false,
    '引用来源建议': false,
  });
  const [isGeneratingVersion, setIsGeneratingVersion] = useState(false);
  const [generateTip, setGenerateTip] = useState('');
  const [isEditingVersion, setIsEditingVersion] = useState(false);
  const [editableContent, setEditableContent] = useState('');
  const [useDeepSearch, setUseDeepSearch] = useState<boolean>(state?.useDeepSearch ?? true);
  const [useFactRag, setUseFactRag] = useState<boolean>(state?.useFactRag ?? true);
  const [showGlobalReviewSummary, setShowGlobalReviewSummary] = useState(false);
  const [expandedSectionBlocks, setExpandedSectionBlocks] = useState<Record<string, boolean>>({});
  const [extraGlossaryEntries, setExtraGlossaryEntries] = useState<GlossaryEntry[]>([]);
  const [selectedGlossaryTerm, setSelectedGlossaryTerm] = useState('');
  const revisedContentRef = useRef<HTMLDivElement | null>(null);
  const glossarySectionRef = useRef<HTMLDivElement | null>(null);
  const displayedVersionContent = String(reviewData?.revised_content || '');
  const structuredSections = buildStructuredSections(reviewData);
  const hasGlobalReviewSummary =
    (Array.isArray(reviewData?.issues) && reviewData!.issues!.length > 0) ||
    (Array.isArray(reviewData?.modifications_made) && reviewData!.modifications_made!.length > 0);
  const overallReviewSummary = useMemo(() => {
    if (!reviewData) return '';

    const issues = Array.isArray(reviewData.issues) ? reviewData.issues : [];
    const modifications = Array.isArray(reviewData.modifications_made) ? reviewData.modifications_made : [];
    const passedSections = structuredSections
      .filter((item) => item.status.includes('通过') || item.status.includes('未发现'))
      .map((item) => item.section);
    const problemSections = structuredSections
      .filter((item) => item.status.includes('需修正'))
      .map((item) => item.section);

    if (issues.length === 0) {
      const sectionText = passedSections.length > 0 ? passedSections.join('、') : '四项科学检查';
      if (modifications.length > 0) {
        return `本次科学审查整体通过，${sectionText}未发现明显错误，并已完成${modifications.length}处表达优化，建议保留当前修订方向继续推进。`;
      }
      return `本次科学审查整体通过，${sectionText}均未发现明显问题，当前内容可进入下一步；建议终稿前再做一次快速复核。`;
    }

    const focusText = problemSections.length > 0 ? problemSections.join('、') : '科学事实与逻辑链路';
    return `本次科学审查识别到${issues.length}项待处理问题，重点集中在${focusText}，请优先按建议完成修订后再进行复核。`;
  }, [reviewData, structuredSections]);

  const mergedGlossaryEntries = useMemo(() => {
    const base = [
      ...(Array.isArray(reviewData?.glossary) ? reviewData!.glossary! : []),
      ...(Array.isArray(reviewData?.revised_glossary) ? reviewData!.revised_glossary! : []),
      ...(Array.isArray(storyData?.glossary) ? storyData.glossary : []),
      ...extraGlossaryEntries,
    ];

    const map = new Map<string, GlossaryEntry>();
    base.forEach((item: any) => {
      const term = String(item?.term || '').trim();
      const explanation = String(item?.explanation || '').trim();
      if (!term) return;
      if (!map.has(term)) {
        map.set(term, {
          term,
          explanation: explanation || `${term}是文中涉及的重要科普词条，建议结合上下文进一步理解其含义。`,
        });
      }
    });

    return Array.from(map.values());
  }, [reviewData?.glossary, reviewData?.revised_glossary, storyData?.glossary, extraGlossaryEntries]);
  const glossaryTerms = useMemo(() => {
    const rawHighlightTerms = Array.isArray(reviewData?.highlight_terms) ? reviewData.highlight_terms : [];
    const raw = [
      ...rawHighlightTerms,
      ...(Array.isArray(reviewData?.glossary) ? reviewData!.glossary! : []),
      ...(Array.isArray(reviewData?.revised_glossary) ? reviewData!.revised_glossary! : []),
      ...(Array.isArray(storyData?.glossary) ? storyData.glossary : []),
    ]
      .map((item: any) => String(item?.term || item || '').trim())
      .filter((term: string) => term.length >= 2);

    return Array.from(new Set(raw)).sort((a, b) => b.length - a.length).slice(0, 12);
  }, [reviewData?.highlight_terms, reviewData?.glossary, reviewData?.revised_glossary, storyData?.glossary]);

  const effectiveHighlightTerms = useMemo(() => {
    const contentText = String(reviewData?.revised_content || storyData?.content || '');
    if (!contentText) return [] as string[];
    return glossaryTerms.filter((term) => contentText.includes(term));
  }, [glossaryTerms, reviewData?.revised_content, storyData?.content]);

  const createFallbackExplanation = (term: string, _content: string) => {
    const normalizedTerm = String(term || '').trim();
    if (!normalizedTerm) {
      return '该词条是文中出现的科学概念，建议结合定义、机制与适用条件理解。';
    }

    const presets: Array<{ keywords: string[]; explanation: string }> = [
      { keywords: ['表面张力'], explanation: '表面张力是液体表面分子受力不均产生的收缩效应，使液面趋向于最小面积。' },
      { keywords: ['水膜'], explanation: '水膜是液体在界面上形成的薄层结构，能在一定条件下包裹气体或附着在固体表面。' },
      { keywords: ['水分子', '分子'], explanation: '分子是由原子组成并保持物质化学性质的最小微粒；水分子由两个氢原子和一个氧原子构成。' },
      { keywords: ['重力', '万有引力', '引力'], explanation: '重力是地球对物体产生的吸引作用，本质上属于万有引力在地表附近的表现。' },
      { keywords: ['浮力'], explanation: '浮力是流体对浸入物体产生的向上托举力，其大小与排开流体的重量有关。' },
    ];

    const matched = presets.find((item) => item.keywords.some((k) => normalizedTerm.includes(k) || k.includes(normalizedTerm)));
    if (matched) {
      return matched.explanation;
    }

    return `${normalizedTerm}是文中涉及的科学术语。建议从“定义是什么、由什么机制产生、在什么条件下成立、会带来什么现象”四个维度理解该词条。`;
  };

  const alignedGlossaryEntries = useMemo(() => {
    const explanationMap = new Map<string, string>();
    mergedGlossaryEntries.forEach((item) => {
      const term = String(item?.term || '').trim();
      const explanation = String(item?.explanation || '').trim();
      if (term && explanation && !explanationMap.has(term)) {
        explanationMap.set(term, explanation);
      }
    });

    const contentText = String(reviewData?.revised_content || storyData?.content || '');
    return effectiveHighlightTerms.map((term) => ({
      term,
      explanation: explanationMap.get(term) || createFallbackExplanation(term, contentText),
    }));
  }, [mergedGlossaryEntries, effectiveHighlightTerms, reviewData?.revised_content, storyData?.content]);

  const handleGlossaryTermClick = (term: string) => {
    const normalizedTerm = String(term || '').trim();
    if (!normalizedTerm) return;

    setSelectedGlossaryTerm(normalizedTerm);

    const exists = alignedGlossaryEntries.some((item) => item.term === normalizedTerm);
    if (!exists) {
      const contentText = String(reviewData?.revised_content || storyData?.content || '');
      const explanation = createFallbackExplanation(normalizedTerm, contentText);
      setExtraGlossaryEntries((prev) => {
        if (prev.some((item) => item.term === normalizedTerm)) return prev;
        return [...prev, { term: normalizedTerm, explanation }];
      });
    }

    setTimeout(() => {
      glossarySectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
  };

  useEffect(() => {
    const container = revisedContentRef.current;
    if (!container || effectiveHighlightTerms.length === 0) return;

    const escapedTerms = effectiveHighlightTerms
      .map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      .filter(Boolean);
    if (escapedTerms.length === 0) return;

    const regex = new RegExp(`(${escapedTerms.join('|')})`, 'g');
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    const textNodes: Text[] = [];
    const highlightedTermKeys = new Set<string>();

    while (walker.nextNode()) {
      const node = walker.currentNode as Text;
      const parentTag = node.parentElement?.tagName;
      if (!node.nodeValue || !node.nodeValue.trim()) continue;
      if (parentTag === 'MARK' || parentTag === 'CODE' || parentTag === 'PRE') continue;
      textNodes.push(node);
    }

    textNodes.forEach((node) => {
      const text = node.nodeValue || '';
      regex.lastIndex = 0;
      if (!regex.test(text)) return;

      const fragment = document.createDocumentFragment();
      let lastIndex = 0;
      text.replace(regex, (match, _group, offset) => {
        const key = String(match).toLowerCase();
        if (offset > lastIndex) {
          fragment.appendChild(document.createTextNode(text.slice(lastIndex, offset)));
        }

        if (!highlightedTermKeys.has(key)) {
          const mark = document.createElement('mark');
          mark.textContent = match;
          mark.className = 'rounded px-1 py-0.5 bg-[#DDFCE9] text-[#0B6B3A] border border-[#B8EFCF] cursor-pointer hover:bg-[#C9F6DC] transition-colors';
          mark.title = `点击查看词条：${match}`;
          mark.addEventListener('click', () => handleGlossaryTermClick(match));
          fragment.appendChild(mark);
          highlightedTermKeys.add(key);
        } else {
          fragment.appendChild(document.createTextNode(match));
        }

        lastIndex = offset + match.length;
        return match;
      });

      if (lastIndex < text.length) {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
      }

      node.parentNode?.replaceChild(fragment, node);
    });
  }, [reviewData?.revised_content, effectiveHighlightTerms, mergedGlossaryEntries, selectedGlossaryTerm, alignedGlossaryEntries]);

  const jumpToStep = (step: ReviewStepKey) => {
    const routeMap: Record<ReviewStepKey, string> = {
      literature: '/editor/literature-review',
      science: '/editor/science-review',
      audience: '/editor/reader-feedback',
    };
    navigate(routeMap[step], { state });
  };

  const runReview = async () => {
    if (!hasLiteratureResult || !storyData?.id || !storyData?.content) {
      return;
    }

    setIsLoading(true);
    setError('');
    try {
      const response = await fetchApi('/api/check/verify', {
        method: 'POST',
        body: JSON.stringify({
          story_id: storyData.id,
          title: storyData.title || '未命名故事',
          content: storyData.content,
          target_audience: resolveTargetAudience(formData),
          use_deepsearch: useDeepSearch,
          deepsearch_top_k: 6,
          use_fact_rag: useFactRag,
          evidence_top_k: 6,
          rag_doc_type: 'SCIENCE_FACT',
        }),
      });

      const data = await response.json();
      if (data.code !== 200) {
        throw new Error(data.msg || '科学审核失败');
      }

      const result: ScienceData = data.data || {};
      setReviewData(result);
      setAdoptionMap({
        '事实准确性校验': false,
        '专业术语适用性检查': false,
        '科学逻辑验证': false,
        '引用来源建议': false,
      });
      setGenerateTip('');
      setIsEditingVersion(false);

      navigate(location.pathname, {
        replace: true,
        state: {
          ...(state || {}),
          useDeepSearch,
          useFactRag,
          scienceData: result,
          storyData: {
            ...(storyData || {}),
            glossary: result.glossary || result.revised_glossary || storyData.glossary || [],
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
    if (!displayedVersionContent) {
      setGenerateTip('请先选择采纳建议并生成科学修订版本。');
      return;
    }
    setEditableContent(displayedVersionContent);
    setIsEditingVersion(true);
  };

  const handleCancelEditVersion = () => {
    setIsEditingVersion(false);
    setEditableContent('');
  };

  const handleSaveEditedVersion = () => {
    const nextContent = editableContent.trim();
    if (!nextContent) return;

    const nextReviewData: ScienceData = {
      ...(reviewData || {}),
      revised_content: nextContent,
    };
    setReviewData(nextReviewData);
    setIsEditingVersion(false);

    navigate(location.pathname, {
      replace: true,
      state: {
        ...(state || {}),
        useDeepSearch,
        useFactRag,
        scienceData: nextReviewData,
        storyData: {
          ...(storyData || {}),
          content: nextContent,
          glossary: nextReviewData.glossary || nextReviewData.revised_glossary || storyData.glossary || [],
        },
      },
    });
  };

  const toggleAdoption = (section: CanonicalSection) => {
    setAdoptionMap((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const handleGenerateBySelection = async () => {
    if (!storyData?.id || !storyData?.content || !reviewData) return;

    const selectedSections = structuredSections
      .filter((section) => adoptionMap[section.section])
      .map((section) => ({
        section: section.section,
        suggestion: section.suggestion,
        suggested_revision: section.suggested_revision,
        issue_list: section.issue_list,
        modification_list: section.modification_list,
      }));

    setIsGeneratingVersion(true);
    setError('');
    try {
      const response = await fetchApi('/api/check/apply-selected', {
        method: 'POST',
        body: JSON.stringify({
          story_id: storyData.id,
          title: storyData.title || '未命名故事',
          content: storyData.content,
          target_audience: resolveTargetAudience(formData),
          selected_sections: selectedSections,
        }),
      });

      const data = await response.json();
      if (data.code !== 200) {
        throw new Error(data.msg || '生成科学修订版本失败');
      }

      const nextContent = String(data.data?.revised_content || '').trim() || storyData.content;
      const adoptedSections = Array.isArray(data.data?.adopted_sections) ? data.data.adopted_sections : [];
      const notes = String(data.data?.notes || '').trim();

      const nextReviewData: ScienceData = {
        ...(reviewData || {}),
        revised_content: nextContent,
        review_sections: structuredSections.map((s) => ({
          ...s,
          adopted: adoptedSections.includes(s.section),
        })),
      };

      setReviewData(nextReviewData);
      setGenerateTip(notes || (adoptedSections.length > 0 ? `已按 ${adoptedSections.length} 项采纳建议生成版本。` : '未采纳建议，已保留原文。'));

      navigate(location.pathname, {
        replace: true,
        state: {
          ...(state || {}),
          useDeepSearch,
          useFactRag,
          scienceData: nextReviewData,
          storyData: {
            ...(storyData || {}),
            content: nextContent,
            glossary: nextReviewData.glossary || nextReviewData.revised_glossary || storyData.glossary || [],
          },
        },
      });
    } catch (err: any) {
      setError(err.message || '生成科学修订版本失败');
    } finally {
      setIsGeneratingVersion(false);
    }
  };

  useEffect(() => {
    if (reviewData) return;
    if (!hasLiteratureResult) return;
    if (!storyData?.id || !storyData?.content) return;
    runReview();
  }, []);

  if (!hasLiteratureResult) {
    return (
      <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.06)] border border-gray-100 p-6 min-h-[500px]">
        <ReviewProgress
          currentStep="science"
          literatureDone={false}
          scienceDone={false}
          audienceDone={!!state?.readerData}
          onStepClick={jumpToStep}
        />

        <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[320px] bg-gray-50/50 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-500 mb-4">请先完成文学家审校，再进入科学视角审核。</p>
            <button
              onClick={() => navigate('/editor/literature-review', { state })}
              className="px-5 py-2.5 bg-[#FF9F45] text-white rounded-[12px] font-medium hover:bg-[#FF8C1A] transition-all"
            >
              前往文学家审校
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!storyData?.id || !storyData?.content) {
    return (
      <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.06)] border border-gray-100 p-6 min-h-[500px]">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">3.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">科学性检查</h3>
            <p className="text-sm text-gray-500">需要先完成前序故事生成/润色，再进行科学审查。</p>
          </div>
        </div>

        <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[320px] bg-gray-50/50 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-500 mb-4">暂未检测到可审查正文，请先完成第 1-2 步。</p>
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
        currentStep="science"
        literatureDone={!!state?.literatureData}
        scienceDone={!!reviewData}
        audienceDone={!!state?.readerData}
        onStepClick={jumpToStep}
      />

      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">3.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">科学视角审核</h3>
            <p className="text-sm text-gray-500">展示科学审查 Agent 对科学性、正确性的评价建议和修订版内容。</p>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
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
            onClick={runReview}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-orange-200 text-[#FF9F45] bg-orange-50 hover:bg-orange-100 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
            重新审查
          </button>
        </div>
      </div>

      <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[350px] bg-gray-50/50">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center min-h-[260px] text-gray-400 gap-3">
            <Loader2 className="animate-spin text-[#FF9F45]" size={36} />
            <p>科学审查 Agent 正在核对事实与逻辑，请稍候...</p>
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
                    : 'text-xs px-2.5 py-1 rounded-full bg-red-50 text-red-700 border border-red-200'
                }>
                  {reviewData.passed ? '科学性通过' : '发现问题'}
                </span>
              </div>

              <div className="space-y-4">
                <div className="rounded-lg border border-amber-200 bg-amber-50/80 px-3 py-2">
                  <p className="text-sm leading-7 text-amber-800">
                    <span className="font-semibold">简要总结：</span>
                    {overallReviewSummary}
                  </p>
                </div>

                {structuredSections.map((section) => {
                  const statusPassed = section.status.includes('通过') || section.status.includes('未发现');
                  const SectionIcon = SECTION_ICON_MAP[section.section];
                  const issuesKey = `${section.section}-issues`;
                  const suggestionKey = `${section.section}-suggestion`;
                  const revisionKey = `${section.section}-revision`;
                  const revisionText = (section.suggested_revision || '').trim();
                  const hasActionableRevision = !!revisionText && revisionText !== '无需改写' && revisionText !== '暂无示例改写';
                  const mergedIssues = Array.from(
                    new Set([
                      ...(statusPassed ? [] : [section.finding]),
                      ...(Array.isArray(section.issue_list) ? section.issue_list : []),
                    ].filter(Boolean)),
                  );
                  const mergedRevisions = Array.from(
                    new Set([
                      ...(Array.isArray(section.modification_list) ? section.modification_list : []),
                      ...(hasActionableRevision ? [revisionText] : []),
                    ].filter(Boolean)),
                  );
                  const hasMergedIssues = mergedIssues.length > 0;
                  const hasMergedRevisions = mergedRevisions.length > 0;
                  return (
                    <div key={section.section} className="rounded-xl border border-[#E5E7EB] bg-[#FCFCFD] p-4">
                      <div className="mb-3 flex items-center gap-2 text-[#111827]">
                        <SectionIcon size={16} className="text-[#6366F1]" />
                        <h5 className="text-[24px] font-extrabold leading-none tracking-tight">{section.section}</h5>
                      </div>

                      <div className="space-y-3 border-l-[3px] border-[#6366F1] pl-3">
                        <div className={[
                          'rounded-2xl border px-3 py-2',
                          statusPassed ? 'border-green-200 bg-green-50/70' : 'border-red-200 bg-red-50/70',
                        ].join(' ')}>
                          <p className={['mb-1 text-sm font-semibold', statusPassed ? 'text-green-700' : 'text-red-700'].join(' ')}>
                            <span className="inline-flex items-center gap-1">
                              {statusPassed ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                              {statusPassed ? '通过' : '问题'}
                            </span>
                          </p>
                          <CollapsibleBlock
                            expanded={!!expandedSectionBlocks[issuesKey]}
                            onToggle={() =>
                              setExpandedSectionBlocks((prev) => ({ ...prev, [issuesKey]: !prev[issuesKey] }))
                            }
                            collapsedLines={3}
                            lineHeightPx={28}
                          >
                            {hasMergedIssues ? (
                              <ul className={['list-disc pl-5 text-sm leading-7', statusPassed ? 'text-green-700' : 'text-red-700'].join(' ')}>
                                {mergedIssues.map((issue, idx) => (
                                  <li key={idx}>{issue}</li>
                                ))}
                              </ul>
                            ) : (
                              <p className={['text-sm leading-7', statusPassed ? 'text-green-700' : 'text-red-700'].join(' ')}>
                                未发现明显问题
                              </p>
                            )}
                          </CollapsibleBlock>
                        </div>

                        <div className="rounded-2xl border border-[#C8D8FF] bg-[#F2F7FF] px-3 py-2">
                          <CollapsibleBlock
                            expanded={!!expandedSectionBlocks[suggestionKey]}
                            onToggle={() =>
                              setExpandedSectionBlocks((prev) => ({ ...prev, [suggestionKey]: !prev[suggestionKey] }))
                            }
                            collapsedLines={3}
                            lineHeightPx={28}
                          >
                            <p className="text-sm leading-7 text-[#2753A6]">
                              <span className="font-semibold">建议：</span>
                              {section.suggestion}
                            </p>
                          </CollapsibleBlock>
                        </div>

                        <div className="rounded-2xl border border-[#CDE0FF] bg-[#EEF4FF] px-3 py-2 text-[#3D63A8]">
                          <p className="mb-1 text-sm font-semibold">修改</p>
                          <CollapsibleBlock
                            expanded={!!expandedSectionBlocks[revisionKey]}
                            onToggle={() =>
                              setExpandedSectionBlocks((prev) => ({ ...prev, [revisionKey]: !prev[revisionKey] }))
                            }
                            collapsedLines={3}
                            lineHeightPx={28}
                          >
                            {hasMergedRevisions ? (
                              <ul className="list-disc pl-5 text-sm leading-7">
                                {mergedRevisions.map((item, idx) => (
                                  <li key={idx}>{item}</li>
                                ))}
                              </ul>
                            ) : (
                              <p className="text-sm leading-7">无需改写</p>
                            )}
                          </CollapsibleBlock>
                        </div>

                        {hasMergedRevisions ? (
                          <button
                            type="button"
                            onClick={() => toggleAdoption(section.section)}
                            className={[
                              'inline-flex w-fit items-center gap-1 rounded-full px-2.5 py-1 text-sm font-semibold transition-colors',
                              adoptionMap[section.section]
                                ? 'bg-emerald-50 text-emerald-600 border border-emerald-200 hover:bg-emerald-100'
                                : 'bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200',
                            ].join(' ')}
                          >
                            <BadgeInfo size={14} />
                            {adoptionMap[section.section] ? '已采纳（点击取消）' : '待采纳（点击采纳）'}
                          </button>
                        ) : null}
                      </div>
                    </div>
                  );
                })}

                {hasGlobalReviewSummary ? (
                  <div className="rounded-lg border border-gray-200 bg-gray-50/70 p-3">
                    <button
                      type="button"
                      onClick={() => setShowGlobalReviewSummary((v) => !v)}
                      className="flex w-full items-center justify-between text-left"
                    >
                      <span className="text-sm font-semibold text-gray-700">全局问题/全局修改（可展开查看）</span>
                      {showGlobalReviewSummary ? (
                        <ChevronDown size={16} className="text-gray-500" />
                      ) : (
                        <ChevronRight size={16} className="text-gray-500" />
                      )}
                    </button>

                    {showGlobalReviewSummary ? (
                      <div className="mt-3 space-y-3">
                        {Array.isArray(reviewData.issues) && reviewData.issues.length > 0 ? (
                          <div className="rounded-md border border-red-200 bg-red-50 p-3">
                            <p className="mb-2 text-sm font-semibold text-red-700">识别到的问题</p>
                            <ul className="list-disc pl-5 text-sm text-red-700 space-y-1">
                              {reviewData.issues.map((issue, index) => (
                                <li key={index}>{issue}</li>
                              ))}
                            </ul>
                          </div>
                        ) : null}

                        {Array.isArray(reviewData.modifications_made) && reviewData.modifications_made.length > 0 ? (
                          <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3">
                            <p className="mb-2 text-sm font-semibold text-emerald-700">已进行的修改</p>
                            <ul className="list-disc pl-5 text-sm text-emerald-700 space-y-1">
                              {reviewData.modifications_made.map((item, index) => (
                                <li key={index}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h4 className="text-base font-bold text-gray-900">科学修订后版本</h4>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleGenerateBySelection}
                    disabled={isGeneratingVersion}
                    className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 disabled:opacity-60"
                  >
                    {isGeneratingVersion ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                    按采纳项生成版本
                  </button>
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
                    className="min-h-[360px] w-full rounded-lg border border-gray-300 px-3 py-2 text-sm leading-7 text-gray-700 outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
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
                <>
                  {generateTip ? (
                    <div className="mb-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
                      {generateTip}
                    </div>
                  ) : null}
                  {displayedVersionContent ? (
                    <div ref={revisedContentRef} className="prose prose-orange max-w-none text-[15px] leading-relaxed text-gray-700">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          h1: ({ children }) => (
                            <h1 className="mt-2 mb-6 text-3xl font-extrabold text-gray-900 tracking-tight">{children}</h1>
                          ),
                          h2: ({ children }) => (
                            <h2 className="mt-8 mb-3 text-2xl font-extrabold text-gray-900 border-l-4 border-orange-400 pl-3">
                              {children}
                            </h2>
                          ),
                          h3: ({ children }) => <h3 className="mt-6 mb-3 text-lg font-bold text-gray-900">{children}</h3>,
                          p: ({ children }) => {
                            const text = flattenText(children).trim();
                            const chapterPattern = /^第[一二三四五六七八九十百千万零两〇0-9]+(?:章|节|部分|幕|回)\s*[：:]?\s*.+$/;

                            if (chapterPattern.test(text)) {
                              return <h2 className="mt-8 mb-3 text-2xl font-extrabold text-gray-900 border-l-4 border-orange-400 pl-3">{text}</h2>;
                            }

                            return <p className="mb-2 leading-8">{children}</p>;
                          },
                        }}
                      >
                        {formatScienceContent(displayedVersionContent)}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div className="rounded-md border border-dashed border-gray-300 bg-gray-50 px-3 py-4 text-sm text-gray-600">
                      请先在上方逐条选择“是否采纳”，然后点击“按采纳项生成版本”。
                    </div>
                  )}
                </>
              )}

              <div ref={glossarySectionRef} className="mt-6 rounded-2xl border-2 border-[#FFB067] bg-gradient-to-br from-[#FFF5E8] via-[#FFFDF8] to-[#EEF8FF] p-4 shadow-[0_10px_24px_rgba(255,159,69,0.12)]">
                <div className="mb-4 flex items-center gap-3">
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-[#FF9F45] text-white shadow-[0_6px_14px_rgba(255,159,69,0.35)]">
                    <BadgeInfo size={16} />
                  </span>
                  <div>
                    <h5 className="text-base font-black tracking-tight text-[#8A3E00]">文末科普词条</h5>
                    <p className="text-xs text-[#A65A1A]">点击正文高亮词可快速定位到这里查看解释</p>
                  </div>
                </div>
                {alignedGlossaryEntries.length > 0 ? (
                  <div className="space-y-3">
                    {alignedGlossaryEntries.map((item, index) => (
                      <div
                        key={`${item.term}-${index}`}
                        className={[
                          'rounded-xl border px-4 py-3 transition-colors shadow-[0_4px_12px_rgba(255,176,103,0.12)]',
                          selectedGlossaryTerm === item.term
                            ? 'border-[#67D38F] bg-[#ECFBF2]'
                            : 'border-[#FFD3A6] bg-white',
                        ].join(' ')}
                      >
                        <p className="mb-1 inline-flex items-center rounded-full border border-[#FFC68E] bg-[#FFF3E3] px-2.5 py-0.5 text-sm font-extrabold text-[#8A3E00]">
                          {item.term || `词条 ${index + 1}`}
                        </p>
                        <p className="text-sm text-gray-800 leading-7">{item.explanation || '暂无解释'}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="rounded-lg border border-dashed border-[#FFC68E] bg-white/80 px-3 py-2 text-sm text-[#A65A1A]">
                    本次审查未返回 glossary 词条。
                  </p>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center min-h-[260px] text-gray-400">等待科学审查结果...</div>
        )}
      </div>
    </div>
  );
}
