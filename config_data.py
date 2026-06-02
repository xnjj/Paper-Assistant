from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent

# ---------------------------- 环境配置 ----------------------------
OPENAI_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

# ---------------------------- 本地存储配置 ----------------------------
LLM_MODEL_NAME = "qwen3-max"
EMBEDDING_MODEL_NAME = "text-embedding-v1"
DOCUMENT_CHUNK_MAX_CHARS = 2048
MODEL_MAX_CONTEXT_LENGTH = 20_000

# ---------------------------- 检索配置 ----------------------------
# TOP_K 是本地向量召回候选 chunk 数；RECALL_K 是本地重排后保留并送入问答的 chunk 数。
TOP_K = 100
RECALL_K = 20
CHUNK_LIMIT_PER_PAPER = 2

# 外部检索与最终证据拼接上限。
MAX_PARALLEL_EXTERNAL_QUERIES = 3
MAX_EXTERNAL_QUERY_LIMIT = 5
MAX_SOURCE_FINAL_LIMIT = 10
DEFAULT_EXTERNAL_FINAL_LIMIT = 20
MAX_SEARCH_NUM = 30

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

