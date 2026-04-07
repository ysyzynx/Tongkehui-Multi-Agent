import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Loader2, RefreshCw, MessageCircleHeart, BadgeInfo, Pencil, Save, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ReviewProgress, { type ReviewStepKey } from '../../components/ReviewProgress';
import { fetchApi } from '../../lib/api';
import { getModelVersionBadge } from '../../lib/workHistory';

type ReaderData = {
  reader_feedback?: string;
  audience_feedback?: string;
  feedback?: string;
  comment?: string;
  content?: string;
  error?: string;
  revised_content?: string;
  optimization_notes?: string;
  version?: string;
};

type GlossaryItem = {
  term?: string;
  explanation?: string;
};

type GlossaryEntry = {
  term: string;
  explanation: string;
  sourceUrl?: string;
  sourceLabel?: string;
};

type ScienceData = {
  highlight_terms?: string[];
  glossary?: GlossaryItem[];
  revised_glossary?: GlossaryItem[];
};

const SCIENCE_EXPLANATION_PRESETS: Array<{ keywords: string[]; explanation: string }> = [
  {
    keywords: ['温度', '气温', '热度', '摄氏度', '华氏度', '开尔文'],
    explanation: '温度是描述物体冷热程度的物理量，本质上反映了微观粒子热运动的平均强弱。温度越高，粒子平均运动越剧烈；常见单位有摄氏度（°C）、华氏度（°F）和开尔文（K）。',
  },
  {
    keywords: ['天气', '气候', '气象'],
    explanation: '天气是某地在短时间内的大气状态，通常由气温、湿度、风、降水和气压等要素共同决定；气候则是这些天气现象在更长时间尺度上的统计特征。',
  },
  {
    keywords: ['光线', '光', '反射', '折射'],
    explanation: '光是一种电磁波。光线传播到不同介质或物体表面时会发生反射、折射或吸收，这些过程共同决定了我们看到的亮度、颜色和成像效果。',
  },
  {
    keywords: ['声音', '声波', '振动', '回声'],
    explanation: '声音本质上是由物体振动产生的机械波，需要通过空气、水或固体等介质传播；音调、响度和音色分别与频率、振幅和波形结构有关。',
  },
  {
    keywords: ['重力', '引力', '万有引力'],
    explanation: '引力是物体之间普遍存在的相互吸引作用。质量越大、距离越近，引力越强，这也是天体运行和物体下落等现象的重要原因。',
  },
  {
    keywords: ['摩擦力', '摩擦'],
    explanation: '摩擦力是在接触面之间阻碍相对运动或相对运动趋势的力。它与接触材料、表面粗糙程度和压力大小等因素相关。',
  },
  {
    keywords: ['电流', '电压', '电阻', '电路'],
    explanation: '电流是电荷的定向移动，电压可理解为推动电荷移动的“势能差”，电阻反映导体对电流的阻碍程度，三者共同决定电路工作状态。',
  },
  {
    keywords: ['细胞', 'DNA', '基因', '遗传'],
    explanation: '细胞是生命活动的基本结构与功能单位，DNA携带遗传信息，基因是DNA上具有特定功能的片段，决定并调控生物体的多种性状。',
  },
  {
    keywords: ['光合作用'],
    explanation: '光合作用是绿色植物等利用光能，将二氧化碳和水合成为有机物并释放氧气的过程，是地球生态系统能量输入的重要来源。',
  },
  {
    keywords: ['蒸发', '凝结', '降水', '水循环'],
    explanation: '水循环包括蒸发、凝结、降水和径流等环节，驱动力主要来自太阳辐射和重力，是地球水资源再分配与更新的关键机制。',
  },
];

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

