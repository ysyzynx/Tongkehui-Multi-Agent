# Phase-1 历史样本导出与标注模板工作流

## 目标

在不改动线上功能的前提下，完成以下两项能力：

1. 历史样本导出模板
2. 标注模板生成器

## 产物清单

1. scripts/export_historical_samples_template.py
   - 从数据库 `agent_feedbacks` + `stories` 只读导出。
   - 输出 `outputs/phase1/historical_samples_template.jsonl`。

2. scripts/generate_annotation_templates.py
   - 读取历史样本 JSONL。
   - 输出：
     - `outputs/phase1/annotation_tasks.jsonl`
     - `outputs/phase1/annotation_matrix.csv`

## 快速使用

在项目根目录执行：

```powershell
python scripts/export_historical_samples_template.py --limit 500
python scripts/generate_annotation_templates.py --input outputs/phase1/historical_samples_template.jsonl
```

按故事主题抽样导出（Phase-1.5）：

```powershell
python scripts/export_historical_samples_template.py --theme-keywords 地球,光 --sample-per-theme 20 --limit 200
```

## 导出模板字段说明

每条样本包含：

1. source
   - feedback_id / story_id / agent_type / created_at
2. story
   - title / content / age_group / style / target_audience / extra_requirements
3. model_output
   - feedback_text / revised_content / review_sections / evidence / raw_feedback / parsed_feedback
4. annotation
   - status / primary_label_id / secondary_label_ids / quality_score / rationale / evidence_spans 等

## 标注模板策略

1. science 类 agent（包含字符串 science）默认候选分组：`SCIENCE_REVIEW`
2. 其他 agent 默认候选分组：`VALUE_TAG`

## 注意事项

1. 历史反馈字段当前以 `str(dict)` 为主，导出脚本已做 JSON + literal_eval 双解析兼容。
2. 本阶段不写回数据库，不改动任何现有 API。
3. 可重复执行，输出文件会覆盖，建议在每轮标注前留存快照。
4. 主题抽样参数说明：
   - `--theme-keywords`：按 `stories.theme` 子串匹配过滤（逗号分隔）
   - `--sample-per-theme`：每个主题最多抽样 N 条
   - `--random-seed`：抽样随机种子，保证复现实验
