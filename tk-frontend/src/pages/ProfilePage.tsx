import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, UserRound, BookMarked, Save, LayoutDashboard, Settings, Eye, PlusCircle, Clock3, Layers3, FileCheck2, Trash2, Bot } from 'lucide-react';
import { deleteWorkRecord, loadProfile, loadWorks, saveProfile, type WorkRecord } from '../lib/workHistory';
import apiClient, { type LLMProviderOption } from '../lib/api-client';

function formatTime(ts: number) {
  return new Date(ts).toLocaleString('zh-CN', {
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getWorkCover(work: WorkRecord) {
  const latest = work.versions[0];
  const illustrations = Array.isArray(latest?.state?.illustrations) ? latest.state.illustrations : [];
  const withImage = illustrations.find((item: any) => item?.image_url);
  return withImage?.image_url || '';
}

export default function ProfilePage() {
  const navigate = useNavigate();

  const initialProfile = loadProfile();
  const [avatar, setAvatar] = useState(initialProfile.avatar);
  const [nickname, setNickname] = useState(initialProfile.nickname);
  const [bio, setBio] = useState(initialProfile.bio);
  const [saveTip, setSaveTip] = useState('');
  const [llmSaveTip, setLlmSaveTip] = useState('');
  const [textLlmProvider, setTextLlmProvider] = useState<'qwen' | 'volcengine' | 'hunyuan' | 'deepseek' | 'wenxin'>('qwen');
  const [textLlmApiKey, setTextLlmApiKey] = useState('');
  const [textLlmApiKeyMasked, setTextLlmApiKeyMasked] = useState('');
  const [imageLlmProvider, setImageLlmProvider] = useState<'volcengine' | 'qwen'>('volcengine');
  const [imageLlmApiKey, setImageLlmApiKey] = useState('');
  const [imageLlmApiKeyMasked, setImageLlmApiKeyMasked] = useState('');
  const [llmOptions, setLlmOptions] = useState<LLMProviderOption[]>([]);
  const [isSavingLlmConfig, setIsSavingLlmConfig] = useState(false);

  const [works, setWorks] = useState<WorkRecord[]>(loadWorks());
  const [visibleCount, setVisibleCount] = useState(4);
  const [isMultiSelectMode, setIsMultiSelectMode] = useState(false);
  const [selectedWorkIds, setSelectedWorkIds] = useState<string[]>([]);

  useEffect(() => {
    let canceled = false;

    const loadLlmConfig = async () => {
      try {
        const [options, current] = await Promise.all([
          apiClient.getLlmProviders(),
          apiClient.getCurrentLlmConfig(),
        ]);
        if (canceled) return;

        setLlmOptions(options);
        const supported = ['qwen', 'volcengine', 'hunyuan', 'deepseek', 'wenxin'];
        const provider = supported.includes(current.text?.provider || current.provider)
          ? ((current.text?.provider || current.provider) as 'qwen' | 'volcengine' | 'hunyuan' | 'deepseek' | 'wenxin')
          : 'qwen';
        setTextLlmProvider(provider);
        setTextLlmApiKeyMasked(current.text?.api_key_masked || current.api_key_masked || '');

        const imageProviderRaw = String(current.image?.provider || 'volcengine').trim().toLowerCase();
        const imageProvider = imageProviderRaw === 'qwen' ? 'qwen' : 'volcengine';
        setImageLlmProvider(imageProvider);
        setImageLlmApiKeyMasked(current.image?.api_key_masked || current.api_key_masked || '');
      } catch {
        if (!canceled) {
          setLlmSaveTip('加载LLM配置失败，请检查后端是否启动');
        }
      } finally {
        if (!canceled) {
          // no-op
        }
      }
    };

    loadLlmConfig();
    return () => {
      canceled = true;
    };
  }, []);

  const stats = useMemo(() => {
    const versionCount = works.reduce((sum, item) => sum + item.versions.length, 0);
    const exportedCount = works.filter((item) =>
      item.versions.some((version) => version.state?.publisherData?.pdfUrl),
    ).length;
    const latestUpdatedAt = works[0]?.updatedAt || 0;

    return {
      workCount: works.length,
      versionCount,
      exportedCount,
      latestUpdatedAt,
    };
  }, [works]);

  const visibleWorks = useMemo(() => works.slice(0, visibleCount), [works, visibleCount]);
  const hasMoreWorks = works.length > visibleCount;

  const selectedCount = selectedWorkIds.length;
  const allSelected = works.length > 0 && selectedCount === works.length;

  useEffect(() => {
    setSelectedWorkIds((prev) => prev.filter((id) => works.some((work) => work.id === id)));
  }, [works]);

  const saveUserProfile = () => {
    saveProfile({
      avatar: avatar.trim() || '🧪',
      nickname: nickname.trim() || '童科绘创作者',
      bio: bio.trim() || '热爱科普与创作，持续记录灵感与版本。',
    });
    setSaveTip('已保存');
    setTimeout(() => setSaveTip(''), 1200);
  };

  const saveLlmConfig = async () => {
    try {
      setIsSavingLlmConfig(true);
      const next = await apiClient.updateLlmConfig({
        text_provider: textLlmProvider,
        text_api_key: textLlmApiKey.trim() || undefined,
        image_provider: imageLlmProvider,
        image_api_key: imageLlmApiKey.trim() || undefined,
      });
      setTextLlmApiKey('');
      setImageLlmApiKey('');
      setTextLlmApiKeyMasked(next.text?.api_key_masked || next.api_key_masked || '');
      setImageLlmApiKeyMasked(next.image?.api_key_masked || next.api_key_masked || '');
      setLlmSaveTip('LLM配置已保存');
      setTimeout(() => setLlmSaveTip(''), 1500);
    } catch (err: any) {
      setLlmSaveTip(err?.message || '保存LLM配置失败');
    } finally {
      setIsSavingLlmConfig(false);
    }
  };

  const refreshWorks = () => {
    const next = loadWorks();
    setWorks(next);
    setVisibleCount(4);
  };

  const openWork = (work: WorkRecord) => {
    const latest = work.versions[0];
    if (!latest) return;
    const targetPath = typeof latest.path === 'string' && latest.path.startsWith('/editor/')
      ? latest.path
      : '/editor/draft';
    const nextState = latest.state && typeof latest.state === 'object' ? latest.state : {};
    navigate(targetPath, { state: nextState });
  };

  const deleteWork = (work: WorkRecord) => {
    const confirmed = window.confirm(`确认删除《${work.title}》吗？删除后无法恢复。`);
    if (!confirmed) return;
    deleteWorkRecord(work.id);
    refreshWorks();
  };

  const toggleWorkSelection = (workId: string) => {
    setSelectedWorkIds((prev) =>
      prev.includes(workId) ? prev.filter((id) => id !== workId) : [...prev, workId],
    );
  };

  const toggleSelectAllWorks = () => {
    if (allSelected) {
      setSelectedWorkIds([]);
      return;
    }
    setSelectedWorkIds(works.map((work) => work.id));
  };

  const clearSelection = () => {
    setSelectedWorkIds([]);
  };

  const exitMultiSelectMode = () => {
    setIsMultiSelectMode(false);
    clearSelection();
  };

  const deleteSelectedWorks = () => {
    if (selectedWorkIds.length === 0) return;
    const confirmed = window.confirm(`确认批量删除 ${selectedWorkIds.length} 个作品吗？删除后无法恢复。`);
    if (!confirmed) return;

    selectedWorkIds.forEach((id) => deleteWorkRecord(id));
    setSelectedWorkIds([]);
    refreshWorks();
  };

  const expandWorks = () => {
    setVisibleCount((prev) => Math.min(prev + 4, works.length));
  };

  return (
    <div className="min-h-screen bg-[#FAFAF5] py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-[1380px] mx-auto">
        <button
          onClick={() => navigate('/')}
          className="mb-6 inline-flex items-center gap-2 text-sm text-gray-600 hover:text-[#FF9F45]"
        >
          <ArrowLeft size={16} />
          返回主页
        </button>

        <div className="grid grid-cols-1 xl:grid-cols-[1fr,280px] gap-6 items-start">

          <section className="space-y-6">
            <div className="rounded-2xl border border-orange-100 bg-white p-5 shadow-[0_6px_18px_rgba(0,0,0,0.05)]">
              <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                <div className="h-20 w-20 rounded-2xl bg-gradient-to-br from-[#FFE0BA] to-[#FFD7A3] border border-orange-200 text-4xl flex items-center justify-center shadow-inner">
                  {avatar || '🧪'}
                </div>
                <div className="flex-1">
                  <h2 className="text-2xl font-black text-gray-900 inline-flex items-center gap-2">
                    <UserRound size={20} className="text-[#FF9F45]" />
                    {nickname || '童科绘创作者'}
                  </h2>
                  <p className="mt-2 text-sm text-gray-600 leading-7">{bio || '热爱科普与创作，持续记录灵感与版本。'}</p>
                </div>
              </div>
            </div>

            <section className="rounded-2xl border border-orange-100 bg-white p-4 shadow-[0_6px_18px_rgba(0,0,0,0.05)]">
              <h3 className="text-sm font-extrabold text-[#B75A00] mb-3">快捷操作</h3>
              <div className="space-y-2">
                <button
                  onClick={() => navigate('/creation')}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#FF9F45] px-4 py-3 text-sm font-bold text-white hover:bg-[#FF8C1A]"
                >
                  <PlusCircle size={16} />
                  新建绘本
                </button>
                <button
                  onClick={() => navigate('/knowledge-graph')}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#FF9F45] px-4 py-3 text-sm font-bold text-white hover:bg-[#FF8C1A]"
                >
                  <Bot size={16} />
                  知识图谱中心
                </button>
              </div>
            </section>

            <div className="rounded-2xl border border-orange-100 bg-white p-5 shadow-[0_6px_18px_rgba(0,0,0,0.05)]">
              <div className="mb-4 flex items-center justify-between gap-3">
                <h3 className="text-lg font-extrabold text-gray-900 inline-flex items-center gap-2">
                  <BookMarked size={18} className="text-[#FF9F45]" />
                  我的作品画廊
                </h3>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsMultiSelectMode((prev) => !prev)}
                    className="text-sm rounded-lg border border-orange-200 px-3 py-1.5 text-[#B75A00] hover:bg-orange-50"
                  >
                    {isMultiSelectMode ? '退出多选' : '多选管理'}
                  </button>
                  <button
                    onClick={refreshWorks}
                    className="text-sm rounded-lg border border-gray-200 px-3 py-1.5 text-gray-600 hover:text-[#FF9F45]"
                  >
                    刷新列表
                  </button>
                </div>
              </div>

              {works.length > 0 && isMultiSelectMode ? (
                <div className="mb-4 rounded-xl border border-orange-100 bg-orange-50/60 px-3 py-2 flex flex-wrap items-center gap-3">
                  <label className="inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={toggleSelectAllWorks}
                      className="h-4 w-4 rounded border-gray-300 text-[#FF9F45] focus:ring-orange-200"
                    />
                    全选
                  </label>
                  <span className="text-xs text-gray-600">已选 {selectedCount} / {works.length}</span>
                  <button
                    onClick={clearSelection}
                    className="text-xs rounded-lg border border-gray-200 bg-white px-2.5 py-1 text-gray-600 hover:text-[#FF9F45] disabled:opacity-50"
                    disabled={selectedCount === 0}
                  >
                    清空选择
                  </button>
                  <button
                    onClick={exitMultiSelectMode}
                    className="text-xs rounded-lg border border-gray-200 bg-white px-2.5 py-1 text-gray-600 hover:text-[#FF9F45]"
                  >
                    完成
                  </button>
                  <button
                    onClick={deleteSelectedWorks}
                    className="inline-flex items-center gap-1 text-xs rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 font-semibold text-red-700 hover:bg-red-100 disabled:opacity-50"
                    disabled={selectedCount === 0}
                  >
                    <Trash2 size={13} />
                    批量删除
                  </button>
                </div>
              ) : null}

              {works.length === 0 ? (
                <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-6 text-sm text-gray-500">
                  你还没有历史作品。先去开始创作，系统会自动保存每一步版本。
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {visibleWorks.map((work) => {
                    const cover = getWorkCover(work);
                    const isSelected = selectedWorkIds.includes(work.id);
                    return (
                      <article
                        key={work.id}
                        className={`relative rounded-2xl border overflow-hidden transition-all hover:border-orange-200 ${isSelected ? 'border-orange-300 ring-2 ring-orange-200/70' : 'border-gray-200'}`}
                      >
                        {isMultiSelectMode ? (
                          <label className="absolute left-3 top-3 z-10 inline-flex items-center gap-2 rounded-lg bg-white/90 px-2 py-1 text-xs font-semibold text-gray-700 shadow-sm cursor-pointer">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleWorkSelection(work.id)}
                              className="h-4 w-4 rounded border-gray-300 text-[#FF9F45] focus:ring-orange-200"
                            />
                            选择
                          </label>
                        ) : null}

                        {cover ? (
                          <img src={cover} alt={work.title} className="h-36 w-full object-cover" />
                        ) : (
                          <div className="h-36 w-full bg-gradient-to-br from-[#FFE7C7] via-[#FFF2DF] to-[#F1F8FF] flex items-center justify-center text-[#B75A00] font-bold">
                            科普绘本
                          </div>
                        )}

                        <div className="p-4">
                          <p className="text-base font-extrabold text-gray-900 line-clamp-2">{work.title}</p>
                          {work.versions[0]?.storyVersion ? (
                            <p className="text-xs text-[#B75A00] mt-1 font-semibold">版本号：{work.versions[0].storyVersion}</p>
                          ) : null}
                          <p className="text-xs text-gray-500 mt-1">生成时间：{formatTime(work.createdAt)}</p>
                          <p className="text-xs text-gray-500">最近更新：{formatTime(work.updatedAt)}</p>

                          <div className="mt-3 flex items-center justify-between gap-2">
                            <button
                              onClick={() => openWork(work)}
                              className="inline-flex items-center gap-1 rounded-lg border border-orange-200 bg-orange-50 px-3 py-1.5 text-xs font-semibold text-[#B75A00] hover:bg-orange-100"
                            >
                              <Eye size={14} />
                              查看
                            </button>
                            <button
                              onClick={() => deleteWork(work)}
                              className="inline-flex items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100"
                            >
                              <Trash2 size={14} />
                              删除
                            </button>
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}

              {works.length > 0 ? (
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-xs text-gray-500">
                    已展示 {Math.min(visibleCount, works.length)} / {works.length} 幅作品
                  </p>
                  {hasMoreWorks ? (
                    <button
                      onClick={expandWorks}
                      className="inline-flex items-center gap-1 rounded-lg border border-orange-200 bg-orange-50 px-3 py-1.5 text-xs font-semibold text-[#B75A00] hover:bg-orange-100"
                    >
                      展开更多（+4）
                    </button>
                  ) : null}
                </div>
              ) : null}
            </div>

            <div className="rounded-2xl border border-orange-100 bg-white p-5 shadow-[0_6px_18px_rgba(0,0,0,0.05)]">
              <h3 className="text-lg font-extrabold text-gray-900 mb-4 inline-flex items-center gap-2">
                <Settings size={18} className="text-[#FF9F45]" />
                设置
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className="block">
                  <span className="mb-1 block text-sm text-gray-600">头像（可用 Emoji）</span>
                  <input
                    value={avatar}
                    onChange={(e) => setAvatar(e.target.value)}
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-200"
                    placeholder="例如 🧪"
                  />
                </label>

                <label className="block">
                  <span className="mb-1 block text-sm text-gray-600">昵称</span>
                  <input
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    className="w-full rounded-xl border border-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-200"
                    placeholder="输入昵称"
                  />
                </label>
              </div>

              <label className="block mt-4">
                <span className="mb-1 block text-sm text-gray-600">个人签名（简介）</span>
                <textarea
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  rows={3}
                  className="w-full rounded-xl border border-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-200"
                  placeholder="说点什么..."
                />
              </label>

              <div className="mt-4 flex items-center gap-3">
                <button
                  onClick={saveUserProfile}
                  className="inline-flex items-center gap-2 rounded-xl bg-[#FF9F45] px-4 py-2 text-white font-semibold hover:bg-[#FF8C1A]"
                >
                  <Save size={16} />
                  保存资料
                </button>
                {saveTip ? <p className="text-xs text-emerald-600">{saveTip}</p> : null}
              </div>

              <div className="mt-6 border-t border-orange-100 pt-5">
                <h4 className="text-base font-bold text-gray-800 mb-3">我的 LLM 配置</h4>

                <div className="rounded-xl border border-orange-100 bg-[#FFF8EE] p-4">
                  <p className="mb-3 text-sm font-bold text-[#B75A00]">文本部分</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <label className="block">
                      <span className="mb-1 block text-sm text-gray-600">文本模型供应商</span>
                      <select
                        value={textLlmProvider}
                        onChange={(e) => setTextLlmProvider(e.target.value as 'qwen' | 'volcengine' | 'hunyuan' | 'deepseek' | 'wenxin')}
                        className="w-full rounded-xl border border-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-200"
                      >
                        {(llmOptions.length > 0 ? llmOptions : [
                          { provider: 'qwen', label: '通义千问', base_url: '', default_model: '', default_vision_model: '' },
                          { provider: 'volcengine', label: '火山引擎', base_url: '', default_model: '', default_vision_model: '' },
                          { provider: 'hunyuan', label: '腾讯混元', base_url: '', default_model: '', default_vision_model: '' },
                          { provider: 'deepseek', label: 'DeepSeek', base_url: '', default_model: '', default_vision_model: '' },
                          { provider: 'wenxin', label: '百度文心', base_url: '', default_model: '', default_vision_model: '' },
                        ]).map((opt) => (
                          <option key={opt.provider} value={opt.provider}>{opt.label}</option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="mb-1 block text-sm text-gray-600">文本 API Key</span>
                      <input
                        type="password"
                        value={textLlmApiKey}
                        onChange={(e) => setTextLlmApiKey(e.target.value)}
                        className="w-full rounded-xl border border-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-200"
                        placeholder={textLlmApiKeyMasked ? `已配置：${textLlmApiKeyMasked}` : '请输入文本 API Key'}
                      />
                    </label>
                  </div>
                </div>

                <div className="mt-4 rounded-xl border border-orange-100 bg-[#FFF8EE] p-4">
                  <p className="mb-3 text-sm font-bold text-[#B75A00]">绘画部分</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <label className="block">
                      <span className="mb-1 block text-sm text-gray-600">绘画模型供应商</span>
                      <select
                        value={imageLlmProvider}
                        onChange={(e) => setImageLlmProvider(e.target.value as 'volcengine' | 'qwen')}
                        className="w-full rounded-xl border border-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-200"
                      >
                        <option value="volcengine">火山引擎</option>
                        <option value="qwen">通义万相</option>
                      </select>
                    </label>

                    <label className="block">
                      <span className="mb-1 block text-sm text-gray-600">绘画 API Key</span>
                      <input
                        type="password"
                        value={imageLlmApiKey}
                        onChange={(e) => setImageLlmApiKey(e.target.value)}
                        className="w-full rounded-xl border border-gray-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-200"
                        placeholder={imageLlmApiKeyMasked ? `已配置：${imageLlmApiKeyMasked}` : '请输入绘画 API Key'}
                      />
                    </label>
                  </div>
                </div>

                <div className="mt-3 flex items-center gap-3">
                  <button
                    onClick={saveLlmConfig}
                    className="inline-flex items-center gap-2 rounded-xl bg-[#FF9F45] px-4 py-2 text-white font-semibold hover:bg-[#FF8C1A] disabled:opacity-60"
                    disabled={isSavingLlmConfig}
                  >
                    <Save size={16} />
                    {isSavingLlmConfig ? '保存中...' : '保存LLM配置'}
                  </button>
                  <p className="text-xs text-gray-500">默认会回填当前文本/绘画配置的 API Key 掩码</p>
                </div>
                {llmSaveTip ? <p className="mt-2 text-xs text-emerald-600">{llmSaveTip}</p> : null}
              </div>
            </div>
          </section>

          <aside className="xl:sticky xl:top-6 space-y-4">
            <section className="rounded-2xl border border-orange-100 bg-white p-4 shadow-[0_6px_18px_rgba(0,0,0,0.05)]">
              <h3 className="text-sm font-extrabold text-[#B75A00] mb-3 inline-flex items-center gap-2">
                <LayoutDashboard size={15} />
                数据看板
              </h3>

              <div className="space-y-2">
                <div className="rounded-xl border border-orange-100 bg-[#FFF8EE] p-3">
                  <p className="text-xs text-gray-500 inline-flex items-center gap-1"><BookMarked size={13} />作品数量</p>
                  <p className="text-2xl font-black text-gray-900">{stats.workCount}</p>
                </div>
                <div className="rounded-xl border border-orange-100 bg-[#FFF8EE] p-3">
                  <p className="text-xs text-gray-500 inline-flex items-center gap-1"><Layers3 size={13} />版本快照</p>
                  <p className="text-2xl font-black text-gray-900">{stats.versionCount}</p>
                </div>
                <div className="rounded-xl border border-orange-100 bg-[#FFF8EE] p-3">
                  <p className="text-xs text-gray-500 inline-flex items-center gap-1"><FileCheck2 size={13} />导出PDF作品</p>
                  <p className="text-2xl font-black text-gray-900">{stats.exportedCount}</p>
                </div>
                <div className="rounded-xl border border-orange-100 bg-[#FFF8EE] p-3">
                  <p className="text-xs text-gray-500 inline-flex items-center gap-1"><Clock3 size={13} />最近更新</p>
                  <p className="text-xs font-semibold text-gray-800 mt-1">
                    {stats.latestUpdatedAt ? formatTime(stats.latestUpdatedAt) : '暂无记录'}
                  </p>
                </div>
              </div>
            </section>

          </aside>
        </div>
      </div>
    </div>
  );
}
