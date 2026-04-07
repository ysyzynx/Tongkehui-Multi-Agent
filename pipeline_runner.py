import os
import json
from agent.story_creator import StoryCreatorAgent
from agent.literature_checker import LiteratureCheckerAgent
from agent.science_checker import ScienceCheckerAgent
from agent.reader import ReaderAgent
from agent.illustrator import IllustratorAgent
from agent.publisher import PublisherAgent
from utils.pdf_generator import PDFGenerator

def run_pipeline():
    print("="*60)
    print("🚀 欢迎使用【童科绘】全自动科普绘本生成工作流 🚀")
    print("="*60)

    # 1. 采用交互式输入方式获取所有参数
    print("\n📝 请按提示依次输入您的设定 (直接回车将使用默认值)")
    
    theme_input = input("\n1. 请输入主题 (默认: '令人惊奇的科学现象') ➠ ").strip()
    theme = theme_input if theme_input else "令人惊奇的科学现象"
    
    age_input = input("\n2. 请输入年龄段 (默认: '全年龄段') ➠ ").strip()
    age_group = age_input if age_input else "全年龄段"
    
    style_input = input("\n3. 请输入文章风格 (默认: '趣味科普') ➠ ").strip()
    style = style_input if style_input else "趣味科普"

    print("\n4. 【科普对象类型选择】(请选择 1-5，直接回车则默认'全年龄段普通大众'):")
    print("  [1] 青少幼年儿童 ")
    print("  [2] 产业工人")
    print("  [3] 老年人")
    print("  [4] 领导干部和公务员")
    print("  [5] 农民")
    target_num = input("请选择您的科普对象 ➠ ").strip()
    
    target_map = {
        "1": "青少幼年儿童（核心目标：科学基础启蒙认知、激发好奇心、想象力，培养科学兴趣，语言生动易懂且贴近生活）",
        "2": "产业工人（核心目标：技能提升、职业创新、工匠精神）",
        "3": "老年人（核心目标：健康科普、跨越“数字鸿沟”、防诈骗）",
        "4": "领导干部和公务员（核心目标：科学决策能力、生态文明理念）",
        "5": "农民（核心目标：乡村振兴、移风易俗、现代农业技术）"
    }
    target_audience = target_map.get(target_num, "全年龄段普通大众")

    if target_num == "1":
        print("\n  👉 您选择了【青少幼年儿童】，请进一步选择具体群体 (直接回车默认'少年及青年 6-18岁'):")
        print("    [1] 幼年（3-6岁，目标：科学基础启蒙认知、简单趣味、语言极其生动易懂）")
        print("    [2] 少年（6-12岁，目标：激发好奇心、想象力，培养科学兴趣）")
        print("    [3] 青年（12-28岁，目标：深入科学原理，树立科学价值观）")
        sub_target_num = input("  请选择细分群体 ➠ ").strip()
        
        if sub_target_num == "1":
            target_audience = "幼年儿童（3-6岁）（核心目标：科学基础启蒙认知、简单趣味、语言极其生动易懂且贴近生活）"
        elif sub_target_num == "2":
            target_audience = "少儿群体（6-12岁）（核心目标：激发好奇心、想象力，培养并在实践中探索科学兴趣）"
        elif sub_target_num == "3":
            target_audience = "青少年群体（12-28岁）（核心目标：深入理解科学原理，树立正确的科学价值观）"

    print("\n5. 【自定义故事要求】")
    extra_requirements = input("是否有其他特殊编剧要求？（例如：主角是小猫 等。直接回车跳过） ➠ ").strip()

    print("\n6. 【绘画配图设定】")
    print("请选择绘本画面风格 (默认: '卡通风格，色彩鲜艳明快'):")
    print("  [1] 卡通")
    print("  [2] 儿童绘画")
    print("  [3] 水彩画")
    print("  [4] 写真")
    print("  [5] 3D渲染")
    style_num = input("请选择绘画风格 ➠ ").strip()
    
    style_map = {
        "1": "卡通风格，色彩鲜艳明快",
        "2": "儿童绘画风格，色彩鲜艳明快",
        "3": "水彩画风格，色彩鲜艳明快",
        "4": "写真风格，色彩鲜艳明快",
        "5": "3D渲染风格，色彩鲜艳明快"
    }
    art_style = style_map.get(style_num, "卡通风格，色彩鲜艳明快")

    print("\n7. 【自定义额外绘画要求】")
    extra_draw_req = input("例如：'主角必须是一只戴眼镜的蓝色小猫'。若无额外要求，请直接回车跳过 ➠ ").strip()
    
    image_count_input = input("\n8. 请输入分镜插图数量 (默认: 3张) ➠ ").strip()
    image_count = int(image_count_input) if image_count_input.isdigit() else 3

    print(f"\n【最终设定总结】")
    print(f"- 主题: {theme}")
    print(f"- 年龄段: {age_group}")
    print(f"- 风格: {style}")
    print(f"- 目标受众: {target_audience}")
    print(f"- 故事额外要求: {extra_requirements if extra_requirements else '无'}")
    print(f"- 画风: {art_style} (共 {image_count} 张)")
    print(f"- 绘画额外要求: {extra_draw_req if extra_draw_req else '无'}\n")

    # --- Step 1: 故事创作 ---
    print("="*60)
    print("📝 [Step 1/6] 故事初创中 (StoryCreatorAgent) ...")
    creator = StoryCreatorAgent()
    story_result = creator.run(
        theme=theme,
        age_group=age_group,
        style=style,
        target_audience=target_audience,
        extra_requirements=extra_requirements
    )
    
    title = story_result.get("title", theme)
    content = story_result.get("content", "")
    print(f"✅ 初稿完成！标题：《{title}》 (总字数: {len(content)})")
    print(f"\n【Creator 初稿正文】\n{content}\n")


    # --- Step 2: 文学润色 ---
    print("="*60)
    print("✒️  [Step 2/6] 文学评委润色中 (LiteratureCheckerAgent) ...")
    lit_checker = LiteratureCheckerAgent()
    lit_result = lit_checker.review_story(title, content)
    
    # 继承润色后的版本
    if "revised_content" in lit_result:
        content = lit_result["revised_content"]
        
    print("✅ 文学润色完毕！")
    print(f"💡 综合评价与修改意见：\n{lit_result.get('feedback', '无')} ")
    print(f"\n【LiteratureChecker 润色后正文】\n{content}\n")


    # --- Step 3: 科学勘误与提取 ---
    print("="*60)
    print("🔬 [Step 3/6] 科学评委审查中 (ScienceCheckerAgent) ...")
    sci_checker = ScienceCheckerAgent()
    sci_result = sci_checker.run(story_title=title, story_content=content, target_audience=target_audience)
    
    # 获取科学订正后的最终版本和词汇表
    if "revised_content" in sci_result:
        content = sci_result["revised_content"]
    glossary = sci_result.get("revised_glossary", [])
    
    print("✅ 科学审查完毕！")
    if sci_result.get("issues"):
        print("🔧 发现并修正了以下科学漏洞：")
        for idx, issue in enumerate(sci_result["issues"]):
            print(f"  {idx+1}. {issue}")
    else:
        print("🌟 科学性极佳，未发现明显学术漏洞！")
        
    print(f"📚 提取到了 {len(glossary)} 个科普知识词条。")
    if glossary:
        print("\n【科普词汇表】")
        for item in glossary:
            print(f"  - {item.get('term', '未知词汇')}: {item.get('explanation', '')}")
            
    print(f"\n【ScienceChecker 终修版正文】\n{content}\n")


    # --- Step 4: 虚拟读者试读 ---
    print("="*60)
    print("👀 [Step 4/6] 虚拟读者试读与反馈 (ReaderAgent) ...")
    reader = ReaderAgent()
    reader_result = reader.run(story_content=content, title=title, target_audience=target_audience)
    
    print("✅ 读者试读完毕！")
    print(f"💬 读者读后感：\n{reader_result.get('reader_feedback', '无')}\n")


    # --- Step 5: 插画分镜与生成 ---
    print("="*60)
    print(f"🎨 [Step 5/6] 插画师正在根据故事分镜并绘图 (IllustratorAgent, 预计 {image_count} 幕) ...")
    illustrator = IllustratorAgent()
    illustrations = illustrator.run(
        story_content=content, 
        image_count=image_count, 
        art_style=art_style,
        extra_requirements=extra_draw_req
    )
    
    # 容错处理
    if isinstance(illustrations, dict) and "error" in illustrations:
        print(f"❌ 插画生成失败：{illustrations['error']}")
        illustrations = []
    
    print("✅ 插画步骤完成！")
    for img in illustrations:
        if isinstance(img, dict):
            # IllustratorAgent 返回的 JSON 键是 'summary' 和 'image_prompt'，不是 'description'
            scene_desc = img.get('summary', '') or img.get('image_prompt', '无描述')
            print(f"  - 幕 {img.get('scene_id', '?')}: {scene_desc}")
            print(f"    🌟 提示词: {img.get('image_prompt', '无')}")
            print(f"    🔗 链接: {img.get('image_url', '')}")
            print()


    # --- Step 6: 网页排版与 PDF 输出 ---
    print("="*60)
    print("🖨️  [Step 6/6] 最终排版与导出 PDF (PublisherAgent & PDFGenerator) ...")
    publisher = PublisherAgent()
    html_code = publisher.compile_to_html(title, content, glossary, illustrations)
    
    # 确保存储目录 article 存在（使用绝对路径）
    output_dir = r"E:\童科绘\article"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 已创建输出文件夹: {output_dir}")
        
    safe_title = title.replace("？", "").replace("！", " ").replace(":", "-").replace("：", "-").strip()
    
    output_html_name = os.path.join(output_dir, f"{safe_title}.html")
    with open(output_html_name, "w", encoding="utf-8") as f:
        f.write(html_code)
    print(f"✅ HTML 排版完成！已保存为：{output_html_name}")

    pdf_generator = PDFGenerator()
    output_pdf_name = os.path.join(output_dir, f"{safe_title}.pdf")
    print(f"转码 PDF 中...\n")
    final_pdf_path = pdf_generator.html_to_pdf(html_code, output_pdf_name)
    
    print("="*60)
    print(f"🎉 大功告成！全流程运行完毕！")
    print(f"📖 您可以前往查看最终的电子科普绘本：{final_pdf_path}")
    print("="*60)


if __name__ == "__main__":
    run_pipeline()