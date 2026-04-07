from utils.llm_client import LLMClient
from typing import List, Dict, Any
from prompts.publisher_prompt import (
    PUBLISHER_SYSTEM_PROMPT,
    PUBLISHER_USER_PROMPT_TEMPLATE,
)

class PublisherAgent:
    def __init__(self):
        self.llm_client = LLMClient()
        self.system_prompt = PUBLISHER_SYSTEM_PROMPT

    def compile_to_html(self, title: str, content: str, glossary: List[Dict[str, str]], illustrations: List[Dict[str, Any]]) -> str:
        """
        组合所有素材，使用大模型按设定要求一次性输出精美的HTML代码
        """
        # 构建插图列表文本
        illustrations_list = ""
        for idx, img in enumerate(illustrations):
            image_url = img.get("image_url", "https://via.placeholder.com/800x450?text=Image+Not+Found")
            desc = img.get("summary") or img.get("image_prompt", "本文插图")
            illustrations_list += f"- 插图 {idx+1}: [{desc}] \n 图片链接(URL): {image_url}\n"

        # 构建词汇表文本
        glossary_list = ""
        for item in glossary:
            term = item.get("term", "")
            explanation = item.get("explanation", "")
            glossary_list += f"- 词汇: {term} | 解释: {explanation}\n"

        user_prompt = PUBLISHER_USER_PROMPT_TEMPLATE.format(
            title=title,
            content=content,
            illustrations_list=illustrations_list,
            glossary_list=glossary_list,
        )
        
        html_code = self.llm_client.generate_text(self.system_prompt, user_prompt)
        
        # 二次清理，避免模型可能包含的 markdown 痕迹
        if html_code.startswith("```"):
            html_code = html_code[html_code.find('\n')+1:html_code.rfind('```')]
            
        return html_code.strip()
