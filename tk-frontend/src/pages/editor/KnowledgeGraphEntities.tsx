import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Loader2, Pencil, Save, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  ENTITY_TYPE_ZH,
  type EntityType,
  type KnowledgeGraphEntity,
  listEntities,
  updateEntity,
} from '../../lib/kg-api';

const PAGE_SIZE = 10;

export default function KnowledgeGraphEntities() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [tip, setTip] = useState('');
  const [keyword, setKeyword] = useState('');
  const [entityType, setEntityType] = useState<EntityType | ''>('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [entities, setEntities] = useState<KnowledgeGraphEntity[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draftName, setDraftName] = useState('');
  const [draftDescription, setDraftDescription] = useState('');
  const [draftType, setDraftType] = useState<EntityType>('CONCEPT');

  const entityTypeOptions = useMemo(() => {
    return Object.keys(ENTITY_TYPE_ZH) as EntityType[];
  }, []);

  async function loadEntities() {
    setLoading(true);
    setError('');
    try {
      const result = await listEntities({
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
        entity_type: entityType || undefined,
        keyword: keyword.trim() || undefined,
      });
      setEntities(result.results || []);
      setTotal(result.total || 0);
      setTip(`已加载 ${result.results?.length || 0} 条实体记录`);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载实体失败');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEntities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, entityType]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const startEdit = (entity: KnowledgeGraphEntity) => {
    setEditingId(entity.id);
    setDraftName(entity.name || '');
    setDraftDescription(entity.description || '');
    setDraftType(entity.entity_type);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setDraftName('');
    setDraftDescription('');
  };

  const saveEdit = async (entityId: number) => {
    if (!draftName.trim()) {
      setError('实体名称不能为空');
      return;
    }
    setSavingId(entityId);
    setError('');
    try {
      const updated = await updateEntity(entityId, {
        name: draftName.trim(),
        entity_type: draftType,
        description: draftDescription.trim(),
      });
      setEntities((prev) => prev.map((item) => (item.id === entityId ? { ...item, ...updated } : item)));
      setTip(`实体“${updated.name}”已更新`);
      cancelEdit();
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败');
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#FFF1E6] py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-[1200px] mx-auto">
        <button
          onClick={() => navigate('/knowledge-graph')}
          className="mb-6 inline-flex items-center gap-2 text-sm text-gray-600 hover:text-[#FF9F45]"
        >
          <ArrowLeft size={16} />
          返回知识图谱
        </button>

        <div className="rounded-2xl border border-orange-100 bg-white p-5 md:p-6 shadow-[0_12px_34px_-28px_rgba(15,23,42,0.35)]">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-[24px] font-bold text-gray-900">本地实体详情管理</h2>
              <p className="mt-1 text-sm text-gray-500">查看本地已有实体，并直接编辑名称、类型与描述。</p>
            </div>
          </div>

          {error ? <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}
          {tip && !error ? <div className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{tip}</div> : null}

          <div className="mb-4 grid gap-2 md:grid-cols-[1fr_180px_120px]">
            <input
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setPage(1);
                  loadEntities();
                }
              }}
              className="h-11 rounded-xl border border-gray-300 px-3 text-sm outline-none focus:border-orange-400"
              placeholder="输入实体名关键词"
            />
            <select
              value={entityType}
              onChange={(e) => {
                setEntityType((e.target.value || '') as EntityType | '');
                setPage(1);
              }}
              className="h-11 rounded-xl border border-gray-300 px-3 text-sm outline-none focus:border-orange-400"
            >
              <option value="">全部类型</option>
              {entityTypeOptions.map((type) => (
                <option key={type} value={type}>
                  {ENTITY_TYPE_ZH[type] || type}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => {
                setPage(1);
                loadEntities();
              }}
              className="h-11 rounded-xl bg-orange-500 px-4 text-sm font-semibold text-white hover:bg-orange-600"
            >
              查询
            </button>
          </div>

          <div className="space-y-3">
            {loading ? (
              <div className="py-10 text-center text-gray-500 inline-flex items-center gap-2">
                <Loader2 size={16} className="animate-spin" /> 加载中...
              </div>
            ) : entities.length === 0 ? (
              <div className="py-10 text-center text-gray-400">暂无实体数据</div>
            ) : (
              entities.map((entity) => {
                const isEditing = editingId === entity.id;
                return (
                  <div key={entity.id} className="rounded-xl border border-gray-200 bg-[#FFFEFC] p-4">
                    {!isEditing ? (
                      <>
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <h3 className="text-base font-bold text-gray-900">{entity.name}</h3>
                            <span className="rounded-full border border-orange-200 bg-orange-50 px-2 py-0.5 text-xs text-[#B75A00]">
                              {ENTITY_TYPE_ZH[entity.entity_type] || entity.entity_type}
                            </span>
                          </div>
                          <button
                            onClick={() => startEdit(entity)}
                            className="inline-flex items-center gap-1 rounded-md border border-orange-200 bg-white px-2.5 py-1 text-xs font-semibold text-[#B75A00] hover:bg-orange-50"
                          >
                            <Pencil size={13} /> 编辑
                          </button>
                        </div>
                        <p className="mt-2 text-sm leading-7 text-gray-600">{entity.description || '暂无描述'}</p>
                      </>
                    ) : (
                      <div className="space-y-3">
                        <input
                          value={draftName}
                          onChange={(e) => setDraftName(e.target.value)}
                          className="h-10 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-orange-400"
                          placeholder="实体名称"
                        />
                        <select
                          value={draftType}
                          onChange={(e) => setDraftType(e.target.value as EntityType)}
                          className="h-10 w-full rounded-lg border border-gray-300 px-3 text-sm outline-none focus:border-orange-400"
                        >
                          {entityTypeOptions.map((type) => (
                            <option key={type} value={type}>
                              {ENTITY_TYPE_ZH[type] || type}
                            </option>
                          ))}
                        </select>
                        <textarea
                          value={draftDescription}
                          onChange={(e) => setDraftDescription(e.target.value)}
                          className="min-h-[110px] w-full rounded-lg border border-gray-300 px-3 py-2 text-sm leading-7 outline-none focus:border-orange-400"
                          placeholder="实体描述"
                        />
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={cancelEdit}
                            className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-50"
                          >
                            <X size={13} /> 取消
                          </button>
                          <button
                            onClick={() => saveEdit(entity.id)}
                            disabled={savingId === entity.id}
                            className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 disabled:opacity-60"
                          >
                            {savingId === entity.id ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} 保存
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          <div className="mt-4 flex items-center justify-between">
            <div className="text-xs text-gray-500">共 {total} 条记录</div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600 disabled:opacity-50"
              >
                上一页
              </button>
              <span className="text-xs text-gray-500">第 {page} / {totalPages} 页</span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600 disabled:opacity-50"
              >
                下一页
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
