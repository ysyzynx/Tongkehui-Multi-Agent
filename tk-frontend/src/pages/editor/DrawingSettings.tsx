import { useCallback, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Check, Image as ImageIcon, Palette } from 'lucide-react';

const ART_STYLES = [
  { id: '1', label: '卡通风格', desc: '色彩鲜艳明快' },
  { id: '2', label: '儿童绘画', desc: '稚气纯真童趣' },
  { id: '3', label: '水彩画', desc: '柔和高级艺术感' },
  { id: '4', label: '写真', desc: '写实逼真质感' },
  { id: '5', label: '3D渲染', desc: '立体现代科技感' },
];

export default function DrawingSettings() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state || {}) as any;

  const formData = useMemo(() => {
    const source = state.formData || {};
    return {
      ...source,
      artStyle: source.artStyle || '1',
      imageCount: Number.isFinite(Number(source.imageCount))
        ? Math.max(1, Math.min(10, Number(source.imageCount)))
        : 3,
      extraDrawReq: source.extraDrawReq || '',
    };
  }, [state.formData]);

  const updateFormData = useCallback((patch: Record<string, any>) => {
    navigate(location.pathname, {
      replace: true,
      state: {
        ...state,
        formData: {
          ...formData,
          ...patch,
        },
      },
    });
  }, [location.pathname, navigate, state, formData]);


  if (!state?.storyData?.id || !state?.storyData?.content) {
    return (
      <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.06)] border border-gray-100 p-6 min-h-[500px]">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">5.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">绘画设定</h3>
            <p className="text-sm text-gray-500">请先完成前序步骤，再进行绘画风格和分镜数量设定。</p>
          </div>
        </div>

        <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[320px] bg-gray-50/50 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-500 mb-4">尚未检测到可用于分镜的故事正文。</p>
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
        <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">5.</div>
        <div>
          <h3 className="text-xl font-bold text-gray-900">绘画设定</h3>
          <p className="text-sm text-gray-500">在读者反馈后选择画风、插画数量与绘制偏好，再进入插画生成。</p>
        </div>
      </div>

      <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[350px] bg-gray-50/50">
        <div className="bg-white rounded-[12px] border border-[#E5E7EB] p-5">
          <h4 className="text-base font-bold text-gray-800 mb-5 inline-flex items-center gap-2">
            <Palette size={16} className="text-[#FF9F45]" />
            插画与分镜设定
          </h4>

          <div className="mb-6">
            <label className="text-[14px] font-medium text-gray-700 mb-3 block">期望画风</label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {ART_STYLES.map(style => {
                const isSelected = formData.artStyle === style.id;
                return (
                  <button
                    key={style.id}
                    onClick={() => updateFormData({ artStyle: style.id })}
                    className={"group relative px-3 py-2.5 rounded-[12px] border transition-all duration-200 text-left hover:-translate-y-[1px] hover:shadow-[0_4px_12px_rgba(255,159,69,0.1)] " + (
                      isSelected
                        ? 'bg-[#FF9F45] border-[#FF9F45] text-white'
                        : 'bg-white border-[#E5E7EB] text-gray-600 hover:border-[#FF9F45] hover:text-[#FF9F45]'
                    )}
                  >
                    <div className="text-[14px] font-semibold">{style.label}</div>
                    <div className={"text-[12px] mt-0.5 " + (isSelected ? 'text-white/90' : 'text-gray-400')}>{style.desc}</div>
                    {isSelected ? (
                      <div className="absolute top-1/2 -translate-y-1/2 right-2 text-[#FF9F45] bg-white rounded-full p-0.5 shadow-sm">
                        <Check size={12} strokeWidth={3} />
                      </div>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mb-6">
            <label className="text-[14px] font-medium text-gray-700 mb-3 block inline-flex items-center gap-2">
              <ImageIcon size={14} className="text-[#FF9F45]" />
              分镜插画张数
            </label>
            <div className="flex items-center gap-4 bg-white p-2 rounded-[12px] border border-[#E5E7EB] w-fit hover:border-[#FF9F45] transition-colors duration-200">
              <button
                onClick={() => updateFormData({ imageCount: Math.max(1, formData.imageCount - 1) })}
                className="w-8 h-8 rounded-[12px] flex items-center justify-center text-[#FF9F45] hover:bg-[#FF9F45]/10 transition-colors duration-200"
              >
                -
              </button>
              <div className="w-8 text-center font-bold text-[14px] text-gray-800">{formData.imageCount}</div>
              <button
                onClick={() => updateFormData({ imageCount: Math.min(10, formData.imageCount + 1) })}
                className="w-8 h-8 rounded-[12px] flex items-center justify-center text-[#FF9F45] hover:bg-[#FF9F45]/10 transition-colors duration-200"
              >
                +
              </button>
            </div>
          </div>

          <div>
            <label className="text-[14px] font-medium text-gray-700 mb-3 block">自定义绘画要求 (可选)</label>
            <textarea
              value={formData.extraDrawReq}
              onChange={(e) => updateFormData({ extraDrawReq: e.target.value })}
              placeholder="例如：画面色调偏暖，主角保持统一服饰，背景加入实验室元素..."
              className="w-full bg-white rounded-[12px] border border-[#E5E7EB] px-4 py-3 text-[14px] text-gray-800 placeholder:text-[#999] focus:outline-none focus:border-[#FF9F45] focus:ring-1 focus:ring-[#FF9F45] hover:border-[#FF9F45] transition-all duration-200 resize-none h-28"
            />
          </div>
        </div>

      </div>
    </div>
  );
}
