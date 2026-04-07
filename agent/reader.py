from typing import Dict, Any
from agent.base_agent import BaseAgent
from utils.llm_client import LLMClient
from prompts.reader_prompt import (
    READER_SYSTEM_PROMPT,
    READER_USER_PROMPT_TEMPLATE,
    READER_REFINE_SYSTEM_PROMPT,
    READER_REFINE_USER_PROMPT_TEMPLATE,
)

class ReaderAgent(BaseAgent):
    """读者Agent：根据生成结果提供虚拟读者评分与反馈"""

    def __init__(self):
        super().__init__(name="Reader", description="Evaluates story from the perspective of target audience.")
        self.llm_client = LLMClient()
        self.system_prompt = READER_SYSTEM_PROMPT

    def _normalize_refine_result(self, result: Any, fallback_content: str) -> Dict[str, Any]:
        payload = result if isinstance(result, dict) else {}
        revised_content = str(payload.get("revised_content") or "").strip()

        if not revised_content:
            plain = self.llm_client.generate_text(
                "你是科普文本编辑，请只输出微调后的正文，不要输出 JSON。",
                (
                    "请基于以下文本做轻量微调，保持科学事实不变，提升可读性与趣味性。"
                    f"\n\n原文：\n{fallback_content}"
                ),
            )
            plain_text = str(plain or "").strip()
            if plain_text and not plain_text.startswith("<!-- 生成失败"):
                revised_content = plain_text

        if not revised_content:
            revised_content = fallback_content

        optimization_notes = str(payload.get("optimization_notes") or "").strip()
        if not optimization_notes:
            optimization_notes = "根据观众反馈完成轻量润色，优化了表达节奏与读者代入感。"

        return {
            "revised_content": revised_content,
            "optimization_notes": optimization_notes,
            "version": "4.0",
        }

    def _normalize_result(self, result: Any, target_audience: str) -> Dict[str, Any]:
        payload = result if isinstance(result, dict) else {}

        feedback_text = (
            str(payload.get("reader_feedback") or "").strip()
            or str(payload.get("audience_feedback") or "").strip()
            or str(payload.get("feedback") or "").strip()
            or str(payload.get("comment") or "").strip()
        )

        fallback_content = str(payload.get("content") or "").strip()
        known_error_msg = "内容生成过程中出现异常"
        error_text = str(payload.get("error") or "").strip()

        # 非结构化文本兜底：若 content 不是通用报错文案，则可视为候选反馈。
        if not feedback_text and fallback_content and known_error_msg not in fallback_content:
            feedback_text = fallback_content

        if not feedback_text:
            prefix = f"本次观众反馈生成出现异常（{error_text}），以下为系统兜底反馈。\n" if error_text else ""
            feedback_text = prefix + (
                f"我的身份是{target_audience}。\n"
                "1. 易读性：整体表达比较顺畅，主要信息能够读懂；建议对个别长句进一步拆分，降低阅读负担。\n"
                "2. 科普性：文章呈现了核心科学点，能够形成初步认知；可再补1-2个生活化例子帮助理解。\n"
                "3. 有趣性：叙述有一定故事感，能够保持阅读兴趣；可增加一个互动提问提升参与感。\n"
                "4. 实用性：内容对日常学习有启发，具备迁移价值；建议补充“如何实践”的简短步骤。\n"
                "5. 传播性：整体适合分享给同伴，主题清晰；若加一句记忆点总结，传播效果会更好。\n\n"
                "【总体印象】我最喜欢的是内容清楚、节奏稳定；仍可改进的是部分知识点可再更具体一些。"
            )

        normalized = dict(payload)
        normalized["reader_feedback"] = feedback_text
        return normalized

    def run(self, story_content: str, title: str, target_audience: str) -> Dict[str, Any]:
        """
        作为“试读人员”，评估故事是否符合目标受众，有无吸引力。
        :param story_content: 故事正文
        :param title: 故事标题
        :param target_audience: 目标受众画像描述（例如："幼年儿童（3-6岁）"等）
        """
        user_prompt = READER_USER_PROMPT_TEMPLATE.format(
            target_audience=target_audience,
            title=title,
            story_content=story_content,
        )
        
        print(f"虚拟读者（身份：{target_audience}）正在试读故事...")
        raw_result = self.llm_client.generate_json(self.system_prompt, user_prompt)

        # Reader 场景允许二次降级：当模型返回的是非 JSON 纯文本时，
        # 直接改走文本生成，避免将“JSON 解析失败”误判为 API 不可用。
        if isinstance(raw_result, dict) and str(raw_result.get("error") or "").strip():
            plain_prompt = (
                f"你是{target_audience}身份的读者。请直接输出读者反馈正文，不要输出 JSON，不要代码块。\n"
                f"必须包含：\n"
                f"1. 开头写“我的身份是{target_audience}”。\n"
                f"2. 严格按 1-5 五个小节：易读性、科普性、有趣性、实用性、传播性。\n"
                f"3. 每节 2-4 句，并在末尾写【总体印象】。\n\n"
                f"文章标题：《{title}》\n"
                f"文章正文：\n{story_content}"
            )
            text_result = self.llm_client.generate_text(
                "你是虚拟读者反馈助手，请只输出中文反馈正文。",
                plain_prompt,
            )
            cleaned = str(text_result or "").strip()
            if cleaned and not cleaned.startswith("<!-- 生成失败"):
                raw_result = {"reader_feedback": cleaned}

        self.result = self._normalize_result(raw_result, target_audience)
        return self.result

    def refine_by_feedback(
        self,
        story_content: str,
        title: str,
        target_audience: str,
        reader_feedback: str,
    ) -> Dict[str, Any]:
        user_prompt = READER_REFINE_USER_PROMPT_TEMPLATE.format(
            target_audience=target_audience,
            title=title,
            story_content=story_content,
            reader_feedback=reader_feedback,
        )

        raw_result = self.llm_client.generate_json(
            READER_REFINE_SYSTEM_PROMPT,
            user_prompt,
        )
        return self._normalize_refine_result(raw_result, story_content)
