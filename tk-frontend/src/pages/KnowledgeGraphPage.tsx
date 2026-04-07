import { ArrowLeft, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import KnowledgeGraph from './editor/KnowledgeGraph';

export default function KnowledgeGraphPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#FAFAF5] py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-[1380px] mx-auto">
        <button
          onClick={() => navigate('/profile')}
          className="mb-6 inline-flex items-center gap-2 text-sm text-gray-600 hover:text-[#FF9F45]"
        >
          <ArrowLeft size={16} />
          返回个人主页
        </button>

        <div className="mb-4 rounded-2xl border border-orange-100 bg-white p-5 shadow-[0_6px_18px_rgba(0,0,0,0.05)]">
          <h1 className="inline-flex items-center gap-2 text-2xl font-black text-gray-900">
            <Sparkles size={20} className="text-[#FF9F45]" />
            知识图谱中心
          </h1>
          <p className="mt-2 text-sm text-gray-600">在这里可独立完成图谱抽取、检索与可视化分析。</p>
        </div>

        <KnowledgeGraph />
      </div>
    </div>
  );
}
