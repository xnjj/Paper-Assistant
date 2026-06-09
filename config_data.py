from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent

# ---------------------------- 环境配置 ----------------------------
OPENAI_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

# ---------------------------- 检索配置 ----------------------------
TOP_K = 50                              # 本地向量召回候选 chunk 数
KEYWORD_RECALL_K = 50                   # 关键词 BM25 召回候选 chunk 数，最终会与向量召回做融合
HYBRID_RRF_K = 60                       # RRF 融合平滑系数，值越大越强调多路召回共同命中
HYBRID_CANDIDATE_LIMIT = 50             # RRF 融合后送入本地重排器的最大候选 chunk 数
RECALL_K = 20                           # 本地重排后保留并送入问答的 chunk 数

# ---------------------------- 重排配置 ----------------------------
RERANK_PROVIDER = os.getenv("RAG_RERANK_PROVIDER", "qwen")  # 本地候选重排器：qwen 或 rule
RERANK_MODEL_NAME = os.getenv("RAG_RERANK_MODEL_NAME", "gte-rerank-v2")  # DashScope 重排模型名
QWEN_RERANK_ENDPOINT = os.getenv(
    "QWEN_RERANK_ENDPOINT",
    "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
)  # qwen3-rerank HTTP 接口地址
RERANK_TIMEOUT_SECONDS = 30             # 单次重排请求超时时间
RERANK_MAX_DOCUMENTS = 100              # rerank 模型单次送入重排模型的最大候选数
RERANK_MAX_DOC_CHARS = 4000             # rerank 模型单个候选文本最大 token 数，避免超过模型输入上限
RERANK_FALLBACK_TO_RULE = True          # 云端重排失败时是否自动回退到规则重排
RERANK_INSTRUCTION = "根据用户问题，判断候选论文片段是否能直接支撑回答，并按相关性从高到低排序。"

MAX_PARALLEL_EXTERNAL_QUERIES = 3       # 单个外部数据源最大并发请求查询数，防止过大被限流
MAX_PARALLEL_CROSSREF_QUERIES = 5       # CROSSREF最大并发请求查询数
MAX_PARALLEL_LLM_QUERIES = 10           # 最大并发 LLM 请求数
MAX_EXTERNAL_QUERY_LIMIT = 10            # 单个外部数据源单次请求查询返回限制，防止过大被限流
DEFAULT_EXTERNAL_FINAL_LIMIT = 20       # 所有外部数据源检索返回总数限制
MAX_SEARCH_NUM = 20                     # 本地+外部检索总返回数限制

# ---------------------------- 语义分块配置 ----------------------------
SEMANTIC_CHUNK_PAGES_PER_BATCH = 3      # 每个语义结构识别任务读取的 PDF 最大页数
SEMANTIC_CHUNK_MAX_WORKERS_PER_DOCUMENT = 3     # 单篇文献内部最多并发多少个结构识别任务；真实 LLM 总并发仍受 MAX_PARALLEL_LLM_QUERIES 统一限制。

OUTPUT_DIR = os.getenv("RAG_PAPER_ASSISTANT_DATA_DIR", str(ROOT_DIR / "daily_papers"))
APP_DB_FILE = str(Path(OUTPUT_DIR) / "app_state.db")
DATABASE_FILE = str(Path(OUTPUT_DIR) / "chroma_db")
DATABASE_TABLE = "papers_collection"
CONFIGURED_FOLDER_ROOT = str(Path(OUTPUT_DIR) / "configured_folders")
RUNTIME_CONFIG_FILE = str(Path(OUTPUT_DIR) / "runtime_config.json")

DEFAULT_PAPER_FOLDER = str(ROOT_DIR / "paper_demo")

def ensure_runtime_directories() -> None:
    """确保运行期所需目录存在。"""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(CONFIGURED_FOLDER_ROOT).mkdir(parents=True, exist_ok=True)
    Path(DATABASE_FILE).mkdir(parents=True, exist_ok=True)


def load_runtime_config() -> dict[str, str]:
    """读取运行期配置文件，不存在时返回空字典。"""
    ensure_runtime_directories()
    config_path = Path(RUNTIME_CONFIG_FILE)
    if not config_path.exists():
        return {}

    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def get_paper_folder() -> str:
    """获取当前配置的文献目录。"""
    runtime_config = load_runtime_config()
    paper_folder = runtime_config.get("paper_folder", DEFAULT_PAPER_FOLDER)
    return str(Path(paper_folder))

