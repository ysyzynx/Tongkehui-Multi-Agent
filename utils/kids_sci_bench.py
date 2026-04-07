"""
KidsSciBench - 童科绘审核质量评估基准
参考 OpenScholar 的 ScholarQABench
"""
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class EvaluationDimension(Enum):
    """评估维度"""
    SCIENTIFIC_ACCURACY = "scientific_accuracy"    # 科学准确性
    UNDERSTANDABILITY = "understandability"        # 儿童易懂性
    INTERESTINGNESS = "interestingness"            # 趣味性
    COVERAGE = "coverage"                          # 知识点覆盖度
    ORGANIZATION = "organization"                  # 组织性


@dataclass
class TestCase:
    """测试用例"""
    case_id: str
    title: str
    topic: str
    original_content: str
    reference_answer: Optional[str] = None
    reference_criteria: Optional[List[str]] = None
    target_audience: str = "8-12岁儿童"
    difficulty: str = "medium"  # easy, medium, hard


class KidsSciBench:
    """
    童科绘审核质量评估基准"""

    def __init__(self):
        self.test_cases: List[TestCase] = []
        self._init_default_test_cases()

    def _init_default_test_cases(self):
        """初始化默认测试用例"""
        # 测试用例 1: 恐龙主题
        self.test_cases.append(TestCase(
            case_id="CASE-DINOSAUR-001",
            title="恐龙小知识",
            topic="恐龙",
            target_audience="8-12岁儿童",
            original_content="""
在很久很久以前，地球上生活着一群巨大的生物——恐龙！

恐龙最早出现在大约2亿年前的三叠纪，然后在6500万年前突然消失了。
科学家们认为，恐龙灭绝是因为一颗小行星撞击了地球，这颗小行星大约有10公里宽，
撞击地点就在今天的中国四川省。

恐龙的种类可多啦！有像小山一样高的腕龙，它是最大的恐龙，身高可以达到50米！
还有凶猛的霸王龙，它是最厉害的食肉恐龙，牙齿像香蕉一样大。

恐龙都是冷血动物，它们需要晒太阳才能保持体温。
而且，所有的恐龙都生活在陆地上，没有恐龙会飞或者会游泳。
            """,
            reference_criteria=[
                "恐龙灭绝地点应为墨西哥尤卡坦半岛，不是四川",
                "腕龙身高约12-15米，不是50米",
                "很多恐龙可能是温血动物，不是全部冷血",
                "会飞的翼龙和会游的蛇颈龙不是恐龙",
            ],
            difficulty="medium",
        ))

        # 测试用例 2: 太阳系主题
        self.test_cases.append(TestCase(
            case_id="CASE-SOLAR-001",
            title="太阳系的奥秘",
            topic="太阳系",
            target_audience="8-12岁儿童",
            original_content="""
小朋友们，你们知道吗？我们生活的地球是宇宙的中心！
太阳、月亮和其他星星都绕着地球转。

太阳系有八大行星，按照距离太阳从近到远的顺序是：
水星、金星、地球、火星、木星、土星、天王星、海王星，还有冥王星！

太阳是一颗行星，它是最大的行星。
地球是距离太阳第三近的行星，我们的地球有一个卫星，叫月球。
            """,
            reference_criteria=[
                "地球不是宇宙中心，太阳才是太阳系中心",
                "冥王星已被归类为矮行星，不算八大行星",
                "太阳是恒星，不是行星",
            ],
            difficulty="easy",
        ))

        # 测试用例 3: 植物主题
        self.test_cases.append(TestCase(
            case_id="CASE-PLANT-001",
            title="植物的光合作用",
            topic="植物",
            target_audience="8-12岁儿童",
            original_content="""
植物和我们人类一样，都需要吃饭才能长大。
植物的食物就是土壤里的东西，它们用根把食物吸上来。

植物通过光合作用制造氧气，吸收二氧化碳。
光合作用发生在植物的根部，因为根在土壤里可以吸收阳光。
            """,
            reference_criteria=[
                "植物通过光合作用自己制造养分，不是从土壤里吸收食物",
                "光合作用主要发生在叶子里，不是根部",
            ],
            difficulty="medium",
        ))

    def get_test_case(self, case_id: str) -> Optional[TestCase]:
        """获取指定测试用例"""
        for case in self.test_cases:
            if case.case_id == case_id:
                return case
        return None

    def get_test_cases_by_topic(self, topic: str) -> List[TestCase]:
        """按主题获取测试用例"""
        return [c for c in self.test_cases if topic.lower() in c.topic.lower()]

    def evaluate(
        self,
        generated_content: str,
        test_case: TestCase,
    ) -> Dict[str, Any]:
        """
        评估生成的内容

        返回:
            {
                "overall_score": 0.85,
                "dimensions": {...},
                "issues_found": [...],
                "passed": true/false,
            }
        """
        issues_found = self._check_against_criteria(
            generated_content,
            test_case.reference_criteria or []
        )

        dimension_scores = self._evaluate_dimensions(
            generated_content,
            test_case
        )

        overall_score = sum(dimension_scores.values()) / max(1, len(dimension_scores))

        return {
            "case_id": test_case.case_id,
            "title": test_case.title,
            "overall_score": round(overall_score, 2),
            "dimensions": dimension_scores,
            "issues_found": issues_found,
            "total_criteria": len(test_case.reference_criteria or []),
            "criteria_met": len(test_case.reference_criteria or []) - len(issues_found),
            "passed": len(issues_found) == 0 and overall_score >= 0.7,
        }

    def _check_against_criteria(
        self,
        content: str,
        criteria: List[str],
    ) -> List[str]:
        """检查内容是否符合参考标准"""
        issues = []

        # 这里是简单的关键词匹配，实际使用时可以用 LLM
        content_lower = content.lower()

        # 检查恐龙相关
        if "四川" in content and "恐龙" in content:
            issues.append("恐龙灭绝地点可能有误（应为墨西哥，不是四川）")

        if "50米" in content and "腕龙" in content:
            issues.append("腕龙身高可能有误（应为12-15米，不是50米）")

        if "都是冷血动物" in content and "恐龙" in content:
            issues.append("恐龙温血/冷血表述可能不准确")

        if "没有恐龙会飞" in content or "没有恐龙会游泳" in content:
            issues.append("恐龙定义可能需要澄清（翼龙/蛇颈龙不是恐龙）")

        # 检查太阳系相关
        if "地球是宇宙的中心" in content or "太阳绕着地球" in content:
            issues.append("太阳系中心表述有误（应为太阳）")

        if "冥王星" in content and "八大行星" in content:
            issues.append("冥王星已被归类为矮行星")

        if "太阳是一颗行星" in content:
            issues.append("太阳是恒星，不是行星")

        # 检查植物相关
        if "光合作用发生在植物的根部" in content:
            issues.append("光合作用主要发生在叶子里")

        if "植物的食物就是土壤里的东西" in content:
            issues.append("植物通过光合作用自己制造养分")

        return issues

    def _evaluate_dimensions(
        self,
        content: str,
        test_case: TestCase,
    ) -> Dict[str, float]:
        """评估各个维度"""
        scores = {}

        # 科学准确性（基于发现的问题数量）
        issues = self._check_against_criteria(content, test_case.reference_criteria or [])
        total_criteria = max(1, len(test_case.reference_criteria or []))
        accuracy_score = max(0, (total_criteria - len(issues)) / total_criteria)
        scores[EvaluationDimension.SCIENTIFIC_ACCURACY.value] = accuracy_score

        # 儿童易懂性（简单评估：句子长度、用词复杂度）
        sentences = content.split("。")
        avg_sentence_length = sum(len(s) for s in sentences) / max(1, len(sentences))
        if avg_sentence_length < 30:
            understandability = 0.9
        elif avg_sentence_length < 50:
            understandability = 0.7
        else:
            understandability = 0.5
        scores[EvaluationDimension.UNDERSTANDABILITY.value] = understandability

        # 趣味性（简单评估：是否有问号、感叹号、生动的描述）
        has_questions = "？" in content or "?" in content
        has_exclamations = "！" in content or "!" in content
        interestingness = 0.7
        if has_questions:
            interestingness += 0.1
        if has_exclamations:
            interestingness += 0.1
        scores[EvaluationDimension.INTERESTINGNESS.value] = min(1.0, interestingness)

        # 知识点覆盖度（简单评估：内容长度）
        content_length = len(content)
        if content_length > 300:
            coverage = 0.9
        elif content_length > 200:
            coverage = 0.7
        elif content_length > 100:
            coverage = 0.5
        else:
            coverage = 0.3
        scores[EvaluationDimension.COVERAGE.value] = coverage

        # 组织性（简单评估：是否有分段、逻辑连接词）
        has_paragraphs = "\n" in content
        has_connectives = any(w in content for w in ["因为", "所以", "但是", "而且", "然后"])
        organization = 0.6
        if has_paragraphs:
            organization += 0.2
        if has_connectives:
            organization += 0.2
        scores[EvaluationDimension.ORGANIZATION.value] = min(1.0, organization)

        return scores

    def run_full_evaluation(self) -> Dict[str, Any]:
        """运行完整的基准测试"""
        results = []
        total_score = 0.0
        passed_count = 0

        print("=" * 80)
        print("KidsSciBench 评估基准测试")
        print("=" * 80)

        for case in self.test_cases:
            print(f"\n[测试用例] {case.case_id} - {case.title}")
            result = self.evaluate(case.original_content, case)
            results.append(result)

            total_score += result["overall_score"]
            if result["passed"]:
                passed_count += 1

            print(f"  总分: {result['overall_score']:.2f}")
            print(f"  通过: {'✓' if result['passed'] else '✗'}")
            print(f"  发现问题: {len(result['issues_found'])}")
            for issue in result['issues_found']:
                print(f"    - {issue}")

        avg_score = total_score / max(1, len(self.test_cases))
        pass_rate = passed_count / max(1, len(self.test_cases))

        print("\n" + "=" * 80)
        print("基准测试总结")
        print("=" * 80)
        print(f"测试用例总数: {len(self.test_cases)}")
        print(f"平均得分: {avg_score:.2f}")
        print(f"通过率: {pass_rate:.1%}")

        return {
            "results": results,
            "average_score": round(avg_score, 2),
            "pass_rate": round(pass_rate, 2),
            "total_cases": len(self.test_cases),
            "passed_count": passed_count,
        }


# 便捷函数
def create_kids_sci_bench() -> KidsSciBench:
    """创建 KidsSciBench 实例"""
    return KidsSciBench()


if __name__ == "__main__":
    bench = create_kids_sci_bench()
    bench.run_full_evaluation()
