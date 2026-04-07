#!/usr/bin/env python3
"""
科学审查RAG库初始化脚本
用于快速填充科学事实知识库数据
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import models
from sqlalchemy import func
from sqlalchemy.orm import Session
from utils.database import SessionLocal
from utils.science_collector import get_science_collector, ingest_collected_articles


def collect_from_sites(db: Session, per_site_limit: int = 3) -> int:
    """从五个科普网站采集内容并入库到 SCIENCE_FACT。"""
    print("\n" + "=" * 60)
    print("正在从科普网站采集内容（SCIENCE_FACT）...")
    print("=" * 60)

    collector = get_science_collector()

    sites = [
        ("kepu_gov_cn", "科普中国"),
        ("cas_voice", "中科院之声"),
        ("kepu_net_cn", "中国科普博览"),
        ("sciencenet_cn", "科学网博客"),
        ("guokr_com", "果壳网"),
    ]

    total_collected = 0
    total_ingested = 0

    for site_id, site_name in sites:
        print(f"\n正在采集: {site_name}...")
        try:
            articles = collector.collect_from_site(site_id, limit=per_site_limit)
            if not articles:
                print("  未采集到文章")
                continue

            print(f"  采集到 {len(articles)} 篇文章")
            total_collected += len(articles)

            ingested = ingest_collected_articles(db, articles, doc_type="SCIENCE_FACT")
            print(f"  成功入库 {len(ingested)} 篇")
            total_ingested += len(ingested)
        except Exception as e:
            print(f"  采集失败: {e}")

    print(f"\n网站采集完成: 共采集 {total_collected} 篇，入库 {total_ingested} 篇")
    return total_ingested


def cleanup_creator_style_docs(db: Session) -> int:
    """删除 CREATOR_STYLE 历史数据，避免影响当前科学审查库。"""
    creator_docs = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.doc_type == "CREATOR_STYLE").all()
    if not creator_docs:
        print("未发现 CREATOR_STYLE 历史文档，无需清理。")
        return 0

    doc_ids = [d.id for d in creator_docs]
    chunk_deleted = (
        db.query(models.KnowledgeChunk)
        .filter(models.KnowledgeChunk.document_id.in_(doc_ids))
        .delete(synchronize_session=False)
    )
    doc_deleted = (
        db.query(models.KnowledgeDocument)
        .filter(models.KnowledgeDocument.id.in_(doc_ids))
        .delete(synchronize_session=False)
    )
    db.commit()

    print(f"已清理 CREATOR_STYLE 历史数据: 文档 {doc_deleted} 条, 分块 {chunk_deleted} 条")
    return int(doc_deleted)


def show_stats(db: Session):
    """显示知识库统计信息。"""
    print("\n" + "=" * 60)
    print("知识库统计")
    print("=" * 60)

    total_docs = db.query(func.count(models.KnowledgeDocument.id)).scalar() or 0
    total_chunks = db.query(func.count(models.KnowledgeChunk.id)).scalar() or 0

    doc_type_counts = {}
    rows = (
        db.query(models.KnowledgeDocument.doc_type, func.count(models.KnowledgeDocument.id).label("count"))
        .group_by(models.KnowledgeDocument.doc_type)
        .all()
    )
    for row in rows:
        doc_type_counts[row.doc_type] = row.count

    print(f"总文档数: {total_docs}")
    print(f"总分块数: {total_chunks}")
    print(f"文档类型分布: {doc_type_counts}")


def main():
    print("=" * 60)
    print("科学审查RAG库初始化脚本")
    print("=" * 60)

    db = SessionLocal()
    try:
        print("\n[步骤1] 清理创作者RAG历史数据（CREATOR_STYLE）...")
        cleanup_creator_style_docs(db)

        print("\n[步骤2] 从科普网站采集 SCIENCE_FACT 数据...")
        choice = input("是否从科普网站采集内容？(y/n，默认y): ").strip().lower()
        if choice in ("", "y"):
            limit = input("每个网站采集几篇？(默认3): ").strip()
            per_site_limit = int(limit) if limit.isdigit() else 3
            collect_from_sites(db, per_site_limit=per_site_limit)
        else:
            print("跳过网站采集。")

        print("\n[步骤3] 查看统计信息...")
        show_stats(db)

        print("\n" + "=" * 60)
        print("初始化完成！")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    main()#!/usr/bin/env python3
"""
创作者RAG库初始化脚本
用于快速填充初始知识库数据
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from utils.database import SessionLocal
from utils.fact_rag import index_fact_document
from utils.science_collector import get_science_collector, ingest_collected_articles