function formatReaderFeedback(content: string) {
  const normalized = (content || '').replace(/\r\n/g, '\n').trim();
  const firstSectionIndex = normalized.search(/[1-5][\.、]\s*(易读性|科普性|有趣性|实用性|传播性)\s*[：:]/);

  if (firstSectionIndex < 0) {
    return normalized;
  }

  const intro = normalized.slice(0, firstSectionIndex).trim();
  const sectionsText = normalized.slice(firstSectionIndex);

  const pattern = /([1-5])[\.、]\s*(易读性|科普性|有趣性|实用性|传播性)\s*[：:]\s*([\s\S]*?)(?=(?:\s*[1-5][\.、]\s*(?:易读性|科普性|有趣性|实用性|传播性)\s*[：:])|$)/g;
  const blocks: string[] = [];
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(sectionsText)) !== null) {
    const index = match[1];
    const label = match[2];
    const body = (match[3] || '').trim();
    blocks.push(`### ${index}. ${label}\n${body}`);
  }

  if (blocks.length === 0) {
    return normalized;
  }

  return intro ? `${intro}\n\n${blocks.join('\n\n')}` : blocks.join('\n\n');
}

function resolveFeedbackText(data: ReaderData | null) {
  if (!data) return '';
  return data.reader_feedback || data.audience_feedback || data.feedback || data.comment || data.content || data.error || '';
}

function flattenText(children: any): string {
  if (typeof children === 'string') return children;
  if (Array.isArray(children)) return children.map((child) => flattenText(child)).join('');
  if (children && typeof children === 'object' && 'props' in children) {
    return flattenText((children as any).props?.children);
  }
  return '';
}

