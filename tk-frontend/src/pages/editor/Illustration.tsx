import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Loader2, RefreshCw, Sparkles, Wand2, Users, CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react';
import { fetchApi, joinApiUrl } from '../../lib/api';

type Scene = {
  scene_id: number;
  text_chunk?: string;
  summary?: string;
  image_prompt?: string;
  image_url?: string;
  character_consistency_score?: number;
  character_consistency_status?: 'consistent' | 'minor_diff' | 'inconsistent';
};

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

function resolveImageCount(formData: any) {
  const count = Number(formData?.imageCount);
  if (!Number.isFinite(count)) return 3;
  return Math.max(1, Math.min(10, count));
}

function getCharacterConsistencyIcon(status?: string) {
  switch (status) {
    case 'consistent':
      return <CheckCircle2 size={14} className="text-green-500" />;
    case 'minor_diff':
      return <AlertTriangle size={14} className="text-yellow-500" />;
    case 'inconsistent':
      return <AlertCircle size={14} className="text-red-500" />;
    default:
      return <Users size={14} className="text-gray-400" />;
  }
}

function getCharacterConsistencyLabel(status?: string) {
  switch (status) {
    case 'consistent': return '人物一致';
    case 'minor_diff': return '轻微差异';
    case 'inconsistent': return '不一致';
    default: return '待检测';
  }
}

function getCharacterConsistencyColor(status?: string) {
  switch (status) {
    case 'consistent': return 'bg-green-50 text-green-700 border-green-200';
    case 'minor_diff': return 'bg-yellow-50 text-yellow-700 border-yellow-200';
    case 'inconsistent': return 'bg-red-50 text-red-700 border-red-200';
    default: return 'bg-gray-50 text-gray-600 border-gray-200';
  }
}