def init_sample_creator_style_docs(db: Session):
    """
    初始化创作者风格库的示例数据
    包含经典获奖科普作品片段
    """
    sample_docs = [
        {
            "source_name": "小灵通漫游未来（节选）",
            "source_url": "",
            "publisher": "少年儿童出版社",
            "author": "叶永烈",
            "publish_year": 1978,
            "authority_level": 95,
            "doc_type": "CREATOR_STYLE",
            "topic_tags": ["科幻", "未来科技", "经典"],
            "audience_tags": ["6-12岁", "小学", "青少年"],
            "style_tags": ["故事型", "探险型", "科幻"],
            "award_tags": ["全国优秀科普作品奖"],
            "content": """
第一章 不翼而飞的水滴
清晨的阳光透过窗帘，照在小明床边的玻璃杯上。
"咦？昨晚杯里还有半杯水，怎么现在变少了？"小明揉揉眼睛，奇怪地自言自语。

他把鼻子凑到杯口闻了闻，没有酒味；用手指沾了一点尝尝，也没有咸味。这水究竟到哪儿去了呢？

正在这时，爸爸走进来了。他是位中学化学教师，一眼就看出了小明的心事。
"是在找那半杯水吗？"爸爸笑着说，"它蒸发了，飞到空中去啦！"

"蒸发？"小明更加奇怪了，"水怎么会蒸发呢？我怎么没看见？"

"来，我给你做个实验。"爸爸说着，从厨房里拿来一把水壶，灌了半壶水放在煤气炉上烧。

"注意看！"爸爸说。
小明睁大眼睛，注视着水壶。没过多久，水壶里的水开始翻腾，冒出白色的蒸汽。
"看，这就是水蒸发！"爸爸指着蒸汽说，"水变成了水蒸气，跑到空气中去了。"

"那为什么平时看不见呢？"小明问。
"那是因为温度不够高，水蒸发得很慢很慢，所以我们不容易发现。"爸爸解释说，"不过，只要你留心观察，到处都能看到蒸发现象。"
"""
        },
        {
            "source_name": "十万个为什么：为什么天空是蓝色的",
            "source_url": "",
            "publisher": "少年儿童出版社",
            "author": "叶永烈等",
            "publish_year": 1961,
            "authority_level": 95,
            "doc_type": "CREATOR_STYLE",
            "topic_tags": ["光学", "大气科学", "经典"],
            "audience_tags": ["6-12岁", "小学"],
            "style_tags": ["问答型", "趣味科普"],
            "award_tags": ["全国优秀科普作品奖"],
            "content": """
为什么天空是蓝色的？

如果有人问你："天空是什么颜色的？"你一定会脱口而出："蓝色的！"

可是，你想过没有：天空为什么是蓝色的呢？

也许你会说："因为天空里有蓝色的气体！"不对！空气是没有颜色的，是透明的。

那为什么晴朗的天空总是蓝色的呢？这得从阳光说起。

我们平常看到的阳光，好像是白色的，其实它是由红、橙、黄、绿、蓝、靛、紫七种颜色的光组成的。

当阳光穿过大气层时，会遇到空气中的尘埃和小水滴。这些微粒会把阳光散射开来。

有趣的是，不同颜色的光被散射的程度不一样：红色、橙色这些波长较长的光，能够穿过大气层直接射到地面；而蓝色、紫色这些波长较短的光，很容易被空气中的微粒散射开来，布满整个天空。

所以，我们看到的天空就是蔚蓝色的了！

傍晚的时候，太阳落山了，阳光要穿过更厚的大气层才能到达地面。这时候，蓝色的光被散射得更厉害，只剩下红色和橙色的光能到达地面，所以傍晚的天空总是红彤彤的。

你看，大自然多奇妙啊！
"""
        },
        {
            "source_name": "法布尔昆虫记：蝉（节选）",
            "source_url": "",
            "publisher": "中国少年儿童出版社",
            "author": "法布尔",
            "publish_year": 2000,
            "authority_level": 90,
            "doc_type": "CREATOR_STYLE",
            "topic_tags": ["生物学", "昆虫", "观察"],
            "audience_tags": ["8-15岁", "中小学"],
            "style_tags": ["观察型", "故事型"],
            "award_tags": ["经典科普作品"],
            "content": """
蝉的故事

每年夏天，蝉都会准时来到我们的树林里。它们是大自然的歌手，从早到晚唱个不停。

可是，你知道吗？蝉为了这一个月的阳光歌唱，在地下整整等待了四年！

让我来讲讲蝉的故事吧。

蝉妈妈会在夏天的傍晚，把卵产在树枝的树皮里。她用尖尖的产卵器，在树枝上刺出一排小坑，每个小坑里放几颗卵。

卵孵化后，小幼虫从树枝里爬出来，落到地上。它们马上就会用前爪挖一个小洞，钻到地下。

这一钻，就是四年！

在黑暗的地下，小蝉幼虫靠吸食树根的汁液生活。它们一次又一次地蜕皮，慢慢长大。

四年后的夏天，成熟的蝉幼虫会从地下钻出来，爬到附近的树上。这时候，它们要进行最后一次蜕皮——变成会飞的蝉！

蜕皮的过程非常奇妙。蝉的背部会裂开一条缝，蝉就从这条缝里慢慢钻出来。刚出来的蝉是浅绿色的，翅膀还很软。

过了几个小时，蝉的翅膀变硬了，身体也变成了深色。这时，它就可以飞到树枝上，开始它的歌唱生涯了。

蝉在阳光下只能活一个月左右。在这短短的时间里，它们要完成传宗接代的任务，然后就会死去。

四年黑暗中的等待，一个月阳光下的歌唱——这就是蝉的一生。
"""
        },
        {
            "source_name": "神奇校车：水的故事（节选）",
            "source_url": "",
            "publisher": "四川少年儿童出版社",
            "author": "乔安娜·柯尔",
            "publish_year": 2011,
            "authority_level": 90,
            "doc_type": "CREATOR_STYLE",
            "topic_tags": ["水", "水循环", "探险"],
            "audience_tags": ["4-10岁", "幼儿园小学"],
            "style_tags": ["探险型", "漫画", "趣味"],
            "award_tags": ["美国科普图书奖"],
            "content": """
神奇校车：水的故事

"同学们，今天我们要学习什么是水！"弗瑞丝小姐说。

话音刚落，神奇校车就变了——它变成了一架小飞机，而且越来越小，越来越小！

"抓紧了！"弗瑞丝小姐大喊，"我们要变成水滴啦！"

哇！我们真的变成了水滴，飘到了天上的云朵里。

云朵里可真热闹！成千上万的小水滴挤在一起，撞来撞去。

"当小水滴越聚越多，云朵就变重了，"弗瑞丝小姐解释说，"然后就会下雨啦！"

正说着，我们就跟着大部队从云朵里掉了下去——下雨啦！

我们掉到了一条小溪里，跟着溪水向前流。小溪流进小河，小河又流进大河，最后我们来到了大海。

在大海里，太阳公公把我们晒得暖洋洋的。慢慢地，我们变轻了，升到了空中——这就是蒸发！

在空中，我们遇冷又变成了小水滴，聚在一起变成了云。

"你们看！"弗瑞丝小姐说，"这就是水循环：蒸发→云→雨→河→海→蒸发，循环往复，永不停息！"

太神奇了！原来一滴水也有这么精彩的旅行故事！
"""
        },
        {
            "source_name": "细菌世界历险记（节选）",
            "source_url": "",
            "publisher": "科学出版社",
            "author": "高士其",
            "publish_year": 1941,
            "authority_level": 95,
            "doc_type": "CREATOR_STYLE",
            "topic_tags": ["微生物", "细菌", "经典"],
            "audience_tags": ["10-16岁", "中小学"],
            "style_tags": ["自述型", "故事型"],
            "award_tags": ["全国优秀科普作品奖"],
            "content": """
细菌的自白

小朋友，你们好！我是细菌，是你们肉眼看不见的小不点儿。

在你们看来，我也许是个坏蛋，会让人生病。其实，这对我不太公平——我们细菌家族里，也有很多好人！

先说说我的样子吧。我很小很小，把一千个细菌排在一起，才有一粒米那么大。所以，你们不用显微镜，根本看不见我。

我们细菌的模样各种各样：有的像小圆球，叫球菌；有的像小木棍，叫杆菌；还有的弯弯的，叫螺旋菌。

我们的繁殖速度可快了！只要温度合适，营养充足，一个细菌过二十分钟就能变成两个，再过二十分钟变成四个。这样下去，一天就能繁殖好几亿个！

不过，你们也别害怕，因为大多数细菌都是对人类有益的。

比如，土壤里的细菌能把动植物的尸体分解成肥料，让庄稼长得更好；还有些细菌能帮助人类制造食物，比如酸奶、泡菜、酱油、醋，这些都离不开我们细菌。

当然，我们家族里确实有些坏家伙，会让人生病。不过，只要你们讲卫生，勤洗手，就能把它们挡在身体外面啦！

你看，我们细菌是不是也挺有意思的？
"""
        },
    ]

    print(f"正在添加 {len(sample_docs)} 篇示例创作者文档...")
    count = 0
    for doc in sample_docs:
        try:
            result = index_fact_document(db, doc)
            print(f"  ✓ 已添加: {doc['source_name']} (文档ID: {result['document_id']}, 分块: {result['chunk_count']})")
            count += 1
        except Exception as e:
            print(f"  ✗ 添加失败: {doc['source_name']}, 错误: {e}")

    print(f"创作者风格示例文档添加完成: {count}/{len(sample_docs)}")
    return count


