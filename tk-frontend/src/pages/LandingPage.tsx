import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, ArrowRight, BookOpen, Palette, Rocket, Loader2, Globe, Bot, Microscope, Atom } from 'lucide-react';
import { getCurrentUsername, logout } from '../lib/auth';

const QUOTES = [
  "好奇心造就科学家和诗人—— 法朗士",
  "科学并不是专家的事业，是每个人都可以做的。—— 阿西莫夫",
  "传播知识就是播种幸福。—— 诺贝尔"
];

export default function LandingPage() {
  const navigate = useNavigate();
  const [quote, setQuote] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [username, setUsername] = useState('');

  useEffect(() => {
    // 随机选择一句名言
    const randomIndex = Math.floor(Math.random() * QUOTES.length);
    setQuote(QUOTES[randomIndex]);
    setUsername(getCurrentUsername());
  }, []);

  const handleStart = () => {
    setIsLoading(true);
    // 模拟加载延时增强反馈，然后跳转
    setTimeout(() => {
      navigate('/creation');
    }, 600);
  };

  const handleLogout = async () => {
    if (isLoggingOut) return;
    setIsLoggingOut(true);
    await logout();
    navigate('/', { replace: true });
  };

  return (
    <div className="min-h-screen bg-[#FDFBF7] flex items-center justify-center relative overflow-hidden font-sans">
      <div className="absolute top-4 right-4 z-[220] flex items-center gap-3 rounded-2xl border border-orange-100 bg-white/80 px-3 py-2 backdrop-blur">
        <span className="text-xs text-gray-600 max-w-[120px] truncate">{username || '当前账号'}</span>
        <button
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="inline-flex items-center rounded-lg border border-orange-200 bg-orange-50 px-3 py-1.5 text-xs font-semibold text-[#B75A00] hover:bg-orange-100 disabled:opacity-60"
        >
          {isLoggingOut ? '退出中...' : '退出登录'}
        </button>
      </div>

      {/* 渐变过渡：中心极淡的米白色柔光，突出中间 */}
      <div className="absolute inset-0 bg-gradient-to-b from-white/40 via-transparent to-white/20 pointer-events-none z-0" />
      
      {/* 动态柔和渐变背景装饰球 */}
      <div className="absolute top-[-10%] left-[-5%] w-[40vw] h-[40vw] bg-orange-200/40 rounded-full blur-[100px] pointer-events-none mix-blend-multiply" />
      <div className="absolute bottom-[-10%] right-[-5%] w-[50vw] h-[50vw] bg-blue-200/40 rounded-full blur-[120px] pointer-events-none mix-blend-multiply" />
      <div className="absolute top-[20%] right-[10%] w-[25vw] h-[25vw] bg-yellow-200/40 rounded-full blur-[80px] pointer-events-none mix-blend-multiply" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60vw] h-[60vw] bg-[#FFFBF0]/60 rounded-full blur-[120px] pointer-events-none z-0" />
      
      {/* 极低透明度的科普元素装饰 */}
      <div className="absolute top-[10%] left-[10%] text-slate-800 opacity-[0.08] animate-float-slow pointer-events-none">
        <Globe size={180} strokeWidth={1} />
      </div>
      <div className="absolute top-[15%] right-[15%] text-slate-800 opacity-[0.06] animate-float-slower pointer-events-none">
        <Microscope size={150} strokeWidth={1} />
      </div>
      <div className="absolute bottom-[45%] left-[5%] text-slate-800 opacity-[0.07] animate-float-slowest pointer-events-none">
        <Atom size={170} strokeWidth={1} />
      </div>
      <div className="absolute bottom-[10%] right-[10%] text-slate-800 opacity-[0.08] animate-float-slower pointer-events-none">
        <BookOpen size={160} strokeWidth={1} />
      </div>
      <div className="absolute bottom-[20%] left-[15%] text-slate-800 opacity-[0.08] animate-float-slowest pointer-events-none">
        <Bot size={140} strokeWidth={1} />
      </div>

      {/* 拟物/毛玻璃效果悬浮小图标 (增加童趣与设计感) */}
      <div className="absolute hidden md:flex top-[20%] left-[25%] w-16 h-16 bg-white/60 backdrop-blur-md rounded-2xl shadow-xl border border-white/50 rotate-12 items-center justify-center text-orange-400 animate-breathe hover:rotate-[22deg] transition-transform duration-300 z-10 pointer-events-none">
        <Palette size={28} />
      </div>
      <div className="absolute hidden md:flex bottom-[25%] left-[20%] w-20 h-20 bg-white/60 backdrop-blur-md rounded-full shadow-lg border border-white/50 -rotate-6 items-center justify-center text-blue-400 animate-breathe hover:rotate-[4deg] transition-transform duration-300 z-10 pointer-events-none" style={{ animationDelay: '1s' }}>
        <BookOpen size={32} />
      </div>
      <div className="absolute hidden md:flex top-[30%] right-[20%] w-14 h-14 bg-white/60 backdrop-blur-md rounded-xl shadow-xl border border-white/50 rotate-45 items-center justify-center text-rose-400 animate-breathe hover:rotate-[55deg] transition-transform duration-300 z-10 pointer-events-none" style={{ animationDelay: '0.5s' }}>
        <Rocket size={24} />
      </div>

      <div className="relative z-[100] flex flex-col items-center text-center px-4 max-w-4xl mx-auto w-full">
        {/* 顶部小标签 */}
        <div className="animate-fade-in-up-1 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/80 backdrop-blur border border-orange-100 shadow-sm text-orange-600 text-sm font-medium mb-8">
          <Sparkles size={16} />
          <span>全新多 Agent 协作科普绘本平台</span>
        </div>

        {/* 主标题 */}
        <h1 className="animate-fade-in-up-2 text-7xl md:text-9xl mb-6 tracking-wide drop-shadow-sm flex items-center justify-center gap-2" style={{ fontFamily: 'var(--font-zcool)' }}>
          <span className="text-transparent bg-clip-text bg-gradient-to-br from-amber-300 to-orange-500 hover:scale-110 hover:-rotate-6 transition-transform duration-300">童</span>
          <span className="text-transparent bg-clip-text bg-gradient-to-b from-amber-300 to-orange-500 hover:scale-110 hover:rotate-3 transition-transform duration-300 -translate-y-2">科</span>
          <span className="text-transparent bg-clip-text bg-gradient-to-bl from-amber-300 to-orange-500 hover:scale-110 hover:rotate-6 transition-transform duration-300">绘</span>
        </h1>
        
        {/* 随机名言展示区 */}
        <div className="animate-fade-in-up-3 mb-8 w-full px-4">
          <p className="text-[18px] md:text-[22px] font-bold text-slate-800 tracking-wide">
            {quote}
          </p>
        </div>

        {/* 副标题描述 */}
        <p className="animate-fade-in-up-4 text-lg md:text-2xl text-slate-600 mb-12 max-w-2xl leading-relaxed text-balance">
          点燃孩子们的好奇心！在这里，利用 AI 轻松将深奥的科学知识转化为生动有趣、图文并茂的启蒙绘本。
        </p>

        {/* 核心操作按钮 */}
        <div className="animate-fade-in-up-5 relative z-[200]">
          <button
            onClick={handleStart}
            disabled={isLoading}
            className="group relative z-[200] inline-flex w-[190px] items-center justify-center gap-3 px-8 py-4 text-lg font-bold text-white bg-gradient-to-r from-[#FF9F45] to-[#FF8C1A] rounded-[20px] overflow-hidden shadow-[0_0_15px_rgba(255,159,69,0.4)] hover:shadow-[0_0_25px_rgba(255,159,69,0.6)] hover:-translate-y-[2px] active:translate-y-[1px] active:shadow-[0_0_10px_rgba(255,159,69,0.3)] transition-all duration-300 disabled:opacity-80 disabled:cursor-not-allowed disabled:hover:translate-y-0 cursor-pointer pointer-events-auto"
          >
            <span className="absolute inset-0 w-full h-full -mr-px bg-[#FF8C1A] opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></span>
            <span className="relative flex items-center gap-2 pointer-events-none">
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  生成中...
                </>
              ) : (
                <>
                  开始创作
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </span>
          </button>

          <div className="mt-6 flex flex-col gap-4 items-center">
            <button
              onClick={() => navigate('/profile')}
              className="group relative z-[200] inline-flex w-[190px] items-center justify-center gap-3 px-8 py-4 text-lg font-bold text-white bg-gradient-to-r from-[#FF9F45] to-[#FF8C1A] rounded-[20px] overflow-hidden shadow-[0_0_15px_rgba(255,159,69,0.4)] hover:shadow-[0_0_25px_rgba(255,159,69,0.6)] hover:-translate-y-[2px] active:translate-y-[1px] active:shadow-[0_0_10px_rgba(255,159,69,0.3)] transition-all duration-300 cursor-pointer pointer-events-auto"
            >
              <span className="absolute inset-0 w-full h-full -mr-px bg-[#FF8C1A] opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></span>
              <span className="relative flex items-center gap-2 pointer-events-none">
                个人主页
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
