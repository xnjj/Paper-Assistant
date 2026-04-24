import os
from dotenv import load_dotenv
import sys
# ---------------------------- 配置参数 ----------------------------
# 加载环境变量
load_dotenv()
OPENAI_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not OPENAI_API_KEY:
    print("错误：未找到 OPENAI_API_KEY，请在 .env 文件中设置")
    sys.exit(1)

# 检索主题（可修改）
TOPIC = "Large Language Model"  # arXiv 查询中空格替换为加号
CONTENT = ["Multimodal","Discrete Symbol Understanding","Large Language Model"]
# arXiv 分类（例如 cs.LG, cs.CL, stat.ML 等）
ARXIV_CATEGORY = "cs.AI"

# 相似度阈值（0~1），仅保留高于此值的论文
SIMILARITY_THRESHOLD = 0.5

# 每次查询的最大论文数（防止一次性请求过多）
MAX_RESULTS = 10

# 输出目录和文件
OUTPUT_DIR = "daily_papers"
INDEX_FILE = OUTPUT_DIR+"/database_index.md"
MD5_FILE = OUTPUT_DIR+"/md5.txt"
DATABASE_FILE = OUTPUT_DIR+"/chroma_db"
DATABASE_TABLE = "papers_collection"

PAPER_FOLDER="paper_demo"
REVIEW_FILE = OUTPUT_DIR+"/literature_review.md"
UPLOAD_FILE = OUTPUT_DIR+"/upload_papers.md"
