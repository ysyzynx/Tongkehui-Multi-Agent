import { useState, useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from "react-router-dom"
import { ArrowLeft, Menu, Sparkles, ChevronRight, ChevronLeft, Network } from "lucide-react"
import { saveWorkSnapshot } from '../lib/workHistory'

// 轻量级样式合并工具
function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ")
}

// 工作流阶段（内部真实步骤，供上下步导航与状态计算）
const WORKFLOW_TABS = [
  { id: 1, title: "故事草稿", path: "/editor/draft", status: "创作中" },
  { id: 2, title: "文学家审查", path: "/editor/literature-review", status: "文学审查中" },
  { id: 3, title: "科学家审查", path: "/editor/science-review", status: "科学审查中" },
  { id: 4, title: "观众反馈", path: "/editor/reader-feedback", status: "反馈分析中" },
  { id: 5, title: "绘画设定", path: "/editor/drawing-settings", status: "绘画设定中" },
  { id: 6, title: "插画", path: "/editor/illustration", status: "插画生成中" },
  { id: 7, title: "插画审核", path: "/editor/illustration-review", status: "插画审核中" },
  { id: 8, title: "排版", path: "/editor/layout", status: "排版中" },
]

// 顶部展示阶段（将三类审查合并为一个大模块，绘画设定+插画合并为插画）
const HEADER_TABS = [
  { id: 1, title: "故事草稿", path: "/editor/draft", workflowIndexes: [0] },
  { id: 2, title: "审查模块", path: "/editor/literature-review", workflowIndexes: [1, 2, 3] },
  { id: 3, title: "插画", path: "/editor/drawing-settings", workflowIndexes: [4, 5] },
  { id: 4, title: "插画审核", path: "/editor/illustration-review", workflowIndexes: [6] },
  { id: 5, title: "排版", path: "/editor/layout", workflowIndexes: [7] },
]

