type StoredProfile = {
  avatar: string;
  nickname: string;
  bio: string;
};

import { getCurrentUsername } from './auth';

export type WorkVersion = {
  id: string;
  path: string;
  stepLabel: string;
  storyVersion?: string;
  savedAt: number;
  state: any;
  summary: string;
};

export type WorkRecord = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  versions: WorkVersion[];
};

const PROFILE_KEY = 'tk_profile';
const WORKS_KEY = 'tk_works';
const MAX_WORK_RECORDS = 40;
const MAX_VERSIONS_PER_WORK = 60;
const MAX_STORY_CONTENT_CHARS = 60000;
const MAX_TEXT_CHUNK_CHARS = 6000;

const STEP_LABELS: Record<string, string> = {
  '/editor/draft': '故事草稿',
  '/editor/literature-review': '文学家审查',
  '/editor/science-review': '科学家审查',
  '/editor/reader-feedback': '观众反馈',
  '/editor/drawing-settings': '绘画设定',
  '/editor/illustration': '插画生成',
  '/editor/illustration-review': '插画审核',
  '/editor/layout': '排版',
};

const VERSION_BUMP_PATHS = new Set([
  '/editor/draft',
  '/editor/literature-review',
  '/editor/science-review',
  '/editor/reader-feedback',
  '/editor/layout',
]);

const DEFAULT_PROFILE: StoredProfile = {
  avatar: '🧪',
  nickname: '童科绘创作者',
  bio: '热爱科普与创作，持续记录灵感与版本。',
};

function safeRead<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function safeWrite<T>(key: string, value: T): boolean {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (err) {
    console.warn(`[workHistory] 保存失败: ${key}`, err);
    return false;
  }
}

function normalizeScope(value: string): string {
  const raw = String(value || '').trim().toLowerCase();
  if (!raw) return 'guest';
  return raw.replace(/[^a-z0-9_\-\.]/g, '_');
}

function getUserScopedKey(baseKey: string): string {
  const username = getCurrentUsername();
  const scope = normalizeScope(username);
  return `${baseKey}:${scope}`;
}

function safeReadScoped<T>(baseKey: string, fallback: T): T {
  const scopedKey = getUserScopedKey(baseKey);
  const scopedVal = safeRead<T | null>(scopedKey, null);
  if (scopedVal !== null) return scopedVal;

  // 一次性兼容迁移：把旧全局数据迁到当前账号下，避免升级后历史丢失。
  const legacyVal = safeRead<T | null>(baseKey, null);
  if (legacyVal !== null) {
    safeWrite(scopedKey, legacyVal);
    try {
      localStorage.removeItem(baseKey);
    } catch {
      // ignore
    }
    return legacyVal;
  }

  return fallback;
}

function safeWriteScoped<T>(baseKey: string, value: T): boolean {
  return safeWrite(getUserScopedKey(baseKey), value);
}

