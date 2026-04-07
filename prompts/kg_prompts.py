"""
知识图谱相关提示词模板
用于从文本中提取实体和关系
"""

ENTITY_EXTRACTION_PROMPT = """You are an expert knowledge-graph extraction assistant.

Please extract entities and relations from the given text using structured triples.

Rules:
1. Prefer the pattern: <Entity, Predicate, Entity/Attribute>.
2. Relations must have clear direction.
3. Keep only factual, explicit, non-speculative relations.
4. Each relation must include `relation_text` as the original predicate phrase.

Output ONLY valid JSON in this schema:
{
  "entities": [
    {
      "name": "entity name",
      "type": "entity type from allowed set",
      "description": "short description",
      "confidence": 0.9
    }
  ],
  "relations": [
    {
      "source": "entity name in entities",
      "target": "entity name in entities",
      "type": "relation type from allowed set",
      "relation_text": "2~6个汉字的极简关系动词（如：包含、属于、产生）",
      "description": "optional short explanation",
      "confidence": 0.85
    }
  ]
}

Text:
{content}
"""


ENTITY_EXTRACTION_PROMPT_ZH = """你是一个专业的知识图谱抽取助手。请从输入文本中抽取实体与关系。

## 任务要求

1. 从文章中提取科学实体和关系
2. 只提取明确表述的、科学准确的内容
3. 适合中文语境，关系谓词尽量简洁自然
4. 不要提取过于宽泛或模糊的概念
5. 必须优先使用“实体-关系-实体/属性”的结构化句式进行抽取
## 结构化句式约束（强约束）

- 先在内部形成结构化语句，采用以下之一：
  - `<实体, 关系, 实体>`
  - `<实体, 关系, 属性/现象>`
- 再把这些结构化语句映射为下方 JSON 的 entities 与 relations。
- 关系方向必须清晰，禁止无方向的模糊描述。
- 每条 relation 必须可回溯到一条结构化语句。
- 每条 relation 必须输出 `relation_text` 字段，填写关系谓词原文（如："转动"、"遮挡"、"提出"）。
- **【极其重要】** `relation_text` 必须简洁，通常为主谓结构的动词或动宾短语（严格控制在 **2~4个汉字**），千万不要使用长句！例如使用“属于”、“组成”、“提出理论”、“产生”等，而不要用“是包含在什么之中的”这种长句。

## 三元组模板（请遵循）

- `<实体 A, 关系动词, 实体 B>`
- `<实体, 属性, 属性值>`

## 多领域示例（few-shot）

一、天文领域
- `<太阳，属于，黄矮星>`
- `<太阳，能量来源，氢核聚变>`
- `<地球，公转周期，一年>`
- `<月球，卫星属于，地球>`
- `<日食，形成原因，月球遮挡太阳>`

二、人物领域
- `<李白，朝代，唐朝>`
- `<李白，职业，诗人>`
- `<杜甫，并称，李杜>`
- `<爱因斯坦，提出理论，相对论>`
- `<屠呦呦，获得奖项，诺贝尔生理学或医学奖>`

三、地理领域
- `<北京，首都属于，中国>`
- `<长江，流经，中国>`
- `<喜马拉雅山脉，包含山峰，珠穆朗玛峰>`
- `<太平洋，属于，大洋>`

四、生物领域
- `<人类，属于，哺乳动物>`
- `<猫，食性，肉食动物>`
- `<光合作用，场所，叶绿体>`
- `<DNA，存储，遗传信息>`

五、历史事件领域
- `<辛亥革命，发生时间，1911年>`
- `<丝绸之路，连接，东方与西方>`
- `<造纸术，发明者，蔡伦>`

六、影视/书籍领域
- `<《红楼梦》，作者，曹雪芹>`
- `<孙悟空，出自作品，《西游记》>`
- `<《流浪地球》，类型，科幻电影>`

七、企业与产品领域
- `<字节跳动，研发产品，抖音>`
- `<苹果公司，推出产品，iPhone>`
- `<淘宝，所属公司，阿里巴巴>`

示例（主题：太阳）：
- `<地球，围绕公转，太阳>`
- `<太阳，是中心天体，太阳系>`
- `<太阳辐射，是能量基础，地球生命>`
- `<地球，遮挡形成，月食现象>`

## 实体类型定义

- CONCEPT: 科学概念（如"重力"、"光合作用"、"能量"）
- OBJECT: 物体/物质（如"水"、"恐龙"、"太阳"、"二氧化碳"）
- ORGANISM: 生物（如"蜜蜂"、"榕树"、"蓝鲸"、"大肠杆菌"）
- PERSON: 人物（如"爱因斯坦"、"达尔文"、"居里夫人"）
- PLANET: 星球（如"地球"、"火星"、"月球"、"太阳"）
- PHENOMENON: 自然现象（如"彩虹"、"火山爆发"、"地震"、"潮汐"）
- PROCESS: 过程/原理（如"水循环"、"消化"、"细胞分裂"、"燃烧"）
- DEVICE: 设备/工具（如"显微镜"、"望远镜"、"指南针"、"温度计"）
- PLACE: 地点（如"亚马逊雨林"、"南极"、"马里亚纳海沟"）
- EVENT: 事件（如"恐龙灭绝"、"人类登月"、"工业革命"）

## 关系类型定义

- IS_A: 是一种（如：蜜蜂 IS_A 昆虫）
- PART_OF: 隶属于（如：心脏 PART_OF 循环系统）
- HAS_PART: 包含（如：太阳 HAS_PART 日冕）
- CAUSES: 导致（如：温室效应 CAUSES 全球变暖）
- IS_CAUSED_BY: 归因于（如：地震 IS_CAUSED_BY 板块运动）
- RELATED_TO: 相关（如：蜜蜂 RELATED_TO 花粉）
- INTERACTS_WITH: 相互作用（如：植物 INTERACTS_WITH 阳光）
- LIVES_IN: 生活于（如：企鹅 LIVES_IN 南极）
- DISCOVERED_BY: 发现者（如：万有引力 DISCOVERED_BY 牛顿）
- EXAMPLE_OF: 举例（如：恐龙 EXAMPLE_OF 古生物）
- SIMILAR_TO: 类似（如：蝙蝠 SIMILAR_TO 鸟类）
- CONTRASTS_WITH: 对比（如：冬眠 CONTRASTS_WITH 夏眠）

## 置信度评分标准

- 0.9-1.0: 非常确定，文章中明确说明
- 0.7-0.89: 比较确定，上下文强烈暗示
- 0.5-0.69: 可能正确，有一定依据但不明确
- <0.5: 不确定，不要提取

## 输出格式

请严格以 JSON 格式输出，不要包含任何其他文字；不要输出上述结构化语句原文：

{
  "entities": [
    {
      "name": "实体名称",
      "type": "实体类型",
      "description": "简要描述（适合儿童理解，1-2句话）",
      "confidence": 0.9
    }
  ],
  "relations": [
    {
      "source": "源实体名称（必须在entities列表中）",
      "target": "目标实体名称（必须在entities列表中）",
      "type": "关系类型",
      "relation_text": "关系谓词原文（简短中文动词短语）",
      "description": "关系描述（可选）",
      "confidence": 0.85
    }
  ]
}

## 文章内容：

{content}
"""


def get_entity_extraction_prompt(content: str, language: str = "zh") -> str:
    """获取实体提取提示词"""
    template = ENTITY_EXTRACTION_PROMPT_ZH if language == "zh" else ENTITY_EXTRACTION_PROMPT
    # 模板中包含大量 JSON 花括号，不能使用 str.format。
    return template.replace("{content}", content)


def clean_json_output(text: str) -> str:
    """清理LLM输出的JSON"""
    text = text.strip()
    # 找到第一个{和最后一个}
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start:end+1]
    return text
