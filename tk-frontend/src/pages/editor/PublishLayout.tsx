import { useCallback, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  FileDown,
  Image as ImageIcon,
  Loader2,
  Newspaper,
  Sparkles,
  Download,
  ExternalLink,
  AlertCircle,
  Printer,
} from 'lucide-react';
import { fetchApi, joinApiUrl } from '../../lib/api';
import { getModelVersionBadge } from '../../lib/workHistory';

type Scene = {
  scene_id: number;
  text_chunk?: string;
  summary?: string;
  image_prompt?: string;
  image_url?: string;
};

type StoryData = {
  id?: number;
  title?: string;
  content?: string;
  llm_provider?: string;
  llm_provider_label?: string;
  glossary?: Array<{ term?: string; explanation?: string }>;
};

type ScienceData = {
  revised_content?: string;
  glossary?: Array<{ term?: string; explanation?: string }>;
  revised_glossary?: Array<{ term?: string; explanation?: string }>;
  highlight_terms?: string[];
};

type GlossaryEntry = {
  term: string;
  explanation: string;
};

type ContentBlock = {
  type: 'heading' | 'paragraph';
  text: string;
};

type PublisherResponse = {
  code: number;
  msg?: string;
  data?: {
    download_url?: string;
    filename?: string;
  };
};

function isHeadingLine(line: string) {
  const text = (line || '').trim();
  if (!text) return false;
  if (text.startsWith('#')) return true;
  return /^第[一二三四五六七八九十百千万零两〇0-9]+(?:章|节|部分|幕|回)/.test(text);
}

function isTitleMetaLine(line: string) {
  const text = (line || '').trim();
  return /^[\[【(（]?\s*标题\s*[\]】)）]?\s*[：:].*/.test(text);
}

function formatParagraphText(text: string): string {
  let result = text || '';

  // 1. 清理多余的空格和换行
  result = result.replace(/\s+/g, ' ');

  // 2. 标准化标点符号（英文标点转中文标点）
  result = result.replace(/,/g, '，');
  result = result.replace(/\./g, '。');
  result = result.replace(/!/g, '！');
  result = result.replace(/\?/g, '？');
  result = result.replace(/:/g, '：');
  result = result.replace(/;/g, '；');

  // 3. 标点符号后加空格（中文标点后不需要空格）
  // 确保标点后面没有多余空格
  result = result.replace(/([。！？，；：])\s+/g, '$1');

  // 4. 中文与英文/数字之间加空格
  result = result.replace(/([\u4e00-\u9fff])([a-zA-Z0-9])/g, '$1 $2');
  result = result.replace(/([a-zA-Z0-9])([\u4e00-\u9fff])/g, '$1 $2');

  // 5. 清理开头和结尾
  result = result.trim();

  // 6. 确保段落以正确的标点结尾
  if (result && !/[。！？!?]$/.test(result)) {
    // 如果不是以标点结尾，且内容较长，加上句号
    if (result.length > 10) {
      result += '。';
    }
  }

  return result;
}

