"""
知识图谱可视化页面路由
提供HTML可视化页面
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter(tags=["Knowledge Graph Visualizer"])

# 获取可视化HTML文件路径
KG_VISUALIZER_PATH = Path(__file__).parent.parent / "kg_visualizer.html"


@router.get("/kg-visualizer", response_class=HTMLResponse)
async def get_kg_visualizer():
    """
    知识图谱可视化页面

    直接在浏览器中打开此页面即可查看知识图谱可视化
    """
    if KG_VISUALIZER_PATH.exists():
        with open(KG_VISUALIZER_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        # 如果文件不存在，返回一个简单的提示页面
        return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>知识图谱可视化</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 80px auto;
            padding: 20px;
            text-align: center;
        }
        h1 { color: #667eea; }
        .info { background: #f0f0f0; padding: 20px; border-radius: 10px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>📊 知识图谱可视化</h1>
    <div class="info">
        <p>请确保 <code>kg_visualizer.html</code> 文件存在于项目根目录下。</p>
        <p>您也可以直接在浏览器中打开该文件。</p>
    </div>
    <p><a href="/docs">查看API文档 →</a></p>
</body>
</html>
        """)


@router.get("/kg-visualizer/raw")
async def get_kg_visualizer_raw():
    """
    获取可视化页面的原始HTML内容
    """
    if KG_VISUALIZER_PATH.exists():
        with open(KG_VISUALIZER_PATH, "r", encoding="utf-8") as f:
            return {"html": f.read(), "path": str(KG_VISUALIZER_PATH)}
    else:
        return {"error": "File not found", "expected_path": str(KG_VISUALIZER_PATH)}