function normalizeTermKey(term: string) {
  return String(term || '')
    .trim()
    .toLowerCase()
    .replace(/[\s\-_/（）()【】\[\]，。,.;；：:!?！？"“”'‘’]/g, '');
}

function extractContextSentence(content: string, term: string) {
  const text = String(content || '').replace(/\s+/g, ' ').trim();
  if (!text) return '';
  const index = text.indexOf(term);
  if (index < 0) return '';

  const left = Math.max(
    text.lastIndexOf('。', index),
    text.lastIndexOf('！', index),
    text.lastIndexOf('？', index),
    text.lastIndexOf('.', index),
    text.lastIndexOf('!', index),
    text.lastIndexOf('?', index)
  );
  const nearestRight = [
    text.indexOf('。', index),
    text.indexOf('！', index),
    text.indexOf('？', index),
    text.indexOf('.', index),
    text.indexOf('!', index),
    text.indexOf('?', index),
  ].filter((x) => x >= 0);

  const right = nearestRight.length > 0 ? Math.min(...nearestRight) : text.length;
  return text.slice(left < 0 ? 0 : left + 1, right < 0 ? text.length : right + 1).trim();
}

function createScientificFallbackExplanation(term: string, content: string) {
  const matchedPreset = SCIENCE_EXPLANATION_PRESETS.find((item) => item.keywords.some((keyword) => term.includes(keyword) || keyword.includes(term)));
  const contextSentence = extractContextSentence(content, term);

  if (matchedPreset) {
    return contextSentence
      ? `${matchedPreset.explanation} 在本文中，它对应的语境是：“${contextSentence}”。`
      : matchedPreset.explanation;
  }

  if (contextSentence) {
    return `${term}是文中涉及的科学概念。结合语境“${contextSentence}”，可将其理解为用于解释相关自然现象或机制的关键术语，阅读时可重点关注其定义、形成条件和作用过程。`;
  }

  return `${term}是文中涉及的科学概念。建议从“定义是什么、由什么机制产生、在什么条件下成立、会带来什么现象”四个维度理解该词条。`;
}

function isGenericHeuristicExplanation(text: string) {
  const normalized = String(text || '').trim();
  if (!normalized) return true;
  return [
    '文中重点科普词条',
    '文中涉及的重要科普词条',
    '建议结合上下文进一步理解',
    '建议在阅读时重点关注其定义',
    '反映了该段核心科学概念',
  ].some((flag) => normalized.includes(flag));
}

function pickWikipediaSummary(content: string, term: string) {
  const text = String(content || '').replace(/\r\n/g, '\n');
  const lines = text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length >= 16);

  const byTerm = lines.find((line) => line.includes(term) && !line.startsWith('=='));
  if (byTerm) {
    return byTerm.slice(0, 220);
  }

  const firstParagraph = lines.find((line) => !line.startsWith('=='));
  if (firstParagraph) {
    return firstParagraph.slice(0, 220);
  }

  return '';
}

function formatRefinedContent(content: string) {
  let formatted = content;

  formatted = formatted.replace(
    /^\s*【标题】\s*[：:]\s*(.+)$/m,
    '# $1'
  );

  formatted = formatted.replace(
    /^(?!\s*#)\s*(第[一二三四五六七八九十百千万零两〇0-9]+(?:章|节|部分|幕|回)\s*[：:]?\s*.*)$/gm,
    '## $1'
  );

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

export default function ReaderFeedback() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state || {}) as any;
  const storyVersionBadge = getModelVersionBadge('/editor/reader-feedback', state);
  const storyData = state?.storyData;
  const scienceData = (state?.scienceData || {}) as ScienceData;
  const formData = state?.formData || {};
  const hasScienceResult = !!state?.scienceData;

  const [isLoading, setIsLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('');
  const [error, setError] = useState('');
  const [readerData, setReaderData] = useState<ReaderData | null>(state?.readerData || null);
  const [isEditingVersion, setIsEditingVersion] = useState(false);
  const [editableContent, setEditableContent] = useState('');
  const [extraGlossaryEntries, setExtraGlossaryEntries] = useState<GlossaryEntry[]>([]);
  const [selectedGlossaryTerm, setSelectedGlossaryTerm] = useState('');
  const [, setWikiResolvingTerm] = useState('');
  const revisedContentRef = useRef<HTMLDivElement | null>(null);
  const glossarySectionRef = useRef<HTMLDivElement | null>(null);
  const wikiCacheRef = useRef<Map<string, GlossaryEntry>>(new Map());
  const activeContentText = String(readerData?.revised_content || storyData?.content || '');

  const findBestGlossaryEntry = (term: string, entries: GlossaryEntry[]) => {
    const normalizedTerm = normalizeTermKey(term);
    if (!normalizedTerm) return null;

    let best: GlossaryEntry | null = null;
    let bestScore = -1;
    for (const item of entries) {
      const candidateKey = normalizeTermKey(item.term);
      if (!candidateKey) continue;

      let score = 0;
      if (candidateKey === normalizedTerm) score = 100;
      else if (candidateKey.includes(normalizedTerm) || normalizedTerm.includes(candidateKey)) score = 80;
      else {
        const overlapChars = Array.from(new Set(normalizedTerm.split(''))).filter((ch) => candidateKey.includes(ch)).length;
        score = overlapChars;
      }

      if (score > bestScore && item.explanation?.trim()) {
        best = item;
        bestScore = score;
      }
    }
    return bestScore >= 2 ? best : null;
  };

  const mergedGlossaryEntries = useMemo(() => {
    const base = [
      ...(Array.isArray(scienceData?.glossary) ? scienceData.glossary : []),
      ...(Array.isArray(scienceData?.revised_glossary) ? scienceData.revised_glossary : []),
      ...(Array.isArray(storyData?.glossary) ? storyData.glossary : []),
      ...extraGlossaryEntries,
    ];

    const map = new Map<string, GlossaryEntry>();
    base.forEach((item: any) => {
      const term = String(item?.term || '').trim();
      const explanation = String(item?.explanation || '').trim();
      if (!term) return;
      const scientificExplanation = explanation || createScientificFallbackExplanation(term, activeContentText);
      const existing = map.get(term);

      if (!existing) {
        map.set(term, { term, explanation: scientificExplanation, sourceUrl: item?.sourceUrl, sourceLabel: item?.sourceLabel });
      } else if (explanation) {
        map.set(term, {
          ...existing,
          explanation,
          sourceUrl: item?.sourceUrl || existing.sourceUrl,
          sourceLabel: item?.sourceLabel || existing.sourceLabel,
        });
      }
    });

    return Array.from(map.values());
  }, [scienceData?.glossary, scienceData?.revised_glossary, storyData?.glossary, extraGlossaryEntries, activeContentText]);

  const glossaryTerms = useMemo(() => {
    const rawHighlightTerms = Array.isArray(scienceData?.highlight_terms) ? scienceData.highlight_terms : [];
    const raw = [
      ...rawHighlightTerms,
      ...(Array.isArray(scienceData?.glossary) ? scienceData.glossary : []),
      ...(Array.isArray(scienceData?.revised_glossary) ? scienceData.revised_glossary : []),
      ...(Array.isArray(storyData?.glossary) ? storyData.glossary : []),
    ]
      .map((item: any) => String(item?.term || item || '').trim())
      .filter((term: string) => term.length >= 2);

    return Array.from(new Set(raw)).sort((a, b) => b.length - a.length);
  }, [scienceData?.highlight_terms, scienceData?.glossary, scienceData?.revised_glossary, storyData?.glossary]);

  const effectiveHighlightTerms = useMemo(() => {
    if (!activeContentText) return [] as string[];
    return glossaryTerms.filter((term) => activeContentText.includes(term));
  }, [glossaryTerms, activeContentText]);

  const alignedGlossaryEntries = useMemo(() => {
    const map = new Map<string, GlossaryEntry>();
    mergedGlossaryEntries.forEach((item) => {
      const term = String(item?.term || '').trim();
      const explanation = String(item?.explanation || '').trim();
      if (term && explanation && !map.has(term)) {
        map.set(term, item);
      }
    });

    return effectiveHighlightTerms.map((term) => {
      const existing = map.get(term);
      if (existing?.explanation?.trim()) {
        return existing;
      }
      return {
        term,
        explanation: createScientificFallbackExplanation(term, activeContentText),
      } as GlossaryEntry;
    });
  }, [mergedGlossaryEntries, effectiveHighlightTerms, activeContentText]);

  const handleGlossaryTermClick = (term: string) => {
    const normalizedTerm = String(term || '').trim();
    if (!normalizedTerm) return;

    const exactEntry = alignedGlossaryEntries.find((item) => item.term === normalizedTerm);
    const bestMatchedEntry = exactEntry || findBestGlossaryEntry(normalizedTerm, alignedGlossaryEntries);

    if (bestMatchedEntry?.term) {
      setSelectedGlossaryTerm(bestMatchedEntry.term);

      if (isGenericHeuristicExplanation(bestMatchedEntry.explanation)) {
        const upgradedExplanation = createScientificFallbackExplanation(bestMatchedEntry.term, activeContentText);
        setExtraGlossaryEntries((prev) => {
          const withoutTarget = prev.filter((item) => item.term !== bestMatchedEntry.term);
          return [
            ...withoutTarget,
            {
              ...bestMatchedEntry,
              explanation: upgradedExplanation,
            },
          ];
        });
      }
    } else {
      setSelectedGlossaryTerm(normalizedTerm);
      const explanation = createScientificFallbackExplanation(normalizedTerm, activeContentText);
      setExtraGlossaryEntries((prev) => {
        if (prev.some((item) => item.term === normalizedTerm)) return prev;
        return [...prev, { term: normalizedTerm, explanation }];
      });
    }

    const resolveWikiExplanation = async (sourceTerm: string, displayTerm: string) => {
      const cacheKey = normalizeTermKey(sourceTerm);
      const cached = wikiCacheRef.current.get(cacheKey);
      if (cached) {
        setExtraGlossaryEntries((prev) => {
          const withoutTarget = prev.filter((item) => item.term !== displayTerm);
          return [...withoutTarget, { ...cached, term: displayTerm }];
        });
        return;
      }

      try {
        setWikiResolvingTerm(displayTerm);

        const searchResp = await fetchApi('/api/fact/wikipedia/search', {
          method: 'POST',
          body: JSON.stringify({
            query: sourceTerm,
            limit: 1,
            language: 'zh',
          }),
        });
        const searchData = await searchResp.json();
        const first = searchData?.data?.results?.[0];
        if (!first) return;

        const pageResp = await fetchApi('/api/fact/wikipedia/page', {
          method: 'POST',
          body: JSON.stringify({
            pageid: first.pageid,
            title: first.title,
            language: 'zh',
          }),
        });
        const pageData = await pageResp.json();
        const page = pageData?.data;
        if (!page) return;

        const wikiSummary = pickWikipediaSummary(String(page.content || ''), sourceTerm || displayTerm);
        if (!wikiSummary) return;

        const entry: GlossaryEntry = {
          term: displayTerm,
          explanation: `${wikiSummary}`,
          sourceUrl: String(page.url || first.url || '').trim() || undefined,
          sourceLabel: '维基百科',
        };
        wikiCacheRef.current.set(cacheKey, entry);
        setExtraGlossaryEntries((prev) => {
          const withoutTarget = prev.filter((item) => item.term !== displayTerm);
          return [...withoutTarget, entry];
        });
      } catch {
        // 保留当前解释，不阻塞阅读流程
      } finally {
        setWikiResolvingTerm((current) => (current === displayTerm ? '' : current));
      }
    };

    void resolveWikiExplanation(normalizedTerm, bestMatchedEntry?.term || normalizedTerm);

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
  }, [readerData?.revised_content, effectiveHighlightTerms, mergedGlossaryEntries, selectedGlossaryTerm, storyData?.content, activeContentText, alignedGlossaryEntries]);

  const jumpToStep = (step: ReviewStepKey) => {
    const routeMap: Record<ReviewStepKey, string> = {
      literature: '/editor/literature-review',
      science: '/editor/science-review',
      audience: '/editor/reader-feedback',
    };
    navigate(routeMap[step], { state });
  };

  const runEvaluate = async () => {
    if (!hasScienceResult || !storyData?.id || !storyData?.content) {
      return;
    }

    setIsLoading(true);
    setLoadingText('虚拟读者正在认真试读并反馈，请稍候...');
    setError('');
    try {
      const response = await fetchApi('/api/reader/evaluate', {
        method: 'POST',
        body: JSON.stringify({
          story_id: storyData.id,
          title: storyData.title || '未命名故事',
          content: storyData.content,
          target_audience: resolveTargetAudience(formData),
          age_group: resolveAgeGroup(formData),
        }),
      });

      const data = await response.json();
      if (data.code !== 200) {
        throw new Error(data.msg || '读者反馈生成失败');
      }

      const result: ReaderData = data.data || {};
      const feedbackText = resolveFeedbackText(result);

      setLoadingText('正在根据观众反馈微调 4.0 版本...');
      const refineResponse = await fetchApi('/api/reader/refine', {
        method: 'POST',
        body: JSON.stringify({
          story_id: storyData.id,
          title: storyData.title || '未命名故事',
          content: storyData.content,
          feedback: feedbackText,
          target_audience: resolveTargetAudience(formData),
          age_group: resolveAgeGroup(formData),
        }),
      });
      const refineData = await refineResponse.json();
      if (refineData.code !== 200) {
        throw new Error(refineData.msg || '观众反馈微调失败');
      }

      const refined: ReaderData = {
        ...result,
        ...(refineData.data || {}),
      };

      setReaderData(refined);

      navigate(location.pathname, {
        replace: true,
        state: {
          ...(state || {}),
          readerData: refined,
          storyData: {
            ...(storyData || {}),
            content: refined.revised_content || storyData.content,
          },
        },
      });
    } catch (err: any) {
      setError(err.message || '请求失败，请确认后端服务状态');
    } finally {
      setIsLoading(false);
      setLoadingText('');
    }
  };

  const handleStartEditVersion = () => {
    setEditableContent(activeContentText);
    setIsEditingVersion(true);
  };

  const handleCancelEditVersion = () => {
    setIsEditingVersion(false);
    setEditableContent('');
  };

  const handleSaveEditedVersion = () => {
    const nextContent = editableContent.trim();
    if (!nextContent) return;

    const nextReaderData: ReaderData = {
      ...(readerData || {}),
      revised_content: nextContent,
    };

    setReaderData(nextReaderData);
    setIsEditingVersion(false);

    navigate(location.pathname, {
      replace: true,
      state: {
        ...(state || {}),
        readerData: nextReaderData,
        storyData: {
          ...(storyData || {}),
          content: nextContent,
        },
      },
    });
  };

  useEffect(() => {
    if (readerData) return;
    if (!hasScienceResult) return;
    if (!storyData?.id || !storyData?.content) return;
    runEvaluate();
  }, []);

  if (!hasScienceResult) {
    return (
      <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.06)] border border-gray-100 p-6 min-h-[500px]">
        <ReviewProgress
          currentStep="audience"
          literatureDone={!!state?.literatureData}
          scienceDone={false}
          audienceDone={false}
          onStepClick={jumpToStep}
        />

        <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[320px] bg-gray-50/50 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-500 mb-4">请先完成科学视角审核，再查看观众视角反馈。</p>
            <button
              onClick={() => navigate('/editor/science-review', { state })}
              className="px-5 py-2.5 bg-[#FF9F45] text-white rounded-[12px] font-medium hover:bg-[#FF8C1A] transition-all"
            >
              前往科学视角审核
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
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">4.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">观众反馈</h3>
            <p className="text-sm text-gray-500">需要先完成前序步骤，再生成观众反馈。</p>
          </div>
        </div>

        <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[320px] bg-gray-50/50 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-500 mb-4">暂未检测到可评估正文，请先完成第 1-3 步。</p>
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
        currentStep="audience"
        literatureDone={!!state?.literatureData}
        scienceDone={!!state?.scienceData}
        audienceDone={!!readerData}
        onStepClick={jumpToStep}
      />

      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">4.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">观众反馈</h3>
            <p className="text-sm text-gray-500">先生成观众反馈，再基于科学审查版本做轻量微调，产出 4.0 版本。</p>
          </div>
        </div>

        <button
          onClick={runEvaluate}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-orange-200 text-[#FF9F45] bg-orange-50 hover:bg-orange-100 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
            重新生成 4.0
        </button>
      </div>

      <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[350px] bg-gray-50/50">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center min-h-[260px] text-gray-400 gap-3">
            <Loader2 className="animate-spin text-[#FF9F45]" size={36} />
            <p>{loadingText || '处理中，请稍候...'}</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center min-h-[260px] text-red-400 gap-3">
            <p>{error}</p>
            <button
              onClick={runEvaluate}
              className="px-4 py-2 mt-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition"
            >
              重试
            </button>
          </div>
        ) : readerData ? (
          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h4 className="text-base font-bold text-gray-900 mb-3 inline-flex items-center gap-2">
                <MessageCircleHeart size={16} className="text-[#FF9F45]" />
                观众心声（感受与反馈）
              </h4>
              <div className="prose prose-orange max-w-none text-[15px] leading-relaxed text-gray-700">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h3: ({ children }) => (
                      <h3 className="mt-6 mb-3 text-lg font-bold text-gray-900 border-l-4 border-orange-400 pl-3">
                        {children}
                      </h3>
                    ),
                    p: ({ children }) => <p className="mb-2 leading-8">{children}</p>,
                  }}
                >
                  {formatReaderFeedback(resolveFeedbackText(readerData) || '暂无反馈内容')}
                </ReactMarkdown>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h4 className="text-base font-bold text-gray-900">观众反馈微调后版本</h4>
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
              {readerData.optimization_notes ? (
                <p className="mb-3 text-sm text-gray-600">微调说明：{readerData.optimization_notes}</p>
              ) : null}
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
                    {formatRefinedContent(String(activeContentText || '暂无微调后正文'))}
                  </ReactMarkdown>
                </div>
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
          <div className="flex items-center justify-center min-h-[260px] text-gray-400">等待读者反馈结果...</div>
        )}
      </div>
    </div>
  );
}