function normalizeText(text: string) {
  return (text || '')
    .replace(/^#+\s*/, '')
    .replace(/[\s\p{P}\p{S}]/gu, '')
    .toLowerCase();
}

function splitChunkParagraphs(chunk: string) {
  const paragraphs: string[] = [];
  let buffer: string[] = [];

  const flush = () => {
    if (!buffer.length) return;
    const paragraph = buffer.join('').trim();
    if (paragraph) paragraphs.push(paragraph);
    buffer = [];
  };

  for (const raw of (chunk || '').split('\n')) {
    const line = raw.trim();
    if (!line) {
      flush();
      continue;
    }
    if (isTitleMetaLine(line) || isHeadingLine(line)) {
      flush();
      continue;
    }
    buffer.push(line);
  }

  flush();
  return paragraphs;
}

function matchScore(anchorNorm: string, paragraphNorm: string) {
  if (!anchorNorm || !paragraphNorm) return 0;
  if (paragraphNorm === anchorNorm) return 100;
  if (paragraphNorm.includes(anchorNorm)) return 90;
  if (anchorNorm.includes(paragraphNorm)) return 80;

  const probeLen = Math.min(24, anchorNorm.length);
  const probe = anchorNorm.slice(0, probeLen);
  if (probe && paragraphNorm.includes(probe)) return 70;

  const tailProbeLen = Math.min(24, anchorNorm.length);
  const tailProbe = anchorNorm.slice(anchorNorm.length - tailProbeLen);
  if (tailProbe && paragraphNorm.includes(tailProbe)) return 60;

  return 0;
}

function earlyMatchScore(firstAnchor: string, lastAnchor: string, paragraphNorm: string) {
  const first = matchScore(firstAnchor, paragraphNorm);
  const last = matchScore(lastAnchor, paragraphNorm);
  return Math.max(first, Math.floor(last * 0.7));
}

function splitBlocks(content: string): ContentBlock[] {
  const blocks: ContentBlock[] = [];
  const lines = (content || '').split('\n');
  let paragraphBuffer: string[] = [];

  const flushParagraph = () => {
    if (!paragraphBuffer.length) return;
    // 合并段落并格式化
    const rawText = paragraphBuffer.join('');
    const formattedText = formatParagraphText(rawText);
    blocks.push({ type: 'paragraph', text: formattedText });
    paragraphBuffer = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      flushParagraph();
      continue;
    }

    if (isTitleMetaLine(line)) {
      continue;
    }

    if (isHeadingLine(line)) {
      flushParagraph();
      const headingText = line.replace(/^#+\s*/, '');
      blocks.push({ type: 'heading', text: headingText });
      continue;
    }

    paragraphBuffer.push(line);
  }

  flushParagraph();
  return blocks;
}

function isTrailingResourceLine(line: string): boolean {
  const text = String(line || '').trim();
  if (!text) return false;
  const pattern = /(?:小科学家加油站|USGS\s*Kids|NSTA|capillary\s*action|https?:\/\/|www\.|网站|学习中心|搜索|下载|资源|延伸阅读|一起做的|记录表|实验包|\u2705|\uD83D\uDD17)/i;
  return pattern.test(text);
}

function stripTrailingResourceRecommendations(content: string): string {
  const lines = String(content || '').split('\n');

  while (lines.length > 0 && !String(lines[lines.length - 1] || '').trim()) {
    lines.pop();
  }

  while (lines.length > 0 && isTrailingResourceLine(lines[lines.length - 1])) {
    lines.pop();
    while (lines.length > 0 && !String(lines[lines.length - 1] || '').trim()) {
      lines.pop();
    }
  }

  return lines.join('\n');
}

function matchScenesToParagraphs(blocks: ContentBlock[], scenes: Scene[]) {
  const matched = new Map<number, Scene[]>();
  const list = [...(scenes || [])].sort((a, b) => (a.scene_id || 0) - (b.scene_id || 0));

  if (list.length === 0) return matched;

  const paragraphIndexes = blocks
    .map((block, index) => ({ block, index }))
    .filter((item) => item.block.type === 'paragraph')
    .map((item) => item.index);

  if (paragraphIndexes.length === 0) return matched;

  // 方案：均匀分布策略 + 最佳匹配
  // 1. 计算每个图片应该在的大致位置（均匀分布）
  // 2. 在该位置附近寻找最佳匹配

  const totalParagraphs = paragraphIndexes.length;
  const totalScenes = list.length;

  for (let sceneIndex = 0; sceneIndex < list.length; sceneIndex++) {
    const scene = list[sceneIndex];

    const chunkParagraphs = splitChunkParagraphs(scene.text_chunk || '');
    const firstAnchor = normalizeText(chunkParagraphs[0] || '');
    const lastAnchor = normalizeText(chunkParagraphs[chunkParagraphs.length - 1] || '');

    // 计算理想位置：均匀分布
    // 图片1: 大约在 1/(n+1) 位置
    // 图片2: 大约在 2/(n+1) 位置
    // ...
    const idealRatio = (sceneIndex + 1) / (totalScenes + 1);
    const idealPos = Math.floor(idealRatio * totalParagraphs);

    // 在理想位置附近搜索（前后各一半的范围）
    const searchRange = Math.max(2, Math.floor(totalParagraphs / totalScenes / 2));
    const startPos = Math.max(0, idealPos - searchRange);
    const endPos = Math.min(totalParagraphs - 1, idealPos + searchRange);

    let bestParagraphPos = idealPos;
    let bestScore = -1;

    // 在搜索范围内寻找最佳匹配
    for (let pos = startPos; pos <= endPos; pos++) {
      const blockIndex = paragraphIndexes[pos];
      const paragraphNorm = normalizeText(blocks[blockIndex].text);

      const score = earlyMatchScore(firstAnchor, lastAnchor, paragraphNorm);

      // 给接近理想位置的一些加分
      const distanceBonus = Math.max(0, 20 - Math.abs(pos - idealPos) * 5);
      const totalScore = score + distanceBonus;

      if (totalScore > bestScore) {
        bestScore = totalScore;
        bestParagraphPos = pos;
      }
    }

    const pickedBlockIndex = paragraphIndexes[bestParagraphPos];

    const existing = matched.get(pickedBlockIndex) || [];
    existing.push(scene);
    matched.set(pickedBlockIndex, existing);
  }

  return matched;
}

async function downloadFile(url: string, filename?: string, isImage: boolean = false) {
  try {
    const response = await fetchApi(url, {
      method: 'GET',
      headers: {
        Accept: isImage ? 'image/png,image/jpeg' : 'application/pdf',
      },
    });

    const contentType = (response.headers.get('content-type') || '').toLowerCase();
    const isValidType = isImage
      ? contentType.includes('image/')
      : contentType.includes('application/pdf');

    if (!isValidType) {
      const raw = await response.text();
      let detail = isImage ? '下载内容不是图片文件' : '下载内容不是 PDF 文件';
      try {
        const parsed = JSON.parse(raw || '{}');
        detail = parsed.msg || parsed.detail || parsed.error || detail;
      } catch {
        if (raw) detail = raw.slice(0, 180);
      }
      throw new Error(detail);
    }

    const blob = await response.blob();
    const minSize = isImage ? 1024 : 1024;
    if (!blob || blob.size < minSize) {
      throw new Error(isImage ? '下载到的图片文件异常或过小，请稍后重试' : '下载到的 PDF 文件异常或过小，请稍后重试');
    }

    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename || (isImage ? '童科绘绘本.png' : '童科绘绘本.pdf');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
    return true;
  } catch (err) {
    console.error('文件下载失败:', err);
    return false;
  }
}

function handlePrint(printRef: React.RefObject<HTMLDivElement>) {
  const content = printRef.current;
  if (!content) return;

  // 创建打印窗口
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('请允许弹出窗口以使用打印功能');
    return;
  }

  // 复制内容样式
  const styles = Array.from(document.querySelectorAll('style, link[rel="stylesheet"]'))
    .map(el => el.outerHTML)
    .join('');

  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>${content.querySelector('h2')?.textContent || '童科绘绘本'}</title>
      ${styles}
      <style>
        @media print {
          body { margin: 20px; font-family: system-ui, sans-serif; }
          figure { page-break-inside: avoid; }
          h1, h2, h3 { page-break-after: avoid; }
          .no-print { display: none !important; }
        }
        body { font-family: system-ui, sans-serif; line-height: 1.8; }
        img { max-width: 100%; height: auto; }
        figure { margin: 20px 0; padding: 10px; background: #fff9ea; border-radius: 8px; }
        figcaption { text-align: center; color: #666; font-size: 14px; margin-top: 8px; }
        h1, h2, h3 { color: #333; }
        h2 { border-left: 4px solid #ff9f45; padding-left: 12px; margin-top: 24px; }
        .glossary-section { margin-top: 32px; padding: 20px; background: linear-gradient(135deg, #fff5e8, #fffdf8, #eef8ff); border-radius: 12px; border: 2px solid #ffb067; }
        .glossary-item { margin: 12px 0; padding: 12px; background: white; border-radius: 8px; border: 1px solid #ffd3a6; }
        .glossary-term { display: inline-block; padding: 4px 10px; background: #fff3e3; border-radius: 9999px; font-weight: bold; color: #8a3e00; border: 1px solid #ffc68e; }
      </style>
    </head>
    <body>
      ${content.innerHTML}
    </body>
    </html>
  `);

  printWindow.document.close();

  // 等待图片加载后打印
  setTimeout(() => {
    printWindow.focus();
    printWindow.print();
  }, 500);
}

export default function PublishLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state || {}) as any;

  const storyData: StoryData = state.storyData || {};
  const scienceData: ScienceData = state.scienceData || {};
  const illustrations: Scene[] = Array.isArray(state.illustrations) ? state.illustrations : [];

  const [pageStep, setPageStep] = useState<1 | 2>(1);
  const [selectedLayout] = useState<'paragraph_image'>('paragraph_image');
  const [isExporting, setIsExporting] = useState(false);
  const [isExportingImage, setIsExportingImage] = useState(false);
  const [error, setError] = useState('');
  const [pdfUrl, setPdfUrl] = useState<string>(state?.publisherData?.pdfUrl || '');
  const [pdfFilename, setPdfFilename] = useState<string>(state?.publisherData?.filename || '');
  const [imageUrl, setImageUrl] = useState<string>(state?.publisherData?.imageUrl || '');
  const [imageFilename, setImageFilename] = useState<string>(state?.publisherData?.imageFilename || '');
  const [extraGlossaryEntries, setExtraGlossaryEntries] = useState<GlossaryEntry[]>([]);
  const [selectedGlossaryTerm, setSelectedGlossaryTerm] = useState('');
  const [useFallback, setUseFallback] = useState(false);
  const glossarySectionRef = useRef<HTMLDivElement | null>(null);
  const printContentRef = useRef<HTMLDivElement | null>(null);

  const title = storyData.title || state.storyTitle || '未命名故事';
  const storyVersionLabel = useMemo(() => getModelVersionBadge('/editor/layout', state), [state]);
  const finalContent = useMemo(() => {
    const raw = scienceData.revised_content || storyData.content || '';
    return stripTrailingResourceRecommendations(raw);
  }, [scienceData.revised_content, storyData.content]);

  const baseGlossary = useMemo(() => {
    if (Array.isArray(scienceData.revised_glossary) && scienceData.revised_glossary.length > 0) {
      return scienceData.revised_glossary;
    }
    if (Array.isArray(scienceData.glossary) && scienceData.glossary.length > 0) {
      return scienceData.glossary;
    }
    return Array.isArray(storyData.glossary) ? storyData.glossary : [];
  }, [scienceData.revised_glossary, scienceData.glossary, storyData.glossary]);

  const scienceHighlightTerms = useMemo(() => {
    const terms = Array.isArray(scienceData.highlight_terms) ? scienceData.highlight_terms : [];
    return Array.from(
      new Set(
        terms
          .map((term) => String(term || '').trim())
          .filter((term) => term.length >= 2),
      ),
    );
  }, [scienceData.highlight_terms]);

  const blocks = useMemo(() => splitBlocks(finalContent), [finalContent]);
  const sceneMapping = useMemo(() => matchScenesToParagraphs(blocks, illustrations), [blocks, illustrations]);
  const glossaryEntries = useMemo(() => {
    const source = baseGlossary;
    const map = new Map<string, GlossaryEntry>();

    source.forEach((item: any) => {
      const term = String(item?.term || '').trim();
      if (!term) return;
      if (map.has(term)) return;

      const explanation = String(item?.explanation || '').trim();
      map.set(term, {
        term,
        explanation: explanation || `${term}是本文涉及的科普词条，可结合正文理解其含义。`,
      });
    });

    extraGlossaryEntries.forEach((item) => {
      const term = String(item?.term || '').trim();
      if (!term) return;
      if (map.has(term)) return;
      const explanation = String(item?.explanation || '').trim();
      map.set(term, {
        term,
        explanation: explanation || `${term}是本文涉及的科普词条，可结合正文理解其含义。`,
      });
    });

    return Array.from(map.values());
  }, [baseGlossary, extraGlossaryEntries]);

  const glossaryTerms = useMemo(() => {
    const terms = [
      ...scienceHighlightTerms,
      ...glossaryEntries.map((item) => String(item?.term || '').trim()),
    ]
      .map((item) => String(item || '').trim())
      .filter((term) => term.length >= 2);
    return Array.from(new Set(terms)).sort((a, b) => b.length - a.length).slice(0, 12);
  }, [scienceHighlightTerms, glossaryEntries]);

  const createFallbackExplanation = (term: string, content: string) => {
    const text = (content || '').replace(/\s+/g, ' ').trim();
    const index = text.indexOf(term);
    if (index < 0) {
      return `${term}是文中出现的科普词条。它通常用于描述相关科学概念，建议结合上下文和权威资料进一步理解。`;
    }

    const start = Math.max(0, index - 26);
    const end = Math.min(text.length, index + term.length + 32);
    const snippet = text.slice(start, end).trim();
    return `${term}是文中重点科普词条。结合正文语境“${snippet}”，它反映了该段核心科学概念，建议在阅读时重点关注其定义、作用与适用场景。`;
  };

  const handleGlossaryTermClick = (term: string) => {
    const normalizedTerm = String(term || '').trim();
    if (!normalizedTerm) return;

    setSelectedGlossaryTerm(normalizedTerm);

    const exists = glossaryEntries.some((item) => item.term === normalizedTerm);
    if (!exists) {
      const contentText = String(finalContent || '');
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

  const renderHighlightedParagraph = (text: string, highlightedTermKeys: Set<string>) => {
    if (!text || glossaryTerms.length === 0) return text;

    const escapedTerms = glossaryTerms
      .map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      .filter(Boolean);
    if (escapedTerms.length === 0) return text;

    const regex = new RegExp(`(${escapedTerms.join('|')})`, 'g');
    const nodes: JSX.Element[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;
    let keyIndex = 0;

    while ((match = regex.exec(text)) !== null) {
      const matchedText = match[0];
      const offset = match.index;
      if (offset > lastIndex) {
        nodes.push(<span key={`text-${keyIndex}-${lastIndex}`}>{text.slice(lastIndex, offset)}</span>);
      }

      const isSelected = matchedText === selectedGlossaryTerm;
      const termKey = String(matchedText).toLowerCase();
      if (!highlightedTermKeys.has(termKey)) {
        nodes.push(
          <mark
            key={`mark-${keyIndex}-${offset}`}
            className={`rounded px-1 py-0.5 border cursor-pointer transition-colors ${
              isSelected
                ? 'bg-[#C9F6DC] text-[#0B6B3A] border-[#95E7B8]'
                : 'bg-[#DDFCE9] text-[#0B6B3A] border-[#B8EFCF] hover:bg-[#C9F6DC]'
            }`}
            title={`点击查看词条：${matchedText}`}
            onClick={() => handleGlossaryTermClick(matchedText)}
          >
            {matchedText}
          </mark>,
        );
        highlightedTermKeys.add(termKey);
      } else {
        nodes.push(<span key={`dup-${keyIndex}-${offset}`}>{matchedText}</span>);
      }

      lastIndex = offset + matchedText.length;
      keyIndex += 1;
    }

    if (lastIndex < text.length) {
      nodes.push(<span key={`text-tail-${lastIndex}`}>{text.slice(lastIndex)}</span>);
    }

    return nodes.length > 0 ? nodes : text;
  };

  const renderPreview = () => {
    const highlightedTermKeys = new Set<string>();
    return (
      <div className="space-y-5">
        {blocks.map((block, index) => {
          if (block.type === 'heading') {
            return (
              <h3
                key={`block-${index}`}
                className="text-[22px] md:text-[24px] leading-tight font-extrabold text-gray-900 border-l-4 border-orange-400 pl-3 mt-7"
              >
                {block.text.replace(/^#+\s*/, '')}
              </h3>
            );
          }

          const images = sceneMapping.get(index) || [];

          return (
            <div key={`block-${index}`} className="space-y-3">
              <p className="text-[16px] leading-8 text-gray-800" style={{ textIndent: '2em' }}>{renderHighlightedParagraph(block.text, highlightedTermKeys)}</p>
              {images.map((image) =>
                image?.image_url ? (
                  <figure key={`scene-${image.scene_id}`} className="rounded-2xl border border-orange-100 bg-orange-50/40 p-3">
                    <img
                      src={image.image_url}
                      alt={`story-image-${image.scene_id || index}`}
                      className="w-full h-auto rounded-xl border border-gray-200 object-contain"
                    />
                    <figcaption className="text-[13px] text-gray-600 mt-2 text-center leading-6">
                      {image.summary || image.image_prompt || `插图 ${image.scene_id || index}`}
                    </figcaption>
                  </figure>
                ) : null,
              )}
            </div>
          );
        })}

        <section
          ref={glossarySectionRef}
          className="mt-6 rounded-2xl border-2 border-[#FFB067] bg-gradient-to-br from-[#FFF5E8] via-[#FFFDF8] to-[#EEF8FF] p-5 shadow-[0_10px_24px_rgba(255,159,69,0.15)]"
        >
          <div className="mb-4 flex items-center gap-3">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#FF9F45] text-white shadow-[0_6px_14px_rgba(255,159,69,0.35)]">
              <Sparkles size={18} />
            </span>
            <div>
              <h3 className="text-[20px] font-black tracking-tight text-[#8A3E00]">文末科普词条</h3>
              <p className="text-xs text-[#A65A1A]">阅读完正文后，可在这里快速回顾核心科学概念</p>
            </div>
          </div>
          {glossaryEntries.length > 0 ? (
            <div className="space-y-3">
              {glossaryEntries.map((item, index) => (
                <div
                  key={`${item.term}-${index}`}
                  className="rounded-xl border border-[#FFD3A6] bg-white px-4 py-3 shadow-[0_4px_12px_rgba(255,176,103,0.12)]"
                >
                  <p
                    className={`mb-1 inline-flex items-center rounded-full border px-2.5 py-0.5 text-sm font-extrabold ${
                      item.term === selectedGlossaryTerm
                        ? 'border-[#FF9F45] bg-[#FFE7CC] text-[#7A3000]'
                        : 'border-[#FFC68E] bg-[#FFF3E3] text-[#8A3E00]'
                    }`}
                  >
                    {item.term}
                  </p>
                  <p className="text-sm leading-7 text-gray-800">{item.explanation}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-lg border border-dashed border-[#FFC68E] bg-white/80 px-3 py-2 text-sm text-[#A65A1A]">
              暂无 glossary 词条。
            </p>
          )}
        </section>
      </div>
    );
  };

  const exportPdf = useCallback(async () => {
    if (!finalContent) {
      setError('当前没有可导出的正文内容，请先完成前面的步骤。');
      return;
    }

    setIsExporting(true);
    setError('');
    setUseFallback(false);

    try {
      const response = await fetchApi('/api/publisher/export-pdf', {
        method: 'POST',
        body: JSON.stringify({
          story_id: storyData.id,
          title,
          content: finalContent,
          glossary: glossaryEntries,
          highlight_terms: glossaryTerms,
          illustrations,
          layout_type: selectedLayout,
        }),
      });

      const result: PublisherResponse = await response.json();
      if (result.code !== 200) {
        throw new Error(result.msg || 'PDF 导出失败');
      }

      const downloadUrl = result.data?.download_url;
      if (!downloadUrl) {
        throw new Error('后端未返回下载地址');
      }

      const url = downloadUrl.startsWith('http')
        ? downloadUrl
        : joinApiUrl(downloadUrl);

      const filename = result.data?.filename || `${title || '童科绘绘本'}.pdf`;

      setPdfUrl(url);
      setPdfFilename(filename);

      navigate(location.pathname, {
        replace: true,
        state: {
          ...(state || {}),
          publisherData: {
            ...(state?.publisherData || {}),
            pdfUrl: url,
            filename,
          },
        },
      });

      // 尝试直接下载
      const downloaded = await downloadFile(url, filename, false);
      if (!downloaded) {
        setError('PDF 下载失败，请重试；若仍失败请检查登录状态或后端导出日志。');
      }
    } catch (err: any) {
      console.error('PDF 导出失败:', err);
      setError(err.message || 'PDF 导出失败，请检查后端服务。');
      setUseFallback(true);
    } finally {
      setIsExporting(false);
    }
  }, [storyData.id, finalContent, glossaryEntries, glossaryTerms, title, illustrations, selectedLayout, location.pathname, navigate, state]);

  const exportImage = useCallback(async () => {
    if (!finalContent) {
      setError('当前没有可导出的正文内容，请先完成前面的步骤。');
      return;
    }

    setIsExportingImage(true);
    setError('');
    setUseFallback(false);

    try {
      const response = await fetchApi('/api/publisher/export-image', {
        method: 'POST',
        body: JSON.stringify({
          story_id: storyData.id,
          title,
          content: finalContent,
          glossary: glossaryEntries,
          highlight_terms: glossaryTerms,
          illustrations,
          layout_type: selectedLayout,
        }),
      });

      const result: PublisherResponse = await response.json();
      if (result.code !== 200) {
        throw new Error(result.msg || '长图片导出失败');
      }

      const downloadUrl = result.data?.download_url;
      if (!downloadUrl) {
        throw new Error('后端未返回下载地址');
      }

      const url = downloadUrl.startsWith('http')
        ? downloadUrl
        : joinApiUrl(downloadUrl);

      const filename = result.data?.filename || `${title || '童科绘绘本'}.png`;

      setImageUrl(url);
      setImageFilename(filename);

      navigate(location.pathname, {
        replace: true,
        state: {
          ...(state || {}),
          publisherData: {
            ...(state?.publisherData || {}),
            imageUrl: url,
            imageFilename: filename,
          },
        },
      });

      // 尝试直接下载
      const downloaded = await downloadFile(url, filename, true);
      if (!downloaded) {
        setError('长图片下载失败，请重试；若仍失败请检查登录状态或后端导出日志。');
      }
    } catch (err: any) {
      console.error('长图片导出失败:', err);
      setError(err.message || '长图片导出失败，请检查后端服务。');
      setUseFallback(true);
    } finally {
      setIsExportingImage(false);
    }
  }, [storyData.id, finalContent, glossaryEntries, glossaryTerms, title, illustrations, selectedLayout, location.pathname, navigate, state]);

  if (!finalContent) {
    return (
      <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.06)] border border-gray-100 p-6 min-h-[500px]">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">7.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">排版</h3>
            <p className="text-sm text-gray-500">请先完成故事创作与插画生成，再进入排版。</p>
          </div>
        </div>

        <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[320px] bg-gray-50/50 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-500 mb-4">尚未找到可排版的故事正文。</p>
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
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">7.</div>
        <div>
          <h3 className="text-xl font-bold text-gray-900">排版与导出</h3>
          <p className="text-sm text-gray-500">预览排版效果，导出并保存 PDF 文件。</p>
        </div>
      </div>

      {pageStep === 1 ? (
        <div className="border border-gray-200 rounded-2xl p-5 bg-gradient-to-br from-orange-50 via-amber-50 to-white">
          <p className="text-sm text-gray-500 mb-3">第 1 页：选择排版格式</p>
          <button
            className="w-full text-left p-5 rounded-2xl border-2 border-orange-300 bg-white shadow-sm"
            type="button"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-orange-100 text-[#FF9F45] inline-flex items-center justify-center">
                <Newspaper size={22} />
              </div>
              <div className="flex-1">
                <p className="text-[18px] font-extrabold text-gray-900">文章嵌入图片</p>
                <p className="text-sm text-gray-600 mt-1 leading-6">
                  行文一段文字后，在下方插入该段对应插图，形成自然的图文交替阅读体验。
                </p>
              </div>
              <CheckCircle2 className="text-orange-500" size={20} />
            </div>
          </button>

          <div className="mt-6 flex justify-end">
            <button
              onClick={() => setPageStep(2)}
              className="inline-flex items-center gap-2 px-6 py-3 bg-[#FF9F45] text-white rounded-[12px] font-bold text-[14px] shadow-[0_4px_12px_rgba(255,159,69,0.2)] hover:bg-[#FF8C1A] transition-all"
            >
              下一步
              <Sparkles size={16} />
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="border border-gray-200 rounded-2xl p-6 bg-[#fffdf8]">
            <div className="mb-5 flex items-center justify-between gap-3">
              <h2 className="text-[30px] leading-tight font-black text-gray-900 text-center flex-1">{title}</h2>
              {storyVersionLabel ? (
                <span className="shrink-0 inline-flex items-center rounded-full border border-orange-200 bg-orange-50 px-3 py-1 text-[12px] font-bold text-[#B75A00]">
                  {storyVersionLabel}
                </span>
              ) : null}
            </div>
            {renderPreview()}

            {error && (
              <div className="mt-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-start gap-2">
                <AlertCircle size={18} className="flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p>{error}</p>
                  {useFallback && (
                    <p className="mt-2 text-xs text-gray-600">
                      提示：请确保后端服务已启动，并且 /api/publisher/export-pdf 接口可用。
                    </p>
                  )}
                </div>
              </div>
            )}

            <div className="mt-8 pt-4 border-t border-orange-100 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={exportPdf}
                  disabled={isExporting || isExportingImage}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#FF9F45] text-white hover:bg-[#FF8C1A] disabled:opacity-60 disabled:cursor-not-allowed transition-colors shadow-[0_4px_12px_rgba(255,159,69,0.2)] font-bold"
                >
                  {isExporting ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      正在生成 PDF...
                    </>
                  ) : (
                    <>
                      <FileDown size={18} />
                      生成并下载 PDF
                    </>
                  )}
                </button>

                <button
                  onClick={exportImage}
                  disabled={isExporting || isExportingImage}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600 disabled:opacity-60 disabled:cursor-not-allowed transition-colors shadow-[0_4px_12px_rgba(168,85,247,0.2)] font-bold"
                >
                  {isExportingImage ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      正在生成长图片...
                    </>
                  ) : (
                    <>
                      <ImageIcon size={18} />
                      生成并下载长图
                    </>
                  )}
                </button>

                {pdfUrl && (
                  <>
                    <button
                      onClick={() => downloadFile(pdfUrl, pdfFilename, false)}
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-green-500 text-green-600 bg-green-50 hover:bg-green-100 transition-colors font-semibold"
                    >
                      <Download size={16} />
                      重新下载 PDF
                    </button>
                    <a
                      href={pdfUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 transition-colors font-semibold"
                    >
                      <ExternalLink size={16} />
                      打开 PDF
                    </a>
                  </>
                )}

                {imageUrl && (
                  <>
                    <button
                      onClick={() => downloadFile(imageUrl, imageFilename, true)}
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-purple-500 text-purple-600 bg-purple-50 hover:bg-purple-100 transition-colors font-semibold"
                    >
                      <Download size={16} />
                      重新下载长图
                    </button>
                    <a
                      href={imageUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 transition-colors font-semibold"
                    >
                      <ExternalLink size={16} />
                      打开长图
                    </a>
                  </>
                )}
              </div>

              <button
                onClick={() => navigate('/')}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-green-500 text-white rounded-[12px] font-bold text-[14px] hover:bg-green-600 transition-colors"
              >
                完成创作
                <CheckCircle2 size={16} />
              </button>
            </div>
          </div>

          <div className="flex justify-start">
            <button
              onClick={() => setPageStep(1)}
              className="text-sm text-gray-500 hover:text-[#FF9F45]"
            >
              返回上一步（重新选择排版格式）
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

