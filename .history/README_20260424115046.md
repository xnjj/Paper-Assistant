# RAG Paper Assistant

基于 `Python + Vue + Electron` 的桌面论文助手骨架项目，目标是逐步演进成一个支持本地文献入库、RAG 检索、外部检索、引用生成和文献综述修订的桌面应用。

当前仓库里原有的 `paper_review.py`、`paper_daily_get.py` 等脚本已保留，新的工程骨架放在以下目录：

```text
backend/   FastAPI 后端、OpenAI 调用、知识库与数据层
frontend/  Vue 3 + Vite 前端
desktop/   Electron 桌面壳
```

## 已搭好的能力

- 后端 FastAPI 应用骨架
- SQLite 元数据存储模型
- 本地论文记录、PDF 上传接口
- arXiv 检索接口
- Google Scholar / 知网 / arXiv 浏览器打开接口
- OpenAI 文献综述生成与修订服务封装
- 本地知识库 Markdown 索引文件生成
- Vue 工作台、知识库、检索、综述页面骨架
- Electron 主进程与 preload 骨架

## 快速启动

### 1. 配置环境变量

将根目录 `.env.example` 复制为 `.env`，至少补充：

```bash
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

### 2. 启动后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

### 3. 启动前端与桌面壳

```bash
npm install
npm run dev
```

默认情况下：

- 前端开发服务器运行在 `http://127.0.0.1:5173`
- 后端 API 运行在 `http://127.0.0.1:8000`
- Electron 会加载前端开发服务器

## 下一步建议

1. 将现有 `paper_review.py` 中的 PDF 解析逻辑迁移到 `backend/app/services/library_service.py`
2. 将向量库存储接入 `backend/app/services/knowledge_base_service.py`
3. 将提示词和编排逻辑继续细化到 `backend/app/agents/review_agent.py`
4. 在前端补充真实文件上传、任务进度和错误提示
