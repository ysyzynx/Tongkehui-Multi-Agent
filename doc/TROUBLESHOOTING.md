# 问题诊断与解决指南

## 常见问题

### 1. "API 请求失败: 500 Internal Server Error"

#### 原因分析
这个错误表示后端服务器正在运行，但在处理请求时出现了内部错误。

#### 解决步骤

**步骤 1: 确认后端服务正在运行**

打开一个新的终端窗口，运行：

```bash
cd E:\童科绘
python main.py
```

你应该看到类似这样的输出：
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**步骤 2: 检查后端日志**

查看运行后端的终端窗口，看看是否有错误信息。常见的错误包括：
- 缺少依赖包
- 数据库连接问题
- LLM API 密钥问题
- 端口被占用

**步骤 3: 测试健康检查接口**

打开浏览器访问：`http://localhost:8000/`

或者使用 curl：
```bash
curl http://localhost:8000/
```

应该返回：
```json
{"code":200,"msg":"API is running normally.","data":{"status":"ok"}}
```

**步骤 4: 使用测试脚本**

我已经创建了一个测试脚本 `test_backend.py`，运行它来诊断问题：

```bash
cd E:\童科绘
python test_backend.py
```

### 2. "无法连接到后端服务器"

#### 原因分析
前端无法连接到后端，可能是后端没有运行，或者连接地址配置错误。

#### 解决步骤

**步骤 1: 确认后端正在运行**

见上面的步骤 1。

**步骤 2: 检查 Vite 代理配置**

确认 `tk-frontend/vite.config.ts` 中有正确的代理配置：

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
  '/docs': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
}
```

**步骤 3: 检查环境变量**

确认 `tk-frontend/.env` 中的配置：
```
VITE_API_BASE_URL=auto
```

### 3. 生成故事时出错

#### 可能的原因
- LLM API 密钥无效或过期
- API 额度不足
- 网络连接问题
- 提示词过长

#### 解决步骤

**步骤 1: 检查 API 密钥**

确认 `.env` 文件中的 `OPENAI_API_KEY` 是有效的。

**步骤 2: 测试 API 连接**

检查是否能访问通义千问 API。

**步骤 3: 查看后端日志**

后端日志会显示详细的错误信息。

### 4. 前端页面无法加载

#### 解决步骤

**步骤 1: 确认前端正在运行**

```bash
cd E:\童科绘\tk-frontend
npm install
npm run dev
```

**步骤 2: 清除浏览器缓存**

- 按 `Ctrl + Shift + R` (Windows) 或 `Cmd + Shift + R` (Mac) 硬刷新页面
- 或者在无痕模式下打开

## 快速启动检查清单

在开始使用前，请确认：

- [ ] 后端服务正在运行 (`python main.py`)
- [ ] 前端服务正在运行 (`npm run dev` 在 tk-frontend 目录)
- [ ] 后端端口 8000 没有被占用
- [ ] 前端端口 5173 没有被占用
- [ ] `.env` 文件中有有效的 API 密钥
- [ ] 已安装所有 Python 依赖 (`pip install -r requirements.txt`)
- [ ] 已安装所有 npm 依赖 (`npm install` 在 tk-frontend 目录)

## 获取更多帮助

如果以上步骤都不能解决问题：

1. 收集后端日志中的错误信息
2. 收集浏览器控制台中的错误信息 (按 F12 打开开发者工具)
3. 检查 `E:\童科绘\docs` 目录下的其他文档
