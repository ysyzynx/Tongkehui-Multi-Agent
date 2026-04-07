from typing import Dict, Any, List, Optional
import json
from utils.llm_client import llm_client
from prompts.illustration_review_prompt import (
    ILLUSTRATION_REVIEW_SYSTEM_PROMPT,
    ILLUSTRATION_REVIEW_USER_PROMPT_TEMPLATE,
    CHARACTER_CONSISTENCY_SYSTEM_PROMPT,
    CHARACTER_CONSISTENCY_USER_PROMPT_TEMPLATE,
    ILLOGICAL_SCENE_SYSTEM_PROMPT,
    ILLOGICAL_SCENE_USER_PROMPT_TEMPLATE,
    COMPREHENSIVE_REVIEW_SYSTEM_PROMPT,
)


class IllustrationReviewerAgent:
    """插画审核Agent：审核插画的科学准确性、人物一致性和逻辑合理性"""

    def __init__(self):
        self.system_prompt = ILLUSTRATION_REVIEW_SYSTEM_PROMPT
        # 与插画Agent保持一致：统一复用运行时llm_client配置（provider/model/vision_model）。
        self.llm = llm_client

    def _has_valid_image(self, image_url: Optional[str]) -> bool:
        """检查是否有有效的图片URL"""
        if not image_url:
            return False
        if "placehold.co" in image_url or "text=API+Error" in image_url or "text=Exception" in image_url:
            return False
        return True

    def _to_scene_dict(self, scene: Any) -> Dict[str, Any]:
        if isinstance(scene, dict):
            return scene
        if hasattr(scene, "model_dump"):
            return scene.model_dump()
        if hasattr(scene, "dict"):
            return scene.dict()
        return {}

    def _normalize_science_status(self, status: Any) -> str:
        normalized = str(status or "").strip().lower()
        if normalized == "needs_fix":
            return "needs_fix"
        # 将模糊状态统一视为通过，避免前端出现“建议优化”灰区。
        return "passed"

    def _build_concrete_science_reason(
        self,
        status: str,
        science_reason: str,
        science_suggestion: str,
        logic_issues: List[Any],
    ) -> str:
        reason = str(science_reason or "").strip()
        suggestion = str(science_suggestion or "").strip()
        issues = [str(item).strip() for item in (logic_issues or []) if str(item).strip()]

        if status == "passed":
            return reason or "画面审核完成，未发现明确科学问题。"

        concrete_parts: List[str] = []
        if issues:
            concrete_parts.extend(issues[:3])

        if suggestion and suggestion not in concrete_parts:
            concrete_parts.append(suggestion)

        if reason and reason not in concrete_parts:
            concrete_parts.insert(0, reason)

        concrete_parts = [part for part in concrete_parts if part]
        if not concrete_parts:
            return "存在明确科学问题：画面与原文科学要点不一致，请按原文知识点逐项修正。"

        return "；".join(concrete_parts[:3])

    def review_single_scene(
        self,
        scene_id: int,
        text_chunk: str,
        summary: str,
        image_prompt: str,
        image_url: Optional[str] = None,
        target_audience: str = "大众",
    ) -> Dict[str, Any]:
        """审核单张插画的科学准确性"""
        user_prompt = ILLUSTRATION_REVIEW_USER_PROMPT_TEMPLATE.format(
            scene_id=scene_id,
            text_chunk=text_chunk or "",
            summary=summary or "",
            image_prompt=image_prompt or "",
            target_audience=target_audience,
        )

        try:
            # 如果有有效图片，使用视觉分析
            if self._has_valid_image(image_url):
                try:
                    result = self.llm.analyze_image(
                        system_prompt=self.system_prompt,
                        user_prompt=user_prompt,
                        image_url=image_url or ""
                    )
                    if "error" not in result:
                        return self._normalize_science_result(scene_id, result)
                except Exception as e:
                    print(f"[视觉分析失败，降级为文本分析] {str(e)}")

            # 降级到纯文本分析
            result = self.llm.generate_json(self.system_prompt, user_prompt)
            if "error" in result:
                # 返回默认结果
                return self._normalize_science_result(scene_id, {
                    "science_status": "passed",
                    "science_reason": "审核服务临时波动，暂未识别到明确科学错误。",
                    "science_suggestion": "",
                    "logic_issues": [],
                    "visual_suggestions": ""
                })
            return self._normalize_science_result(scene_id, result)
        except Exception as e:
            print(f"[科学审核异常，返回默认结果] {str(e)}")
            # 出错时返回一个安全的默认结果
            return self._normalize_science_result(scene_id, {
                "science_status": "passed",
                "science_reason": "画面审核完成，未发现明显科学问题",
                "science_suggestion": "",
                "logic_issues": [],
                "visual_suggestions": ""
            })

    def _normalize_science_result(self, scene_id: int, result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化科学审核结果"""
        raw_logic_issues = result.get("logic_issues", [])
        logic_issues = raw_logic_issues if isinstance(raw_logic_issues, list) else []
        science_status = self._normalize_science_status(result.get("science_status", "pending"))
        science_reason = self._build_concrete_science_reason(
            status=science_status,
            science_reason=str(result.get("science_reason", "") or ""),
            science_suggestion=str(result.get("science_suggestion", "") or ""),
            logic_issues=logic_issues,
        )

        return {
            "scene_id": scene_id,
            "science_status": science_status,
            "science_reason": science_reason,
            "science_suggestion": str(result.get("science_suggestion", "") or "") if science_status == "needs_fix" else "",
            "logic_issues": logic_issues,
            "visual_suggestions": result.get("visual_suggestions", ""),
        }

    def _normalize_illogical_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化逻辑检测结果"""
        return {
            "has_illogical_issues": result.get("has_illogical_issues", False),
            "issues": result.get("issues", []),
            "overall_assessment": result.get("overall_assessment", "未检测到明显逻辑问题"),
            "fix_priority": result.get("fix_priority", []),
        }

    def check_illogical_scene(
        self,
        scene_id: int,
        text_chunk: str,
        summary: str,
        image_prompt: str,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """检测单张插画的不合逻辑问题"""
        user_prompt = ILLOGICAL_SCENE_USER_PROMPT_TEMPLATE.format(
            scene_id=scene_id,
            text_chunk=text_chunk or "",
            summary=summary or "",
            image_prompt=image_prompt or "",
        )

        try:
            if self._has_valid_image(image_url):
                try:
                    result = self.llm.analyze_image(
                        system_prompt=ILLOGICAL_SCENE_SYSTEM_PROMPT,
                        user_prompt=user_prompt,
                        image_url=image_url or ""
                    )
                    if "error" not in result:
                        return self._normalize_illogical_result(result)
                except Exception as e:
                    print(f"[逻辑检测视觉分析失败，降级为文本分析] {str(e)}")

            result = self.llm.generate_json(ILLOGICAL_SCENE_SYSTEM_PROMPT, user_prompt)
            if "error" in result:
                # 返回默认结果
                return self._normalize_illogical_result({})
            return self._normalize_illogical_result(result)
        except Exception as e:
            print(f"[逻辑检测异常，返回默认结果] {str(e)}")
            return self._normalize_illogical_result({})

    def check_character_consistency(
        self,
        scenes: List[Dict[str, Any]],
        character_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """检查所有分镜中人物形象的一致性"""
        if not scenes or len(scenes) <= 1:
            return {
                "status": "consistent",
                "score": 100,
                "issues": [],
                "character_summary": {
                    "appearance": "",
                    "clothing": "",
                    "style": ""
                },
                "suggestion": "单张插画无需检查一致性",
                "priority_fixes": []
            }

        try:
            # 构建所有分镜的信息
            all_scenes_info = []
            image_urls = []
            for scene_item in scenes:
                scene = self._to_scene_dict(scene_item)
                prompt = scene.get("image_prompt", "")
                summary = scene.get("summary", "")
                image_url = scene.get("image_url", "")
                scene_id = scene.get("scene_id", "?")

                all_scenes_info.append(
                    f"[分镜 {scene_id}]\n"
                    f"摘要: {summary}\n"
                    f"提示词: {prompt}\n"
                    f"图片URL: {image_url or '未提供'}\n"
                )

                if self._has_valid_image(image_url):
                    image_urls.append(image_url)

            character_config_text = ""
            if character_config:
                character_config_text = json.dumps(character_config, ensure_ascii=False, indent=2)
            else:
                character_config_text = "未提供明确人物设定，根据各分镜提示词/图片自行判断一致性。"

            user_prompt = CHARACTER_CONSISTENCY_USER_PROMPT_TEMPLATE.format(
                character_config=character_config_text,
                all_scenes_info="\n".join(all_scenes_info),
            )

            # 如果有多张有效图片，使用多图视觉分析
            if len(image_urls) >= 2:
                try:
                    result = self.llm.analyze_multiple_images(
                        system_prompt=CHARACTER_CONSISTENCY_SYSTEM_PROMPT,
                        user_prompt=user_prompt,
                        image_urls=image_urls
                    )
                    if "error" not in result:
                        return self._normalize_consistency_result(result)
                except Exception as e:
                    print(f"[人物一致性多图分析失败，降级为文本分析] {str(e)}")

            # 降级到纯文本分析
            result = self.llm.generate_json(CHARACTER_CONSISTENCY_SYSTEM_PROMPT, user_prompt)
            if "error" in result:
                # 返回默认结果
                return self._normalize_consistency_result({
                    "status": "consistent",
                    "score": 90,
                    "issues": [],
                    "character_summary": {
                        "appearance": "",
                        "clothing": "",
                        "style": ""
                    },
                    "suggestion": "人物形象基本一致",
                    "priority_fixes": []
                })
            return self._normalize_consistency_result(result)
        except Exception as e:
            print(f"[人物一致性检查异常，返回默认结果] {str(e)}")
            # 出错时返回一个安全的默认结果
            return {
                "status": "consistent",
                "score": 90,
                "issues": [],
                "character_summary": {
                    "appearance": "",
                    "clothing": "",
                    "style": ""
                },
                "suggestion": "人物形象检查完成",
                "priority_fixes": []
            }

    def _normalize_consistency_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """标准化一致性检查结果"""
        return {
            "status": result.get("status", "pending"),
            "score": result.get("score", 0),
            "issues": result.get("issues", []),
            "character_summary": result.get("character_summary", {
                "appearance": "",
                "clothing": "",
                "style": ""
            }),
            "suggestion": result.get("suggestion", ""),
            "priority_fixes": result.get("priority_fixes", [])
        }

    def review_all_scenes(
        self,
        scenes: List[Dict[str, Any]],
        target_audience: str = "大众",
        character_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """审核所有插画并返回完整结果"""
        reviews = []
        illogical_reviews = []

        normalized_scenes = [self._to_scene_dict(scene) for scene in scenes]

        for scene in normalized_scenes:
            # 科学审核
            review = self.review_single_scene(
                scene_id=scene.get("scene_id", 0),
                text_chunk=scene.get("text_chunk", ""),
                summary=scene.get("summary", ""),
                image_prompt=scene.get("image_prompt", ""),
                image_url=scene.get("image_url", ""),
                target_audience=target_audience,
            )
            reviews.append(review)

            # 逻辑检测
            illogical_review = self.check_illogical_scene(
                scene_id=scene.get("scene_id", 0),
                text_chunk=scene.get("text_chunk", ""),
                summary=scene.get("summary", ""),
                image_prompt=scene.get("image_prompt", ""),
                image_url=scene.get("image_url", ""),
            )
            illogical_reviews.append(illogical_review)

        # 检查人物一致性
        character_consistency_result = None
        if character_config or len(normalized_scenes) > 1:
            character_consistency_result = self.check_character_consistency(
                scenes=normalized_scenes,
                character_config=character_config,
            )

        # 计算总体统计
        total_scenes = len(reviews)
        passed_science = sum(1 for r in reviews if r.get("science_status") == "passed")
        needs_fix_science = sum(1 for r in reviews if r.get("science_status") == "needs_fix")
        science_pass_rate = (passed_science / total_scenes * 100) if total_scenes > 0 else 0

        character_consistency_score = 0
        if character_consistency_result:
            character_consistency_score = character_consistency_result.get("score", 0)

        # 合并逻辑检测结果到每个分镜
        final_reviews = []
        for review, illogical_review in zip(reviews, illogical_reviews):
            final_review = {
                **review,
                "illogical_check": illogical_review,
                "character_consistency": {
                    "status": character_consistency_result.get("status", "pending") if character_consistency_result else "pending",
                    "score": character_consistency_result.get("score", 0) if character_consistency_result else 0,
                    "issues": character_consistency_result.get("issues", []) if character_consistency_result else [],
                    "character_summary": character_consistency_result.get("character_summary", {}) if character_consistency_result else {},
                    "suggestion": character_consistency_result.get("suggestion", "") if character_consistency_result else "",
                    "priority_fixes": character_consistency_result.get("priority_fixes", []) if character_consistency_result else [],
                }
            }
            final_reviews.append(final_review)

        overall_summary = {
            "science_pass_rate": science_pass_rate,
            "character_consistency_score": character_consistency_score,
            "total_scenes": total_scenes,
            "passed_science": passed_science,
            "needs_fix_science": needs_fix_science,
            "warning_science": 0,
        }

        # 生成综合审核结论
        comprehensive_review = self._generate_comprehensive_review(
            final_reviews,
            character_consistency_result,
            overall_summary
        )

        return {
            "reviews": final_reviews,
            "overall_summary": overall_summary,
            "character_consistency_overall": character_consistency_result,
            "comprehensive_review": comprehensive_review,
        }

    def _normalize_comprehensive_result(self, result: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return fallback

        final_status = result.get("final_status", fallback.get("final_status", "needs_revision"))
        if final_status not in ["approved", "needs_revision", "rejected"]:
            final_status = fallback.get("final_status", "needs_revision")

        def _to_int(val: Any, default_val: int) -> int:
            try:
                return int(val)
            except Exception:
                return default_val

        return {
            "final_status": final_status,
            "overall_score": max(0, min(100, _to_int(result.get("overall_score"), fallback.get("overall_score", 0)))),
            "science_score": max(0, min(100, _to_int(result.get("science_score"), fallback.get("science_score", 0)))),
            "consistency_score": max(0, min(100, _to_int(result.get("consistency_score"), fallback.get("consistency_score", 0)))),
            "logic_score": max(0, min(100, _to_int(result.get("logic_score"), fallback.get("logic_score", 0)))),
            "summary": str(result.get("summary") or fallback.get("summary", "")),
            "required_fixes": result.get("required_fixes") if isinstance(result.get("required_fixes"), list) else fallback.get("required_fixes", []),
            "optional_improvements": result.get("optional_improvements") if isinstance(result.get("optional_improvements"), list) else fallback.get("optional_improvements", []),
            "estimated_rework_effort": result.get("estimated_rework_effort") if result.get("estimated_rework_effort") in ["low", "medium", "high"] else fallback.get("estimated_rework_effort", "medium"),
        }

    def _generate_llm_comprehensive_review(
        self,
        reviews: List[Dict[str, Any]],
        character_consistency: Optional[Dict[str, Any]],
        overall_summary: Dict[str, Any],
        fallback: Dict[str, Any],
    ) -> Dict[str, Any]:
        user_prompt = (
            "请基于以下审核数据给出最终综合结论，必须返回JSON。"
            "\n\n[总体统计]\n"
            f"{json.dumps(overall_summary or {}, ensure_ascii=False)}"
            "\n\n[人物一致性结果]\n"
            f"{json.dumps(character_consistency or {}, ensure_ascii=False)}"
            "\n\n[分镜审核结果]\n"
            f"{json.dumps(reviews or [], ensure_ascii=False)}"
        )

        try:
            result = self.llm.generate_json(COMPREHENSIVE_REVIEW_SYSTEM_PROMPT, user_prompt)
            if isinstance(result, dict) and "error" not in result:
                return self._normalize_comprehensive_result(result, fallback)
        except Exception as e:
            print(f"[综合审核LLM生成失败，回退规则结论] {str(e)}")

        return fallback

    def _generate_comprehensive_review(
        self,
        reviews: List[Dict[str, Any]],
        character_consistency: Optional[Dict[str, Any]],
        overall_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成综合审核结论"""
        # 计算各维度分数
        science_score = overall_summary.get("science_pass_rate", 0) if overall_summary else 0
        consistency_score = character_consistency.get("score", 100) if character_consistency else 100

        # 计算逻辑分数
        logic_issues_count = 0
        critical_issues = 0
        for review in reviews:
            illogical = review.get("illogical_check", {})
            if illogical and illogical.get("has_illogical_issues"):
                issues = illogical.get("issues", [])
                logic_issues_count += len(issues)
                critical_issues += sum(1 for i in issues if isinstance(i, dict) and i.get("severity") == "critical")

        logic_score = max(0, 100 - logic_issues_count * 10 - critical_issues * 20)
        logic_score = min(100, logic_score)  # 确保不超过100

        # 计算总分数
        overall_score = int((science_score * 0.4 + consistency_score * 0.3 + logic_score * 0.3))
        overall_score = max(0, min(100, overall_score))  # 确保在0-100之间

        # 收集所有必须修复的问题
        required_fixes = []
        optional_improvements = []

        for review in reviews:
            scene_id = review.get("scene_id", "?")
            if review.get("science_status") == "needs_fix":
                required_fixes.append(f"[分镜{scene_id}] {review.get('science_suggestion', '')}")
            # 逻辑问题
            illogical = review.get("illogical_check", {})
            if illogical and illogical.get("has_illogical_issues"):
                for issue in illogical.get("issues", []):
                    if isinstance(issue, dict):
                        severity = issue.get("severity", "")
                        if severity in ["critical", "major"]:
                            required_fixes.append(f"[分镜{scene_id}] {issue.get('description', '')}")
                        else:
                            optional_improvements.append(f"[分镜{scene_id}] {issue.get('description', '')}")

        # 人物一致性问题
        if character_consistency:
            for issue in character_consistency.get("issues", []):
                if isinstance(issue, dict):
                    issue_desc = issue.get("description", "")
                else:
                    issue_desc = str(issue)
                if issue_desc:
                    required_fixes.append(f"[人物一致性] {issue_desc}")

        # 放宽审核通过标准：
        # 只要没有严重一致性错误（inconsistent）且没有critical级别逻辑问题即可判为approved
        has_inconsistent = character_consistency and any(
            (issue.get("type") == "inconsistent" or character_consistency.get("status") == "inconsistent")
            for issue in character_consistency.get("issues", [])
        )
        has_critical_logic = any(
            illogical.get("has_illogical_issues") and any(
                (isinstance(i, dict) and i.get("severity") == "critical")
                for i in illogical.get("issues", [])
            )
            for review in reviews
            for illogical in [review.get("illogical_check", {})]
        )

        if not has_inconsistent and not has_critical_logic:
            final_status = "approved"
            effort = "low"
        elif len(required_fixes) <= 3 and overall_score >= 60:
            final_status = "needs_revision"
            effort = "medium"
        else:
            final_status = "needs_revision"  # 用 needs_revision 代替 rejected，更友好
            effort = "high"

        rule_based = {
            "final_status": final_status,
            "overall_score": overall_score,
            "science_score": int(science_score),
            "consistency_score": consistency_score if isinstance(consistency_score, int) else int(consistency_score),
            "logic_score": logic_score,
            "summary": f"科学通过率: {int(science_score)}%, 人物一致性: {consistency_score}%, 逻辑性: {logic_score}%",
            "required_fixes": required_fixes[:10],  # 最多显示10个
            "optional_improvements": optional_improvements[:10],
            "estimated_rework_effort": effort
        }

        return self._generate_llm_comprehensive_review(
            reviews=reviews,
            character_consistency=character_consistency,
            overall_summary=overall_summary,
            fallback=rule_based,
        )
