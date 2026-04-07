import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Atom, BookOpen, Bot, Globe, Loader2, Microscope, Palette, Rocket, Sparkles } from 'lucide-react';
import { isLoggedIn, login, registerAndLogin } from '../lib/auth';

export default function AuthPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isLoggedIn()) {
      navigate('/home', { replace: true });
    }
  }, [navigate]);

  const submit = async () => {
    if (loading) return;
    setLoading(true);
    setError('');

    const result = mode === 'register'
      ? await registerAndLogin(username, password)
      : await login(username, password);

    if (!result.ok) {
      setError(result.message || '操作失败');
      setLoading(false);
      return;
    }

    setTimeout(() => {
      navigate('/home', { replace: true });
    }, 350);
  };

  return (
    <div className="min-h-screen bg-[#FDFBF7] flex items-center justify-center relative overflow-hidden font-sans">
      <div className="absolute inset-0 bg-gradient-to-b from-white/40 via-transparent to-white/20 pointer-events-none z-0" />
      <div className="absolute top-[-10%] left-[-5%] w-[40vw] h-[40vw] bg-orange-200/40 rounded-full blur-[100px] pointer-events-none mix-blend-multiply" />
      <div className="absolute bottom-[-10%] right-[-5%] w-[50vw] h-[50vw] bg-blue-200/40 rounded-full blur-[120px] pointer-events-none mix-blend-multiply" />
      <div className="absolute top-[20%] right-[10%] w-[25vw] h-[25vw] bg-yellow-200/40 rounded-full blur-[80px] pointer-events-none mix-blend-multiply" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60vw] h-[60vw] bg-[#FFFBF0]/60 rounded-full blur-[120px] pointer-events-none z-0" />

      <div className="absolute top-[10%] left-[10%] text-slate-800 opacity-[0.08] pointer-events-none"><Globe size={180} strokeWidth={1} /></div>
      <div className="absolute top-[15%] right-[15%] text-slate-800 opacity-[0.06] pointer-events-none"><Microscope size={150} strokeWidth={1} /></div>
      <div className="absolute bottom-[45%] left-[5%] text-slate-800 opacity-[0.07] pointer-events-none"><Atom size={170} strokeWidth={1} /></div>
      <div className="absolute bottom-[10%] right-[10%] text-slate-800 opacity-[0.08] pointer-events-none"><BookOpen size={160} strokeWidth={1} /></div>
      <div className="absolute bottom-[20%] left-[15%] text-slate-800 opacity-[0.08] pointer-events-none"><Bot size={140} strokeWidth={1} /></div>
      <div className="absolute hidden md:flex top-[20%] left-[25%] w-16 h-16 bg-white/60 backdrop-blur-md rounded-2xl shadow-xl border border-white/50 rotate-12 items-center justify-center text-orange-400 z-10 pointer-events-none"><Palette size={28} /></div>
      <div className="absolute hidden md:flex top-[30%] right-[20%] w-14 h-14 bg-white/60 backdrop-blur-md rounded-xl shadow-xl border border-white/50 rotate-45 items-center justify-center text-rose-400 z-10 pointer-events-none"><Rocket size={24} /></div>

      <div className="relative z-[100] w-full max-w-md px-6">
        <div className="rounded-3xl border border-orange-100/90 bg-white/75 backdrop-blur-lg shadow-[0_18px_40px_rgba(0,0,0,0.08)] p-7">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-orange-100 text-orange-600 text-sm font-medium mb-6">
            <Sparkles size={14} />
            {mode === 'login' ? '欢迎回来' : '创建你的童科绘账号'}
          </div>

          <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-300 to-orange-500 mb-5" style={{ fontFamily: 'var(--font-zcool)' }}>
            童科绘
          </h1>

          <div className="space-y-3">
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入账号"
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-200"
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-200"
            />
          </div>

          {error ? <p className="text-sm text-red-500 mt-3">{error}</p> : null}

          <button
            onClick={submit}
            disabled={loading}
            className="mt-5 w-full inline-flex items-center justify-center gap-2 px-6 py-3 text-lg font-bold text-white bg-gradient-to-r from-[#FF9F45] to-[#FF8C1A] rounded-2xl shadow-[0_0_15px_rgba(255,159,69,0.35)] hover:-translate-y-[1px] transition-all disabled:opacity-70"
          >
            {loading ? <Loader2 size={18} className="animate-spin" /> : null}
            {mode === 'login' ? '登录' : '注册'}
            {!loading ? <ArrowRight size={18} /> : null}
          </button>

          <p className="mt-4 text-sm text-gray-600 text-center">
            {mode === 'login' ? '还没有账号？' : '已有账号？'}
            <button
              type="button"
              onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
              className="ml-2 text-orange-500 font-semibold hover:text-orange-600"
            >
              {mode === 'login' ? '去注册' : '去登录'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
