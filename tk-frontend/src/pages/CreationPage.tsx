import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Smile, Wrench, Heart, Briefcase, Leaf,
  Sparkles, BookOpen,
  Check, ChevronRight, Wand2, ArrowLeft, ChevronDown, RefreshCw,
  Search
} from 'lucide-react';
import apiClient, {
  type StorySuggestion,
} from '../lib/api-client';

const AUDIENCES = [
  { id: '1', label: '青少幼年儿童', icon: Smile, desc: '启蒙认知、激发好奇心' },
  { id: '2', label: '产业工人', icon: Wrench, desc: '技能提升、工匠精神' },
  { id: '3', label: '老年人', icon: Heart, desc: '健康科普、跨越数字鸿沟' },
  { id: '4', label: '领导干部和公务员', icon: Briefcase, desc: '科学决策、生态文明' },
  { id: '5', label: '农民', icon: Leaf, desc: '乡村振兴、现代农业' }
];

const SUB_AUDIENCES = [
  { id: '1_1', label: '幼年 (3-6岁)', desc: '简单趣味，语言极生动易懂' },
  { id: '1_2', label: '少儿 (6-12岁)', desc: '激发想象，培养探索兴趣' },
  { id: '1_3', label: '青少年 (12-28岁)', desc: '深入原理，树立科学价值观' }
];

const THEME_OPTIONS = [
  '健康与医疗',
  '气候与环境前沿技术',
  '航空航天',
  '能源利用',
  '应急避险',
  '食品安全',
  '科普活动',
  '伪科学'
];

const STYLE_OPTIONS = [
  '趣味故事型',
  '百科全书型'
];

const EMPTY_TITLE_INSPIRATIONS: StorySuggestion[] = [
  { title: '小红细胞的极速快递冒险', category: '健康与医疗', clue: '从一次擦伤出发，认识血液如何守护身体。' },
  { title: '会呼吸的地球与碳足迹侦探', category: '气候与环境前沿技术', clue: '跟着小队追踪碳排放，学会绿色生活。' },
  { title: '月球基地的第一堂科学课', category: '航空航天', clue: '在失重环境里探索宇航员的日常挑战。' },
  { title: '风车镇的电力守护计划', category: '能源利用', clue: '对比风能、太阳能与储能技术的协作。' },
  { title: '地震警报响起后的黄金十分钟', category: '应急避险', clue: '通过校园演练掌握关键自救方法。' },
  { title: '神秘午餐盒里的食品安全线索', category: '食品安全', clue: '辨别保质期、添加剂与营养搭配误区。' },
  { title: '社区科学节的奇妙实验大赛', category: '科普活动', clue: '用可操作实验点燃孩子的科学好奇心。' },
  { title: '谣言粉碎机：破解伪科学迷雾', category: '伪科学', clue: '训练证据思维，识别常见伪科学套路。' },
];

function normalizeArticleStyle(style?: string) {
  const raw = String(style || '').trim();
  if (!raw) return '趣味故事型';
  if (raw.includes('百科')) return '百科全书型';
  if (raw.includes('趣味') || raw.includes('童话') || raw.includes('问答') || raw.includes('科普')) {
    return '趣味故事型';
  }
  return raw;
}

const RANDOM_TITLE_HISTORY_KEY = 'tk_random_title_history_v1';
const RANDOM_TITLE_HISTORY_LIMIT = 8;

function normalizeTitleForHistory(title: string): string {
  return String(title || '')
    .trim()
    .toLowerCase()
    .replace(/[\s\p{P}\p{S}]+/gu, '');
}

function resolveAgeGroupText(targetAudience: string, subAudience: string) {
  if (targetAudience === '1') {
    const map: Record<string, string> = {
      '1_1': '3-6岁',
      '1_2': '6-12岁',
      '1_3': '12-28岁',
    };
    return map[subAudience] || '6-12岁';
  }

  const audienceMap: Record<string, string> = {
    '2': '产业工人',
    '3': '老年人',
    '4': '领导干部和公务员',
    '5': '农民',
  };
  return audienceMap[targetAudience] || '全年龄段';
}

