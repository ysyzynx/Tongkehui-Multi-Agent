# Phase-2 任务二：外部语义知识层（标签增强）

## 目标

基于现有知识图谱与标签体系，构建标签增强层，输出：

1. 标签相关子图（标签节点、同义词/提示词映射实体、关系边）
2. 标签关系矩阵（共现矩阵 + 条件概率矩阵）
3. 每个标签的增强向量（工程可行版）
4. 可视化校验文件

## 复用能力

1. `utils.kg_builder.py`
   - 复用 `find_entity_by_name` 做标签到实体的名称/别名召回
   - 复用实体标准化逻辑 `normalize_entity_name`

2. `utils.fact_rag.py`
   - 复用 `search_fact_evidence` 做标签语义证据补全
   - 复用 `cosine_similarity` 做标签-实体向量匹配

3. `utils.llm_client.py`
   - 复用 `generate_embedding` 生成标签、实体、证据向量

## 脚本

- [scripts/build_label_semantic_layer.py](scripts/build_label_semantic_layer.py)

## 运行方式

```powershell
python scripts/build_label_semantic_layer.py --output-dir outputs/phase2 --semantic-top-k 8 --semantic-threshold 0.55 --evidence-top-k 4
```

## 输出文件

输出目录默认：`outputs/phase2`

1. `label_related_subgraphs.json`
   - 每个标签命中的实体、邻域实体、关系边、证据条目

2. `label_relation_matrices.json`
   - `cooccurrence_matrix`
   - `conditional_probability_matrix`
   - `adjacency`（每个标签 top 邻接标签）

3. `label_enhanced_vectors.json`
   - `engineering_features`：图统计特征
   - `semantic_embedding`：标签/实体/证据聚合向量
   - `enhanced_vector`：可直接给下游模型使用

4. `label_cooccurrence_matrix.csv`
5. `label_conditional_probability_matrix.csv`
6. `label_relation_preview.html`
   - 人工抽检标签关系合理性的可视化页面

## 验收对应

1. 能输出每个标签增强向量与邻接关系：
   - `label_enhanced_vectors.json`
   - `label_relation_matrices.json` -> `adjacency`

2. 可视化校验若干标签关系：
   - `label_relation_preview.html`

## 兼容性与安全性

1. 只读数据库，不写入任何业务表。
2. 不改现有路由、不改线上推理。
3. 若向量接口不可用，脚本仍会输出图统计特征与基础矩阵（向量维度可能为0）。