export default function Illustration() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state || {}) as any;
  const storyData = state?.storyData;
  const formData = state?.formData || {};

  const artStyle = useMemo(() => resolveArtStyle(formData), [formData]);
  const imageCount = useMemo(() => resolveImageCount(formData), [formData]);
  const extraDrawReq = formData?.extraDrawReq || '';
  const characterConfig = useMemo((): CharacterConfig | undefined => formData?.characterConfig, [formData]);

  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState('');
  const [scenes, setScenes] = useState<Scene[]>(state?.illustrations || []);
  const [revisionInputs, setRevisionInputs] = useState<Record<number, string>>({});
  const [regeneratingIds, setRegeneratingIds] = useState<Record<number, boolean>>({});

  const generateIllustrations = useCallback(async () => {
    if (!storyData?.id || !storyData?.content) return;

    setIsGenerating(true);
    setError('');
    try {
      const requestBody: any = {
        story_id: storyData.id,
        content: storyData.content,
        image_count: imageCount,
        art_style: artStyle,
        extra_requirements: extraDrawReq,
      };

      // 如果有人物配置，传递给后端
      if (characterConfig) {
        requestBody.character_config = characterConfig;
      }

      const response = await fetchApi('/api/illustrator/suggest', {
        method: 'POST',
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();
      if (data.code !== 200) {
        throw new Error(data.msg || '插画生成失败');
      }

      const sceneList = Array.isArray(data?.data?.scenes) ? data.data.scenes : [];
      setScenes(sceneList);

      navigate(location.pathname, {
        replace: true,
        state: {
          ...(state || {}),
          illustrations: sceneList,
        },
      });
    } catch (err: any) {
      setError(err.message || '插画生成失败，请检查后端服务或图片模型配置');
    } finally {
      setIsGenerating(false);
    }
  }, [storyData, imageCount, artStyle, extraDrawReq, characterConfig, location.pathname, navigate, state]);

  const regenerateOne = useCallback(async (scene: Scene) => {
    const feedback = (revisionInputs[scene.scene_id] || '').trim();
    if (!feedback) return;

    setRegeneratingIds(prev => ({ ...prev, [scene.scene_id]: true }));
    setError('');
    try {
      const requestBody: any = {
        story_id: storyData.id,
        scene_id: scene.scene_id,
        image_prompt: scene.image_prompt || '',
        feedback,
        art_style: artStyle,
        extra_requirements: extraDrawReq,
      };

      // 如果有人物配置，传递给后端
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
      const nextScenes = scenes.map(item => {
        if (item.scene_id !== scene.scene_id) return item;
        return {
          ...item,
          image_url: updated.image_url || item.image_url,
          image_prompt: updated.image_prompt || item.image_prompt,
          character_consistency_score: updated.character_consistency_score,
          character_consistency_status: updated.character_consistency_status,
        };
      });

      setScenes(nextScenes);
      setRevisionInputs(prev => ({ ...prev, [scene.scene_id]: '' }));

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
      setRegeneratingIds(prev => ({ ...prev, [scene.scene_id]: false }));
    }
  }, [storyData, scenes, artStyle, extraDrawReq, characterConfig, revisionInputs, location.pathname, navigate, state]);

  useEffect(() => {
    if (scenes.length > 0) return;
    if (!storyData?.id || !storyData?.content) return;
    generateIllustrations();
  }, []);

  if (!storyData?.id || !storyData?.content) {
    return (
      <div className="bg-white rounded-xl shadow-[0_2px_10px_rgba(0,0,0,0.06)] border border-gray-100 p-6 min-h-[500px]">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">6.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">插画</h3>
            <p className="text-sm text-gray-500">需要先完成前序步骤，再生成分镜插画。</p>
          </div>
        </div>
        <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[320px] bg-gray-50/50 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-500 mb-4">暂未检测到故事正文，请先完成前面步骤。</p>
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
      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-500 font-bold">6.</div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">插画</h3>
            <p className="text-sm text-gray-500">按分镜生成图片，可逐张输入修改意见并重绘。</p>
          </div>
        </div>

        <button
          onClick={generateIllustrations}
          disabled={isGenerating}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-orange-200 text-[#FF9F45] bg-orange-50 hover:bg-orange-100 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          {isGenerating ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
          重新生成全部
        </button>
      </div>

      <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 min-h-[350px] bg-gray-50/50">
        {isGenerating ? (
          <div className="flex flex-col items-center justify-center min-h-[260px] text-gray-400 gap-3">
            <Loader2 className="animate-spin text-[#FF9F45]" size={36} />
            <p>绘画师 Agent 正在拆分分镜并调用火山模型生图，请稍候...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center min-h-[260px] text-red-400 gap-3">
            <p>{error}</p>
            <button
              onClick={generateIllustrations}
              className="px-4 py-2 mt-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition"
            >
              重试
            </button>
          </div>
        ) : scenes.length > 0 ? (
          <div className="space-y-6">
            {scenes.map(scene => (
              <div key={scene.scene_id} className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-base font-bold text-gray-900 inline-flex items-center gap-2">
                    <Sparkles size={16} className="text-[#FF9F45]" />
                    分镜 {scene.scene_id}
                  </h4>
                  {characterConfig && (
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-xs font-semibold ${getCharacterConsistencyColor(scene.character_consistency_status)}`}>
                      {getCharacterConsistencyIcon(scene.character_consistency_status)}
                      {getCharacterConsistencyLabel(scene.character_consistency_status)}
                      {typeof scene.character_consistency_score === 'number' && (
                        <span className="ml-1">({scene.character_consistency_score}%)</span>
                      )}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div>
                    <div className="rounded-lg overflow-hidden border border-gray-200 bg-gray-100 min-h-[260px] flex items-center justify-center">
                      {scene.image_url ? (
                        <img src={scene.image_url} alt={`scene-${scene.scene_id}`} className="w-full h-full object-cover" />
                      ) : (
                        <div className="text-gray-400 text-sm inline-flex items-center gap-2">
                          <Loader2 size={16} className="animate-spin" />
                          图片生成中...
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">画面摘要</p>
                      <p className="text-sm text-gray-800 leading-7">{scene.summary || '暂无摘要'}</p>
                    </div>

                    <div>
                      <p className="text-xs text-gray-500 mb-1">当前提示词</p>
                      <p className="text-sm text-gray-700 leading-7 bg-gray-50 border border-gray-200 rounded-md p-2 max-h-[120px] overflow-auto">
                        {scene.image_prompt || '暂无提示词'}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs text-gray-500 mb-1">修改意见</p>
                      <textarea
                        value={revisionInputs[scene.scene_id] || ''}
                        onChange={(e) => setRevisionInputs(prev => ({ ...prev, [scene.scene_id]: e.target.value }))}
                        placeholder="例如：主角表情更开心、背景改为傍晚、色调更柔和..."
                        className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all shadow-sm resize-none h-24"
                      />
                    </div>

                    <button
                      onClick={() => regenerateOne(scene)}
                      disabled={regeneratingIds[scene.scene_id] || !(revisionInputs[scene.scene_id] || '').trim()}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#FF9F45] text-white hover:bg-[#FF8C1A] disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                    >
                      {regeneratingIds[scene.scene_id] ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
                      按意见重绘
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center min-h-[260px] text-gray-400">等待插画生成结果...</div>
        )}
      </div>
    </div>
  );
}
