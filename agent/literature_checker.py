import json
from utils.llm_client import LLMClient
from typing import Dict, Any
from prompts.literature_checker_prompt import (
    LITERATURE_CHECKER_SYSTEM_PROMPT,
    LITERATURE_CHECKER_USER_PROMPT_TEMPLATE,
)

class LiteratureCheckerAgent:
    def __init__(self):
        self.llm_client = LLMClient()
        self.system_prompt = LITERATURE_CHECKER_SYSTEM_PROMPT

    def review_story(
        self,
        title: str,
        content: str,
        target_audience: str = "大众",
        age_group: str = None,
    ) -> Dict[str, Any]:
        """
        从文学角度审查并润色故事
        """
        # 确定最终的目标受众描述
        final_audience = target_audience or "大众"
        if age_group and age_group not in final_audience:
            final_audience = f"{final_audience}（年龄段：{age_group}）"

        # 判断是否为儿童受众，生成对应的特殊说明
        audience_specific_instruction = self._get_audience_instruction(final_audience)

        user_prompt = LITERATURE_CHECKER_USER_PROMPT_TEMPLATE.format(
            title=title,
            content=content,
            target_audience=final_audience,
            audience_specific_instruction=audience_specific_instruction,
        )

        print("文学编辑正在阅读和润色故事中...")
        response_json = self.llm_client.generate_json(self.system_prompt, user_prompt)
        return response_json

    def _get_audience_instruction(self, target_audience: str) -> str:
        """根据目标受众判断是否需要启用儿童文学特殊指导"""
        child_keywords = ["儿童", "幼儿", "少年", "少儿", "孩子", "小孩", "3-", "6-", "12-", "青少幼年"]
        is_child_audience = any(keyword in target_audience for keyword in child_keywords)

        if is_child_audience:
            return """
- 目标受众为儿童/少儿，请参照【儿童文学黄金法则】进行润色
- 语言要生动有趣、充满童趣，适合儿童理解
- 可参考【儿童文学润色技巧】与示例
- 确保内容积极向上，富有教育意义
"""
        else:
            return """
- 目标受众为普通大众或特定成人群体，请从通用文学专业角度进行润色
- 保持语言的准确性与文学性
- 根据具体受众特点调整语言风格与表达方式
"""