export default function CreationPage() {
  const navigate = useNavigate();
  const [showThemeDropdown, setShowThemeDropdown] = useState(false);
  const [showStyleDropdown, setShowStyleDropdown] = useState(false);
  const themeDropdownRef = useRef<HTMLDivElement>(null);
  const styleDropdownRef = useRef<HTMLDivElement>(null);

  const [formData, setFormData] = useState({
    projectTitle: '',
    theme: '令人惊奇的科学现象',
    themeCategory: '',
    articleStyle: '趣味故事型',
    wordCount: 1200,
    targetAudience: '1',
    subAudience: '1_2',
    extraStoryReq: '',
    artStyle: '1',
    imageCount: 3,
    extraDrawReq: '',
  });
  const [suggestions, setSuggestions] = useState<StorySuggestion[]>([]);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const [isGeneratingRandomTitle, setIsGeneratingRandomTitle] = useState(false);
  const [isMatchingThemeCategory, setIsMatchingThemeCategory] = useState(false);
  const [recentRandomTitleHistory, setRecentRandomTitleHistory] = useState<string[]>([]);
  const [wordCountInput, setWordCountInput] = useState('1200');
  const [emptyTitleSuggestions, setEmptyTitleSuggestions] = useState<StorySuggestion[]>([]);

  const handleChange = (key: string, value: any) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (themeDropdownRef.current && !themeDropdownRef.current.contains(event.target as Node)) {
        setShowThemeDropdown(false);
      }
      if (styleDropdownRef.current && !styleDropdownRef.current.contains(event.target as Node)) {
        setShowStyleDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(RANDOM_TITLE_HISTORY_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        const cleaned = parsed
          .map((item) => String(item || '').trim())
          .filter(Boolean)
          .slice(0, RANDOM_TITLE_HISTORY_LIMIT);
        setRecentRandomTitleHistory(cleaned);
      }
    } catch {
      // ignore bad local data
    }
  }, []);

  useEffect(() => {
    const seed = (formData.projectTitle || '').trim();
    if (!seed) {
      setSuggestions([]);
      setIsSuggesting(false);
      return;
    }

    if (seed.length < 2) {
      setSuggestions([]);
      setIsSuggesting(false);
      return;
    }

    let canceled = false;
    setIsSuggesting(true);

    const timer = window.setTimeout(async () => {
      try {
        const next = await apiClient.suggestTitles({
          theme: seed,
          target_audience: AUDIENCES.find(a => a.id === formData.targetAudience)?.label || '青少幼年儿童',
          age_group: resolveAgeGroupText(formData.targetAudience, formData.subAudience),
        });

        if (canceled) return;

        const filtered = Array.isArray(next)
          ? next.filter((item: any) => item?.title && item?.category && item?.clue).slice(0, 4)
          : [];

        setSuggestions(filtered);
        if (!formData.themeCategory && filtered[0]?.category) {
          setFormData(prev => ({ ...prev, themeCategory: filtered[0].category }));
        }
      } catch {
        if (!canceled) {
          setSuggestions([]);
        }
      } finally {
        if (!canceled) {
          setIsSuggesting(false);
        }
      }
    }, 420);

    return () => {
      canceled = true;
      window.clearTimeout(timer);
    };
  }, [formData.projectTitle, formData.theme, formData.targetAudience, formData.subAudience, refreshTick]);

  const suggestionSeed = (formData.projectTitle || '').trim();
  const hasProjectTitle = suggestionSeed.length > 0;

  const refreshEmptyTitleSuggestions = useCallback(() => {
    const shuffled = [...EMPTY_TITLE_INSPIRATIONS].sort(() => Math.random() - 0.5);
    setEmptyTitleSuggestions(shuffled.slice(0, 4));
  }, []);

  useEffect(() => {
    if (hasProjectTitle) return;
    refreshEmptyTitleSuggestions();
  }, [hasProjectTitle, refreshTick, refreshEmptyTitleSuggestions]);

  const displaySuggestions = hasProjectTitle ? suggestions : emptyTitleSuggestions;

  const groupedSuggestions = [
    { title: hasProjectTitle ? '高匹配推荐' : '随机主题灵感', items: displaySuggestions.slice(0, 2) },
    { title: hasProjectTitle ? '拓展灵感推荐' : '更多主题方向', items: displaySuggestions.slice(2, 4) },
  ];

  const handleRefreshSuggestions = () => {
    if (isSuggesting) return;
    if (!hasProjectTitle) {
      setRefreshTick(prev => prev + 1);
      return;
    }
    if (suggestionSeed.length < 2) return;
    setRefreshTick(prev => prev + 1);
  };

  const normalizeThemeCategory = (raw: string) => {
    const value = String(raw || '').trim();
    if (!value) return '';

    const exact = THEME_OPTIONS.find((item) => item === value);
    if (exact) return exact;

    const fuzzy = THEME_OPTIONS.find((item) => item.includes(value) || value.includes(item));
    return fuzzy || '';
  };

  const fallbackThemeCategoryByTitle = (title: string) => {
    const text = String(title || '').toLowerCase();
    if (!text) return '科普活动';

    const rules: Array<{ category: string; keywords: string[] }> = [
      { category: '健康与医疗', keywords: ['健康', '医疗', '细菌', '病毒', '免疫', '医生', '身体', '疾病'] },
      { category: '气候与环境前沿技术', keywords: ['气候', '环境', '碳', '污染', '生态', '低碳', '温室', '环保'] },
      { category: '航空航天', keywords: ['太空', '火箭', '航天', '宇宙', '星球', '卫星', '月球', '空间站'] },
      { category: '能源利用', keywords: ['能源', '电力', '发电', '太阳能', '风能', '电池', '核能'] },
      { category: '应急避险', keywords: ['地震', '洪水', '台风', '应急', '避险', '灾害', '火灾', '求生'] },
      { category: '食品安全', keywords: ['食品', '食物', '营养', '餐桌', '安全', '添加剂', '饮食'] },
      { category: '科普活动', keywords: ['实验', '科学课', '探索', '探险', '发现', '小科学家', '科普'] },
      { category: '伪科学', keywords: ['谣言', '骗局', '玄学', '偏方', '伪科学', '误区', '辟谣'] },
    ];

    const matched = rules.find((rule) => rule.keywords.some((kw) => text.includes(kw)));
    return matched?.category || '科普活动';
  };

  const handleAutoMatchThemeCategory = async () => {
    if (isMatchingThemeCategory) return;

    const titleSeed = (formData.projectTitle || '').trim();
    if (!titleSeed) {
      const fallback = fallbackThemeCategoryByTitle(formData.theme || '');
      setFormData((prev) => ({ ...prev, theme: fallback, themeCategory: fallback }));
      return;
    }

    setIsMatchingThemeCategory(true);
    try {
      const suggestions = await apiClient.suggestTitles({
        theme: titleSeed,
        target_audience: AUDIENCES.find(a => a.id === formData.targetAudience)?.label || '青少幼年儿童',
        age_group: resolveAgeGroupText(formData.targetAudience, formData.subAudience),
      });
      const candidates = Array.isArray(suggestions)
        ? suggestions
            .map((item: any) => normalizeThemeCategory(String(item?.category || '')))
            .filter(Boolean)
        : [];

      let best = '';
      if (candidates.length > 0) {
        const countMap = new Map<string, number>();
        candidates.forEach((cat: string) => {
          countMap.set(cat, (countMap.get(cat) || 0) + 1);
        });
        best = Array.from(countMap.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] || '';
      }

      const finalCategory = best || fallbackThemeCategoryByTitle(titleSeed);
      setFormData((prev) => ({ ...prev, theme: finalCategory, themeCategory: finalCategory }));
    } catch {
      const fallback = fallbackThemeCategoryByTitle(titleSeed);
      setFormData((prev) => ({ ...prev, theme: fallback, themeCategory: fallback }));
    } finally {
      setIsMatchingThemeCategory(false);
    }
  };

  const handleRandomProjectTitle = async () => {
    if (isGeneratingRandomTitle) return;

    const seedTheme = (formData.theme || formData.projectTitle || '令人惊奇的科学现象').trim();
    const payload = {
      theme: seedTheme,
      target_audience: AUDIENCES.find(a => a.id === formData.targetAudience)?.label || '青少幼年儿童',
      age_group: resolveAgeGroupText(formData.targetAudience, formData.subAudience),
    };

    setIsGeneratingRandomTitle(true);
    try {
      const next = await apiClient.suggestTitles(payload);

      const filtered = Array.isArray(next)
        ? next.filter((item: any) => item?.title && item?.category)
        : [];

      if (filtered.length > 0) {
        const historySet = new Set(recentRandomTitleHistory.map(normalizeTitleForHistory));
        const nonRecent = filtered.filter((item: any) => !historySet.has(normalizeTitleForHistory(String(item?.title || ''))));
        const candidatePool = nonRecent.length > 0 ? nonRecent : filtered;
        const picked = candidatePool[Math.floor(Math.random() * candidatePool.length)];
        const pickedTitle = String(picked.title || '').trim();

        setFormData((prev) => ({
          ...prev,
          projectTitle: pickedTitle,
          themeCategory: prev.themeCategory || String(picked.category || '').trim(),
        }));

        setRecentRandomTitleHistory((prev) => {
          const pickedKey = normalizeTitleForHistory(pickedTitle);
          const nextHistory = [
            pickedTitle,
            ...prev.filter((item) => normalizeTitleForHistory(item) !== pickedKey),
          ].slice(0, RANDOM_TITLE_HISTORY_LIMIT);

          try {
            window.localStorage.setItem(RANDOM_TITLE_HISTORY_KEY, JSON.stringify(nextHistory));
          } catch {
            // ignore storage write failures
          }

          return nextHistory;
        });
      }
    } catch {
      // Ignore request error, keep user's current input untouched.
    } finally {
      setIsGeneratingRandomTitle(false);
    }
  };

  const handleGenerate = () => {
    const parsedWordCount = Number(wordCountInput);
    const finalWordCount = Number.isFinite(parsedWordCount)
      ? Math.max(300, Math.min(5000, parsedWordCount))
      : 1200;

    setWordCountInput(String(finalWordCount));
    setFormData((prev) => ({ ...prev, wordCount: finalWordCount }));

    const allSelectedReferences: any[] = [];

    // 处理空值给默认值
    const finalFormData = {
      ...formData,
      theme: formData.theme || formData.projectTitle || '令人惊奇的科学现象',
      projectTitle: formData.projectTitle || '',
      themeCategory: formData.themeCategory || (suggestions[0]?.category || ''),
      articleStyle: normalizeArticleStyle(formData.articleStyle),
      wordCount: finalWordCount,
    };
    console.log('提交生成参数：', finalFormData);
    // 直接导航至内部初始 Tab（/editor/draft）可以避免 App.tsx 顶层 Route 重定向丢失 State 状态
    navigate('/editor/draft', {
      state: {
        formData: finalFormData,
        ragReferences: allSelectedReferences, // 传递选中的参考材料详情
        workSessionId: `ws_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      },
    });
  };

  return (
    <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8 flex justify-center bg-[#FAFAF5]" style={{ fontFamily: 'Inter, sans-serif' }}>
      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-up {
          animation: fadeUp 0.5s ease-out forwards;
        }
      `}</style>

      <div className="w-full max-w-5xl text-[14px] leading-[1.6] text-gray-800">
        <button 
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-[14px] text-gray-500 hover:text-[#FF9F45] mb-6 font-medium transition-colors duration-200"
        >
          <ArrowLeft size={16} />
          返回主页
        </button>

        <div className="bg-[#FFF9EA] rounded-[12px] shadow-[0_2px_16px_rgba(0,0,0,0.04)] border border-gray-100 p-6 md:p-8 min-h-[500px]">
          <div className="flex items-center justify-between mb-8 pb-6 border-b border-[#FF9F45]/30 animate-fade-up" style={{ opacity: 0, animationDelay: '0s' }}>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-[12px] bg-[#FF9F45]/10 text-[#FF9F45] flex items-center justify-center shadow-sm border border-[#FF9F45]/20">
                <Wand2 size={24} strokeWidth={2} />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-800 tracking-tight">内容创作引导</h2>
                <p className="text-[12px] text-[#999] mt-1">挑选你的创作偏好，AI 魔法生成专属绘本 ✨</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-10">
            <div className="flex flex-col gap-8">
              
              <section className="animate-fade-up relative z-[100]" style={{ opacity: 0, animationDelay: '0.1s' }}>
                <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                  <BookOpen size={18} color="#FF9F45" />
                  1. 故事设定
                </h3>

                <div className="mb-5">
                  <label className="text-[14px] font-medium text-gray-700 block mb-2">项目标题</label>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <input
                      type="text"
                      value={formData.projectTitle}
                      onChange={(e) => handleChange('projectTitle', e.target.value)}
                      placeholder="例如：探索太阳系的奥秘、细菌的奇妙世界"
                      className="w-full bg-white rounded-[12px] border border-[#E5E7EB] px-4 py-3 text-gray-800 placeholder:text-[#999] hover:border-[#FF9F45] focus:outline-none focus:border-[#FF9F45] focus:ring-1 focus:ring-[#FF9F45] transition-all duration-200"
                    />
                    <button
                      type="button"
                      onClick={handleRandomProjectTitle}
                      disabled={isGeneratingRandomTitle}
                      className="sm:shrink-0 inline-flex items-center justify-center gap-2 rounded-[12px] border border-orange-200 bg-orange-50 px-4 py-3 text-[14px] font-semibold text-[#B75A00] hover:bg-orange-100 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                    >
                      <RefreshCw size={15} className={isGeneratingRandomTitle ? 'animate-spin' : ''} />
                      {isGeneratingRandomTitle ? '生成中...' : '随机标题'}
                    </button>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  <div className="flex flex-col gap-2 relative z-50" ref={themeDropdownRef}>
                    <label className="text-[14px] font-medium text-gray-700">科普主题</label>
                    <div className="relative group">
                      <input 
                        type="text" 
                        value={formData.theme}
                        onChange={(e) => handleChange('theme', e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !formData.theme) {
                            handleChange('theme', '令人惊奇的科学现象');
                          }
                        }}
                        placeholder="请输入科普主题"
                        className="w-full bg-white rounded-[12px] border border-[#E5E7EB] pl-4 pr-20 py-3 text-gray-800 placeholder:text-[#999] group-hover:border-[#FF9F45] focus:outline-none focus:border-[#FF9F45] focus:ring-1 focus:ring-[#FF9F45] transition-all duration-200"
                      />
                      <button
                        type="button"
                        onClick={handleAutoMatchThemeCategory}
                        disabled={isMatchingThemeCategory}
                        title="自动匹配主题类别"
                        className="absolute right-10 top-1/2 -translate-y-1/2 text-gray-400 group-hover:text-[#FF9F45] focus:outline-none transition-colors duration-200 disabled:opacity-50"
                      >
                        <Wand2 size={16} className={isMatchingThemeCategory ? 'animate-pulse' : ''} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowThemeDropdown(!showThemeDropdown)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 group-hover:text-[#FF9F45] focus:outline-none transition-colors duration-200"
                      >
                        <ChevronDown size={18} className={"transition-transform duration-200 " + (showThemeDropdown ? 'rotate-180' : '')} />
                      </button>
                    </div>
                    
                    {showThemeDropdown && (
                      <div className="absolute top-[calc(100%+8px)] left-0 w-full bg-white border border-[#E5E7EB] rounded-[12px] shadow-[0_4px_12px_rgba(255,159,69,0.1)] z-[60] py-2 max-h-60 overflow-y-auto">
                        {THEME_OPTIONS.map((theme, idx) => (
                          <button
                            key={idx}
                            onClick={() => {
                              handleChange('theme', theme);
                              setShowThemeDropdown(false);
                            }}
                            className="w-full text-left px-4 py-2.5 text-[14px] text-gray-700 hover:bg-[#FF9F45]/10 hover:text-[#FF9F45] transition-colors duration-200"
                          >
                            {theme}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col gap-2 relative z-40" ref={styleDropdownRef}>
                    <label className="text-[14px] font-medium text-gray-700">文笔风格</label>
                    <div className="relative group">
                      <input 
                        type="text" 
                        value={formData.articleStyle}
                        onChange={(e) => handleChange('articleStyle', e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !formData.articleStyle) {
                            handleChange('articleStyle', '趣味故事型');
                          }
                        }}
                        placeholder="请选择文笔风格"
                        className="w-full bg-white rounded-[12px] border border-[#E5E7EB] pl-4 pr-10 py-3 text-gray-800 placeholder:text-[#999] group-hover:border-[#FF9F45] focus:outline-none focus:border-[#FF9F45] focus:ring-1 focus:ring-[#FF9F45] transition-all duration-200"
                      />
                      <button
                        type="button"
                        onClick={() => setShowStyleDropdown(!showStyleDropdown)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 group-hover:text-[#FF9F45] focus:outline-none transition-colors duration-200"
                      >
                        <ChevronDown size={18} className={"transition-transform duration-200 " + (showStyleDropdown ? 'rotate-180' : '')} />
                      </button>
                    </div>

                    {showStyleDropdown && (
                      <div className="absolute top-[calc(100%+8px)] left-0 w-full bg-white border border-[#E5E7EB] rounded-[12px] shadow-[0_4px_12px_rgba(255,159,69,0.1)] z-[60] py-2 max-h-60 overflow-y-auto">
                        {STYLE_OPTIONS.map((style, idx) => (
                          <button
                            key={idx}
                            onClick={() => {
                              handleChange('articleStyle', style);
                              setShowStyleDropdown(false);
                            }}
                            className="w-full text-left px-4 py-2.5 text-[14px] text-gray-700 hover:bg-[#FF9F45]/10 hover:text-[#FF9F45] transition-colors duration-200"
                          >
                            {style}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col gap-2">
                    <label className="text-[14px] font-medium text-gray-700">字数要求</label>
                    <div className="relative group">
                      <input
                        type="number"
                        min={300}
                        max={5000}
                        step={100}
                        value={wordCountInput}
                        onChange={(e) => {
                          const raw = e.target.value;
                          setWordCountInput(raw);
                          if (raw === '') return;

                          const parsed = Number(raw);
                          if (Number.isFinite(parsed)) {
                            handleChange('wordCount', parsed);
                          }
                        }}
                        onBlur={() => {
                          if (wordCountInput === '') {
                            setWordCountInput('1200');
                            handleChange('wordCount', 1200);
                            return;
                          }

                          const parsed = Number(wordCountInput);
                          const normalized = Number.isFinite(parsed)
                            ? Math.max(300, Math.min(5000, parsed))
                            : 1200;
                          setWordCountInput(String(normalized));
                          handleChange('wordCount', normalized);
                        }}
                        className="w-full bg-white rounded-[12px] border border-[#E5E7EB] pl-4 pr-12 py-3 text-gray-800 placeholder:text-[#999] group-hover:border-[#FF9F45] focus:outline-none focus:border-[#FF9F45] focus:ring-1 focus:ring-[#FF9F45] transition-all duration-200"
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[13px] text-[#999]">字</span>
                    </div>
                    <p className="text-[12px] text-[#999]">默认 1200 字，建议范围 300-5000 字</p>
                  </div>
                </div>

                <div className="mt-5 bg-[linear-gradient(125deg,#F4F0FB_0%,#FFF7EE_52%,#FFF2E0_100%)] border border-[#EDE7DF] rounded-[20px] p-5 md:p-6 shadow-[0_14px_28px_rgba(0,0,0,0.06)]">
                  <div className="flex items-center justify-between gap-3 mb-4">
                    <div className="inline-flex items-center gap-2 text-[#F07E37] font-bold text-[18px]">
                      <Sparkles size={18} />
                      智能标题建议
                    </div>
                    <button
                      type="button"
                      onClick={handleRefreshSuggestions}
                      disabled={(hasProjectTitle && suggestionSeed.length < 2) || isSuggesting}
                      className="inline-flex items-center gap-1.5 text-[13px] px-3 py-1.5 rounded-full bg-white border border-[#FFD5B2] text-[#DD6F2F] hover:bg-[#FFF3E6] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <RefreshCw size={14} className={isSuggesting ? 'animate-spin' : ''} />
                      刷新建议
                    </button>
                  </div>

                  <h4 className="text-[26px] leading-[1.25] font-semibold text-[#B56A3A] text-center mb-5 tracking-[0.01em]" style={{ fontFamily: 'YouYuan, STXinwei, "Microsoft YaHei", sans-serif' }}>
                    {!hasProjectTitle
                      ? '未输入项目标题时，已为你随机准备 4 个不同主题灵感'
                      : suggestionSeed.length < 2
                        ? '输入至少2个字符，AI将自动生成相关主题建议'
                        : '基于当前项目标题，AI已生成 4 个相关推荐'}
                  </h4>

                  {isSuggesting ? (
                    <div className="space-y-5">
                      {[0, 1].map((groupIdx) => (
                        <div key={groupIdx}>
                          <div className="h-4 w-24 rounded bg-white/70 animate-pulse mb-3" />
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {[0, 1].map((itemIdx) => (
                              <div key={itemIdx} className="rounded-[16px] border border-white/80 bg-white/80 p-4 shadow-sm animate-pulse">
                                <div className="h-5 w-4/5 bg-gray-200 rounded mb-3" />
                                <div className="h-4 w-1/3 bg-orange-100 rounded mb-2" />
                                <div className="h-3 w-2/3 bg-gray-100 rounded" />
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : displaySuggestions.length > 0 ? (
                    <div className="space-y-5">
                      {groupedSuggestions.map((group) => (
                        <div key={group.title}>
                          <div className="mb-2 inline-flex items-center px-2.5 py-1 rounded-full bg-white/80 border border-[#F2D8BE] text-[#A76A43] text-[12px] font-semibold">
                            {group.title}
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {group.items.map((item, idx) => (
                              <button
                                key={`${item.title}-${idx}`}
                                type="button"
                                onClick={() => {
                                  handleChange('projectTitle', item.title);
                                  handleChange('themeCategory', item.category);
                                }}
                                className="text-left rounded-[16px] border border-white/90 bg-white px-5 py-4 hover:border-[#FF9F45] hover:shadow-[0_10px_20px_rgba(255,159,69,0.2)] hover:-translate-y-[1px] transition-all duration-200"
                              >
                                <p className="text-[23px] font-medium text-[#8C8A8A] leading-[1.25] tracking-tight">{item.title}</p>
                                <p className="text-[20px] mt-2 text-[#F7A66F] font-semibold">{item.category}</p>
                                <p className="text-[14px] text-[#9C9590] mt-1">{item.clue}</p>
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-[14px] text-gray-500 py-6 text-center">
                      输入至少2个字符后，将自动生成 4 个具体标题建议。
                    </div>
                  )}
                </div>
              </section>

              <section className="animate-fade-up relative z-[90]" style={{ opacity: 0, animationDelay: '0.2s' }}>
                <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                  <Smile size={18} color="#FF9F45" />
                  2. 目标受众选择
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {AUDIENCES.map((aud) => {
                    const isSelected = formData.targetAudience === aud.id;
                    const Icon = aud.icon;
                    return (
                      <button
                        key={aud.id}
                        onClick={() => handleChange('targetAudience', aud.id)}
                        className={"group relative p-4 rounded-[12px] border flex flex-col items-start gap-2 text-left transition-all duration-200 hover:-translate-y-[1px] hover:shadow-[0_4px_12px_rgba(216,154,99,0.12)] " + (
                          isSelected 
                            ? 'bg-[#FF9F45] border-[#FF9F45] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.22)]' 
                            : 'bg-white border-[#E5E7EB] hover:border-[#E7B483]'
                        )}
                      >
                        <Icon size={20} className={isSelected ? 'text-white' : 'text-gray-400 group-hover:text-[#FF9F45] transition-colors duration-200'} />
                        <div>
                          <div className={"font-semibold text-[14px] transition-colors duration-200 " + (isSelected ? 'text-white' : 'text-gray-700 group-hover:text-[#FF9F45]')}>{aud.label}</div>
                          <div className={"text-[12px] mt-1 leading-tight transition-colors duration-200 " + (isSelected ? 'text-white' : 'text-[#999]')}>{aud.desc}</div>
                        </div>
                        {isSelected && (
                          <div className="absolute top-2 right-2 text-[#FF9F45] bg-white rounded-full p-0.5 shadow-sm">
                            <Check size={14} strokeWidth={3} />
                          </div>
                        )}
                      </button>
                    )
                  })}
                </div>

                <div className={"mt-3 overflow-hidden transition-all duration-300 " + (formData.targetAudience === '1' ? 'max-h-[200px] opacity-100' : 'max-h-0 opacity-0')}>
                  <div className="p-4 bg-white border border-[#E5E7EB] rounded-[12px]">
                    <p className="text-[14px] font-medium text-gray-700 mb-3 ml-1">请选择具体儿童年龄段：</p>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {SUB_AUDIENCES.map(sub => {
                        const isSelected = formData.subAudience === sub.id;
                        return (
                          <button
                            key={sub.id}
                            onClick={() => handleChange('subAudience', sub.id)}
                            className={"group relative px-3 py-2.5 rounded-[12px] border flex justify-center text-center flex-col transition-all duration-200 hover:-translate-y-[1px] hover:shadow-[0_4px_12px_rgba(216,154,99,0.12)] " + (
                              isSelected 
                                ? 'bg-[#FF9F45] border-[#FF9F45] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.22)]' 
                                : 'bg-white border-[#E5E7EB] hover:border-[#E7B483]'
                            )}
                          >
                            <span className={"font-semibold text-[14px] transition-colors duration-200 " + (isSelected ? 'text-white' : 'text-gray-700 group-hover:text-[#FF9F45]')}>{sub.label}</span>
                            <span className={"text-[12px] mt-0.5 transition-colors duration-200 " + (isSelected ? 'text-white' : 'text-[#999]')}>{sub.desc}</span>
                            {isSelected && (
                              <div className="absolute top-1 right-1 text-[#FF9F45] bg-white rounded-full p-0.5 shadow-sm">
                                <Check size={12} strokeWidth={3} />
                              </div>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </section>

              <section className="animate-fade-up relative z-[80]" style={{ opacity: 0, animationDelay: '0.3s' }}>
                <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                  <Sparkles size={18} color="#FF9F45" />
                  3. 自定义故事诉求 (可选)
                </h3>
                <textarea
                  value={formData.extraStoryReq}
                  onChange={(e) => handleChange('extraStoryReq', e.target.value)}
                  placeholder="例如：主角必须是一只戴眼镜的蓝色小猫，或者故事发生在外太空..."
                  className="w-full bg-white rounded-[12px] border border-[#E5E7EB] px-4 py-3 text-[14px] text-gray-800 placeholder:text-[#999] focus:outline-none focus:border-[#FF9F45] focus:ring-1 focus:ring-[#FF9F45] hover:border-[#FF9F45] transition-all duration-200 resize-none h-24"
                />
              </section>

              <div className="animate-fade-up relative z-[100]" style={{ opacity: 0, animationDelay: '0.4s' }}>
                <button
                  onClick={handleGenerate}
                  className="w-full md:w-auto group relative z-[100] inline-flex items-center justify-center gap-2 px-8 py-4 text-[14px] font-bold text-white bg-[#FF9F45] rounded-[12px] overflow-hidden shadow-[0_4px_12px_rgba(255,159,69,0.2)] hover:bg-[#FF8C1A] hover:shadow-[0_4px_16px_rgba(255,159,69,0.3)] hover:-translate-y-[1px] active:translate-y-[1px] transition-all duration-200 cursor-pointer pointer-events-auto"
                >
                  <Sparkles size={18} className="animate-pulse pointer-events-none" />
                  <span className="pointer-events-none">进入故事创作流程</span>
                  <ChevronRight size={18} className="group-hover:translate-x-[2px] transition-transform duration-200 pointer-events-none" />
                </button>
                <p className="text-[12px] text-[#999] mt-3 animate-fade-up" style={{ opacity: 0, animationDelay: '0.5s' }}>
                  先生成故事与评审结果，再进入绘画设定与插画生成
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