function compactText(value: any, maxLength: number): string {
  const text = String(value || '');
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}\n...（内容已截断，仅用于本地历史快照）`;
}

function compactSnapshotState(raw: any): any {
  if (!raw || typeof raw !== 'object') return {};

  const state = { ...raw };

  if (state.formData && typeof state.formData === 'object') {
    const formData = { ...state.formData };
    if (formData.characterConfig && typeof formData.characterConfig === 'object') {
      const characterConfig = { ...formData.characterConfig };
      if (typeof characterConfig.referenceImage === 'string' && characterConfig.referenceImage.startsWith('data:image')) {
        delete characterConfig.referenceImage;
      }
      formData.characterConfig = characterConfig;
    }
    state.formData = formData;
  }

  if (state.storyData && typeof state.storyData === 'object') {
    state.storyData = {
      ...state.storyData,
      content: compactText(state.storyData.content, MAX_STORY_CONTENT_CHARS),
    };
  }

  if (Array.isArray(state.illustrations)) {
    state.illustrations = state.illustrations.slice(0, 12).map((item: any) => ({
      scene_id: item?.scene_id,
      summary: item?.summary,
      image_prompt: item?.image_prompt,
      image_url: item?.image_url,
      text_chunk: compactText(item?.text_chunk, MAX_TEXT_CHUNK_CHARS),
      character_consistency_score: item?.character_consistency_score,
      character_consistency_status: item?.character_consistency_status,
    }));
  }

  if (state.publisherData && typeof state.publisherData === 'object') {
    state.publisherData = {
      pdfUrl: state.publisherData.pdfUrl || '',
    };
  }

  return state;
}

function normalizeWorksForStorage(works: WorkRecord[]): WorkRecord[] {
  return [...works]
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, MAX_WORK_RECORDS)
    .map((work) => ({
      ...work,
      versions: (Array.isArray(work.versions) ? work.versions : [])
        .slice(0, MAX_VERSIONS_PER_WORK)
        .map((version) => ({
          ...version,
          state: compactSnapshotState(version.state),
        })),
    }));
}

function persistWorksWithFallback(works: WorkRecord[]) {
  let candidate = normalizeWorksForStorage(works);
  if (safeWriteScoped(WORKS_KEY, candidate)) return;

  // 超限时逐步裁剪：先删旧版本，再删最旧作品，确保不再抛异常导致白屏。
  while (candidate.length > 0) {
    let trimmed = false;

    for (let i = candidate.length - 1; i >= 0; i -= 1) {
      const versions = candidate[i].versions || [];
      if (versions.length > 1) {
        candidate[i] = {
          ...candidate[i],
          versions: versions.slice(0, versions.length - 1),
        };
        trimmed = true;
        break;
      }
    }

    if (!trimmed) {
      candidate = candidate.slice(0, candidate.length - 1);
    }

    if (safeWriteScoped(WORKS_KEY, candidate)) {
      return;
    }
  }
}

function buildWorkId(state: any): string {
  const sessionId = String(state?.workSessionId || '').trim();
  if (sessionId) return `session:${sessionId}`;

  const storyId = state?.storyData?.id;
  if (storyId !== undefined && storyId !== null && String(storyId).trim()) {
    return `story:${String(storyId)}`;
  }

  const seed = String(state?.formData?.projectTitle || state?.formData?.theme || Date.now()).trim();
  return `fallback:${seed}`;
}

function resolveTitle(state: any): string {
  const title = String(state?.storyData?.title || state?.storyTitle || state?.formData?.projectTitle || state?.formData?.theme || '未命名作品').trim();
  return title || '未命名作品';
}

function buildSummary(path: string, state: any): string {
  const chunks: string[] = [];
  if (state?.literatureData) chunks.push('文学审查');
  if (state?.scienceData) chunks.push('科学审查');
  if (state?.readerData) chunks.push('读者反馈');
  if (Array.isArray(state?.illustrations) && state.illustrations.length > 0) chunks.push(`插画${state.illustrations.length}张`);
  if (state?.publisherData?.pdfUrl) chunks.push('已导出PDF');

  const stepLabel = STEP_LABELS[path] || '编辑中';
  return chunks.length > 0 ? `${stepLabel} · ${chunks.join(' · ')}` : `${stepLabel} · 已保存快照`;
}

function resolveModelLabel(state: any): string {
  const explicit = String(state?.storyData?.llm_provider_label || '').trim();
  if (explicit) return explicit;

  const provider = String(state?.storyData?.llm_provider || '').trim().toLowerCase();
  const labelMap: Record<string, string> = {
    qwen: '通义千问',
    volcengine: '火山引擎',
    hunyuan: '腾讯混元',
    deepseek: 'DeepSeek',
    wenxin: '百度文心',
  };
  return labelMap[provider] || '通义千问';
}

export function getModelVersionBadge(path: string, state: any): string {
  const modelLabel = resolveModelLabel(state);
  const stageVersionMap: Record<string, string> = {
    '/editor/draft': '1.0',
    '/editor/literature-review': '2.0',
    '/editor/science-review': '3.0',
    '/editor/reader-feedback': '4.0',
    '/editor/layout': '5.0',
  };
  const version = stageVersionMap[path] || '1.0';
  return `${modelLabel}-${version}`;
}

function buildStoryVersion(modelLabel: string, existingVersions: WorkVersion[]): string {
  const regex = /^(.+)\+(\d+)\.0$/;
  let maxVersion = 0;
  for (const item of existingVersions) {
    const raw = String(item?.storyVersion || '').trim();
    const m = regex.exec(raw);
    if (!m) continue;
    const label = m[1];
    const versionNum = Number(m[2]);
    if (label === modelLabel && Number.isFinite(versionNum)) {
      maxVersion = Math.max(maxVersion, versionNum);
    }
  }
  return `${modelLabel}+${maxVersion + 1}.0`;
}

function resolveLatestStoryVersion(existingVersions: WorkVersion[]): string {
  for (const item of existingVersions) {
    const raw = String(item?.storyVersion || '').trim();
    if (raw) return raw;
  }
  return '';
}

export function loadProfile(): StoredProfile {
  return safeReadScoped<StoredProfile>(PROFILE_KEY, DEFAULT_PROFILE);
}

export function saveProfile(profile: StoredProfile) {
  safeWriteScoped(PROFILE_KEY, profile);
}

export function loadWorks(): WorkRecord[] {
  const list = safeReadScoped<WorkRecord[]>(WORKS_KEY, []);
  return [...list].sort((a, b) => b.updatedAt - a.updatedAt);
}

export function getCurrentWorkVersion(state: any): string {
  if (!state) return '';
  const all = loadWorks();
  const workId = buildWorkId(state);
  const matched = all.find((item) => item.id === workId);
  return String(matched?.versions?.[0]?.storyVersion || '').trim();
}

export function saveWorkSnapshot(path: string, state: any) {
  if (!state || (!state.formData && !state.storyData)) return;

  const compactState = compactSnapshotState(state);

  const all = loadWorks();
  const now = Date.now();
  const workId = buildWorkId(compactState);
  const title = resolveTitle(compactState);
  const stepLabel = STEP_LABELS[path] || '编辑中';
  const index = all.findIndex((item) => item.id === workId);
  const existingVersions = index >= 0 ? all[index].versions : [];
  const modelLabel = resolveModelLabel(compactState);
  const shouldBumpVersion = VERSION_BUMP_PATHS.has(path);
  const latestStoryVersion = resolveLatestStoryVersion(existingVersions);
  const storyVersion = shouldBumpVersion
    ? buildStoryVersion(modelLabel, existingVersions)
    : (latestStoryVersion || buildStoryVersion(modelLabel, existingVersions));

  const nextVersion: WorkVersion = {
    id: `v_${now}_${Math.random().toString(36).slice(2, 8)}`,
    path,
    stepLabel,
    storyVersion,
    savedAt: now,
    state: compactState,
    summary: buildSummary(path, compactState),
  };

  if (index < 0) {
    const created: WorkRecord = {
      id: workId,
      title,
      createdAt: now,
      updatedAt: now,
      versions: [nextVersion],
    };
    persistWorksWithFallback([created, ...all]);
    return;
  }

  const existing = all[index];
  const latest = existing.versions[0];

  if (latest && latest.path === path && JSON.stringify(latest.state) === JSON.stringify(compactState)) {
    return;
  }

  const updated: WorkRecord = {
    ...existing,
    title,
    updatedAt: now,
    versions: [nextVersion, ...existing.versions].slice(0, 120),
  };

  const cloned = [...all];
  cloned[index] = updated;
  persistWorksWithFallback(cloned.sort((a, b) => b.updatedAt - a.updatedAt));
}

export function deleteWorkRecord(workId: string) {
  const all = loadWorks();
  const next = all.filter((item) => item.id !== workId);
  safeWriteScoped(WORKS_KEY, next);
}

export function getLatestSnapshotState(): any {
  const all = loadWorks();
  if (!Array.isArray(all) || all.length === 0) return null;
  const latestWork = all[0];
  const latestVersion = latestWork?.versions?.[0];
  if (!latestVersion || typeof latestVersion.state !== 'object' || latestVersion.state === null) {
    return null;
  }
  return latestVersion.state;
}