def collect_from_sites(db: Session, per_site_limit: int = 3):
    """
    从五个科普网站采集内容
    """
    print("\n" + "="*60)
    print("正在从科普网站采集内容...")
    print("="*60)

    collector = get_science_collector()

    sites = [
        ("kepu_gov_cn", "科普中国"),
        ("cas_voice", "中科院之声"),
        ("kepu_net_cn", "中国科普博览"),
        ("sciencenet_cn", "科学网博客"),
        ("guokr_com", "果壳网"),
    ]

    total_collected = 0
    total_ingested = 0

    for site_id, site_name in sites:
        print(f"\n正在采集: {site_name}...")
        try:
            articles = collector.collect_from_site(site_id, limit=per_site_limit)
            if articles:
                print(f"  采集到 {len(articles)} 篇文章")
                total_collected += len(articles)

                # 入库
                ingested = ingest_collected_articles(db, articles, doc_type="CREATOR_STYLE")
                print(f"  成功入库 {len(ingested)} 篇")
                total_ingested += len(ingested)
            else:
                print(f"  未采集到文章")
        except Exception as e:
            print(f"  采集失败: {e}")

    print(f"\n网站采集完成: 共采集 {total_collected} 篇，入库 {total_ingested} 篇")
    return total_ingested


def show_stats(db: Session):
    """
    显示知识库统计信息
    """
    from sqlalchemy import func
    from models import models

    print("\n" + "="*60)
    print("知识库统计")
    print("="*60)

    total_docs = db.query(func.count(models.KnowledgeDocument.id)).scalar() or 0
    total_chunks = db.query(func.count(models.KnowledgeChunk.id)).scalar() or 0

    # 按类型统计
    doc_type_counts = {}
    rows = db.query(
        models.KnowledgeDocument.doc_type,
        func.count(models.KnowledgeDocument.id).label("count")
    ).group_by(models.KnowledgeDocument.doc_type).all()
    for row in rows:
        doc_type_counts[row.doc_type] = row.count

    print(f"总文档数: {total_docs}")
    print(f"总分块数: {total_chunks}")
    print(f"文档类型分布: {doc_type_counts}")

    # 最近文档
    recent_docs = db.query(models.KnowledgeDocument).order_by(
        models.KnowledgeDocument.created_at.desc()
    ).limit(5).all()

    print("\n最近添加的文档:")
    for doc in recent_docs:
        print(f"  - {doc.source_name} ({doc.doc_type})")


def main():
    print("="*60)
    print("创作者RAG库初始化脚本")
    print("="*60)

    db = SessionLocal()
    try:
        # 1. 添加示例文档
        print("\n[步骤1] 添加创作者风格示例文档...")
        sample_count = init_sample_creator_style_docs(db)

        # 2. 从网站采集
        print("\n[步骤2] 从科普网站采集内容...")
        choice = input("是否从科普网站采集内容？(y/n，默认n): ").strip().lower()
        if choice == 'y':
            limit = input("每个网站采集几篇？(默认3): ").strip()
            limit = int(limit) if limit.isdigit() else 3
            collect_from_sites(db, per_site_limit=limit)
        else:
            print("跳过网站采集。")

        # 3. 显示统计
        show_stats(db)

        print("\n" + "="*60)
        print("初始化完成！")
        print("="*60)

    finally:
        db.close()


if __name__ == "__main__":
    main()