function resolveTabIndex(pathname: string) {
  const exactIndex = WORKFLOW_TABS.findIndex(tab => pathname === tab.path);
  if (exactIndex >= 0) {
    return exactIndex;
  }

  // Fallback: match the longest tab path prefix to avoid "illustration" swallowing "illustration-review".
  const matched = WORKFLOW_TABS
    .map((tab, idx) => ({ idx, matched: pathname.startsWith(tab.path), len: tab.path.length }))
    .filter(item => item.matched)
    .sort((a, b) => b.len - a.len);

  return matched.length > 0 ? matched[0].idx : 0;
}

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [maxReached, setMaxReached] = useState(0);

  // Parse state from CreationPage
  const state = (location.state || {}) as any;
  const navState = location.state && typeof location.state === 'object' ? location.state : {};
  const formData = state?.formData || {};
  
  // Define metadata fallbacks
  const theme = formData.theme || '物理热学'; // Default if none
  const storyTitle = state?.storyTitle || state?.storyData?.title;
  const title = storyTitle || `关于“${theme}”的奇妙探索`;
  const articleStyle = formData.articleStyle || '图文并茂形';
  
  // Mapping Age Group ID to text
  const audMap: Record<string, string> = {
    '1': '👦 青少幼年儿童',
    '2': '👷 产业工人',
    '3': '🧓 老年人',
    '4': '💼 领导干部',
    '5': '🌾 农民',
  };
  
  const subAudMap: Record<string, string> = {
    '1_1': '👶 3-6岁',
    '1_2': '👦 6-12岁',
    '1_3': '🧑 12-28岁'
  };

  // 如果是一般受众就直接显示，如果是儿童则显示具体的年龄段
  let ageGroup = "👦 8-12岁";
  if (formData.targetAudience === '1' && formData.subAudience) {
    ageGroup = subAudMap[formData.subAudience] || ageGroup;
  } else if (formData.targetAudience) {
    ageGroup = audMap[formData.targetAudience] || ageGroup;
  }
  const desc = formData.extraStoryReq || '结合有趣的设定，科普相应的原理，解释为什么会发生这种现象，通过生活细节观察其中变化的关系。';

  const currentPath = location.pathname;
  const currentIndex = resolveTabIndex(currentPath);

  useEffect(() => {
    const currentState = location.state && typeof location.state === 'object' ? location.state : null;
    if (!currentPath.startsWith('/editor')) return;
    if (!currentState) return;
    saveWorkSnapshot(currentPath, currentState);
  }, [currentPath, location.state]);
  
  useEffect(() => {
    if (currentIndex > maxReached) {
      setMaxReached(currentIndex);
    }
  }, [currentIndex, maxReached]);

  const currentTab = WORKFLOW_TABS[currentIndex] || WORKFLOW_TABS[0];

  const handleNextStep = () => {
    if (currentIndex < WORKFLOW_TABS.length - 1) {
      const nextTab = WORKFLOW_TABS[currentIndex + 1];
      navigate(nextTab.path, { state: navState });
    }
  };

  const handlePrevStep = () => {
    if (currentIndex > 0) {
      const prevTab = WORKFLOW_TABS[currentIndex - 1];
      navigate(prevTab.path, { state: navState });
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAF5] text-gray-800 font-sans flex flex-col">
      {/* 顶部导航 Header */}
      <header className="h-[60px] bg-white border-b border-[#E5E7EB] flex items-center justify-between px-6 sticky top-0 z-50 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-[10px] bg-[#FF9F45] flex items-center justify-center text-white">
            <Sparkles size={16} fill="currentColor" />
          </div>
          <h1 className="text-xl font-bold text-gray-800 tracking-wide">童科绘</h1>
        </div>
        <button className="text-gray-500 hover:text-[#FF9F45] p-2 rounded-md hover:bg-orange-50 transition-colors">
          <Menu size={24} />
        </button>
      </header>

      {/* 主体内容区域 */}
      <main className="flex-1 w-full max-w-5xl mx-auto px-4 py-6 md:py-8 lg:px-8">
        
        {/* 返回列表按钮 */}
        <button
          onClick={() => navigate('/creation')}
          className="flex items-center gap-2 text-[14px] text-gray-500 hover:text-[#FF9F45] mb-6 font-medium transition-colors"
        >
          <ArrowLeft size={16} />
          返回项目列表
        </button>

        {/* 项目基本信息 Header */}
        <div className="mb-6">
          <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-[28px] font-bold text-gray-900 leading-tight">{title}</h2>
              <span className="px-2.5 py-0.5 rounded-md bg-orange-50 text-[#FF9F45] text-xs font-semibold border border-orange-200">
                {currentTab.status}
              </span>
            </div>
            <button
              onClick={() => navigate('/knowledge-graph', {
                state: {
                  returnTo: currentPath,
                  returnLabel: `返回${currentTab.title}`,
                  returnState: navState,
                },
              })}
              className="inline-flex items-center gap-2 rounded-xl border border-orange-200 bg-orange-50 px-4 py-2 text-sm font-semibold text-[#FF9F45] hover:bg-orange-100 transition-colors"
            >
              <Network size={16} />
              知识图谱中心
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[14px] text-gray-500 mt-2">
            <span>主题：{theme}</span>
            <span className="flex items-center gap-1.5">
              类型：<span className="w-4 h-4 bg-orange-200 border border-orange-300 rounded overflow-hidden relative inline-block">
                <span className="absolute top-0 right-0 w-0 h-0 border-l-[16px] border-l-transparent border-t-[16px] border-t-[#FF9F45]"></span>
              </span> {articleStyle}
            </span>
            <span>年龄段：{ageGroup}</span>
          </div>
          <p className="text-[14px] text-gray-500 mt-4 leading-relaxed max-w-4xl">
            {desc}
          </p>
        </div>

        {/* 横向 Tab 栏 (工作流进度) */}
        <div className="flex overflow-x-auto no-scrollbar border-b border-gray-200 mb-6 relative">
          {HEADER_TABS.map((tab) => {
            const maxIdx = Math.max(...tab.workflowIndexes);
            const isActive = tab.workflowIndexes.includes(currentIndex);
            const isCompleted = maxIdx <= maxReached;
            
            return (
              <button
                key={tab.id}
                onClick={() => {
                  if (isCompleted) {
                    navigate(tab.path, { state: navState });
                  }
                }}
                className={cn(
                  "px-6 py-3.5 text-[14px] font-medium transition-colors whitespace-nowrap relative outline-none flex items-center gap-2",
                  isActive
                    ? "text-gray-900"
                    : (isCompleted 
                        ? "text-gray-600 hover:text-[#FF9F45]" 
                        : "text-gray-400 cursor-not-allowed opacity-60")
                )}
                disabled={!isCompleted}
              >
                {tab.title}
                {isActive && (
                  <div className="absolute bottom-0 left-0 w-full h-[3px] bg-[#FF9F45] rounded-t-sm" />
                )}
              </button>
            );
          })}
        </div>

        {/* 动态内容渲染区域 (带圆角的白色卡片) */}
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <Outlet />
        </div>

        {/* 底部按钮区域 */}
        {currentIndex > 0 || currentIndex < WORKFLOW_TABS.length - 1 ? (
          <div className="mt-8 flex items-center justify-between">
            {currentIndex > 0 ? (
              <button
                onClick={handlePrevStep}
                className="group flex items-center gap-2 px-6 py-3 bg-[#FF9F45] text-white rounded-[12px] font-bold text-[14px] shadow-[0_4px_12px_rgba(255,159,69,0.2)] hover:bg-[#FF8C1A] hover:shadow-[0_4px_16px_rgba(255,159,69,0.3)] transition-all hover:-translate-y-[1px] active:translate-y-[1px]"
              >
                <ChevronLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                上一步
              </button>
            ) : (
              <div />
            )}

            {currentIndex < WORKFLOW_TABS.length - 1 ? (
              <button
                onClick={handleNextStep}
                className="group flex items-center gap-2 px-6 py-3 bg-[#FF9F45] text-white rounded-[12px] font-bold text-[14px] shadow-[0_4px_12px_rgba(255,159,69,0.2)] hover:bg-[#FF8C1A] hover:shadow-[0_4px_16px_rgba(255,159,69,0.3)] transition-all hover:-translate-y-[1px] active:translate-y-[1px]"
              >
                下一步
                <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
              </button>
            ) : (
              <div />
            )}
          </div>
        ) : null}

      </main>
    </div>
  )
}
