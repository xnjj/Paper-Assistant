"""
提示词：用户的提问 + 向量库中检索到的参考资料
"""
import arxiv
import config_data as config
from typing import List, Dict, Any, Tuple
from langchain_community.chat_models import ChatTongyi
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma

import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import scholarly
import PyPDF2
import re
import fitz  # pip install pymupdf
from dataclasses import dataclass
import json
import os
import hashlib
# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Paper:
    """论文信息"""
    id: int
    title: str
    abstract: str
    keywords: List[str]
    content: str                # 全文或主要部分
    file_path: str
    url: str = ""               # Google Scholar 论文页链接


class LiteratureReviewAgent:
    def __init__(self):
        """
        初始化Agent
        """
        self.model = ChatTongyi(model="qwen3-max")
        self.vectorstore = None
        self.paper_id_to_title = {}  # 用于检索结果映射
        self.chroma = Chroma(
            collection_name=config.DATABASE_TABLE,     # 数据库的表名
            embedding_function=DashScopeEmbeddings(model="text-embedding-v4"),
            persist_directory=config.DATABASE_FILE,     # 数据库本地存储文件夹
        )     # 向量存储的实例 Chroma向量库对象

    def load_papers(self, pdf_paths: List[str]) :
        """加载PDF文件，提取标题、摘要和全文"""
        full_text=""
        for idx, path in enumerate(pdf_paths, start=1):
            try:
                full_text = self._extract_pdf_page_text(path)  # 注意：每篇单独初始化
                if not full_text:
                    raise ValueError("PDF 文本为空，可能是扫描版或受保护文档")

                base_name = Path(path).stem
                # title = self._extract_title_candidates_by_font(path)
                # title,abstract = self._pick_best_title_with_ai(
                #     title_candidates=title,
                #     abstract=abstract,
                #     keywords=keywords
                # )
                title, abstract, keywords = self._extract_title_abstract_keywords_by_ai(
                    full_text=full_text,
                    fallback_title=base_name
                )
                paper = Paper(
                    id=idx,
                    title=title,
                    abstract=abstract,
                    keywords=keywords,
                    content=full_text,
                    file_path=path
                )
                self.update_database(paper)
                self.paper_id_to_title[idx] = title
                logger.info(f"加载论文 {idx}: {title}")
            except Exception as e:
                logger.error(f"加载 {path} 失败: {e}")
        return 
    
    def _extract_pdf_page_text(self, path: str) -> str:
        """
        提取“从首页到摘要页（含）”的文本：
        - 从首页开始逐页读取；
        - 找到 Abstract/摘要 后立即停止，返回截至该页的全部文本；
        - 若始终未找到摘要，则返回前 3 页作为兜底。
        """
        abstract_pat = re.compile(
            r"\b(?:abstract|a\s*b\s*s\s*t\s*r\s*a\s*c\s*t)\b|摘要",
            re.I
        )
        max_pages_if_not_found = 3

        chunks: List[str] = []
        found_abstract = False

        with fitz.open(path) as doc:
            for i, page in enumerate(doc):
                text = page.get_text("text") or ""
                chunks.append(text)

                # 命中摘要：保留当前页并停止（即返回“摘要前 + 摘要页”）
                if abstract_pat.search(text):
                    found_abstract = True
                    break

                # 未命中摘要时，只读前 3 页
                if i + 1 >= max_pages_if_not_found:
                    break

        if not found_abstract:
            return "\n".join(chunks[:max_pages_if_not_found]).strip()
        return "\n".join(chunks).strip()
    
    # def _extract_pdf_text(self, path: str) -> str:
    #     """优先用 PyMuPDF 提取全文"""
    #     chunks = []
    #     with fitz.open(path) as doc:
    #         for page in doc:
    #             chunks.append(page.get_text("text") or "")
    #     return "\n".join(chunks).strip()
    
    # def _extract_title_candidates_by_font(self, path: str, top_n: int = 8) -> Optional[List[str]]:
    #     """
    #     基于首页字体大小提取标题候选（支持多行标题）。
    #     规则：
    #     1) 仅扫描第一页文本块；
    #     2) 遇到 Abstract/Keyword（含中英文）后停止检索；
    #     3) 将相邻且字体接近的行合并为同一候选标题块；
    #     4) 返回按字体大小排序的候选列表，不确定时可返回多个候选；
    #     5) 完全无法提取时返回 None。
    #     """
    #     stop_pat = re.compile(r"\b(Abstract|Keywords?|Index Terms?)\b|摘要|关键词|关键字", re.I)
    #     noise_pat = re.compile(r"(arxiv|doi|http|www\.|@)", re.I)

    #     # 每一行先记录为 (avg_size, y0, text)
    #     line_items: List[Tuple[float, float, str]] = []
    #     hit_stop = False

    #     try:
    #         with fitz.open(path) as doc:
    #             if len(doc) == 0:
    #                 return None

    #             page = doc[0]
    #             page_h = float(page.rect.height)
    #             data = page.get_text("dict")

    #             for block in data.get("blocks", []):
    #                 if block.get("type", 1) != 0:
    #                     continue

    #                 for line in block.get("lines", []):
    #                     line_parts: List[str] = []
    #                     sizes: List[float] = []
    #                     y0_list: List[float] = []

    #                     for span in line.get("spans", []):
    #                         txt = (span.get("text") or "").strip()
    #                         if not txt:
    #                             continue

    #                         if stop_pat.search(txt):
    #                             hit_stop = True
    #                             break

    #                         if noise_pat.search(txt):
    #                             continue

    #                         line_parts.append(txt)
    #                         sizes.append(float(span.get("size", 0.0)))
    #                         bbox = span.get("bbox", [0, 0, 0, 0])
    #                         y0_list.append(float(bbox[1]))

    #                     if hit_stop:
    #                         break

    #                     if not line_parts or not sizes:
    #                         continue

    #                     text = re.sub(r"\s+", " ", " ".join(line_parts)).strip()
    #                     if len(text) < 3 or len(text) > 260:
    #                         continue

    #                     y0 = min(y0_list) if y0_list else page_h
    #                     if y0 > page_h * 0.70:  # 放宽一点，避免漏掉跨两行标题
    #                         continue

    #                     avg_size = sum(sizes) / len(sizes)
    #                     line_items.append((avg_size, y0, text))

    #                 if hit_stop:
    #                     break

    #         if not line_items:
    #             return None

    #         # 先按页面从上到下
    #         line_items.sort(key=lambda x: x[1])

    #         # 合并相邻行：字体接近 + 行距接近
    #         merged_blocks: List[Tuple[float, float, str]] = []
    #         cur_size, cur_y0, cur_text = line_items[0]

    #         for size, y0, text in line_items[1:]:
    #             size_close = abs(size - cur_size) <= max(0.8, cur_size * 0.08)
    #             line_gap = y0 - cur_y0
    #             gap_close = 0 < line_gap <= max(22.0, cur_size * 1.8)

    #             if size_close and gap_close:
    #                 cur_text = f"{cur_text} {text}".strip()
    #                 cur_size = (cur_size + size) / 2.0
    #                 cur_y0 = y0
    #             else:
    #                 merged_blocks.append((cur_size, cur_y0, re.sub(r"\s+", " ", cur_text).strip()))
    #                 cur_size, cur_y0, cur_text = size, y0, text

    #         merged_blocks.append((cur_size, cur_y0, re.sub(r"\s+", " ", cur_text).strip()))

    #         # 二次过滤
    #         candidates: List[Tuple[float, float, str]] = []
    #         for s, y, t in merged_blocks:
    #             if 8 <= len(t) <= 320:
    #                 candidates.append((s, y, t))

    #         if not candidates:
    #             return None

    #         # 排序：字体大优先，其次靠上，最后长度接近标题常见长度
    #         ranked = sorted(candidates, key=lambda x: (-x[0], x[1], abs(len(x[2]) - 90)))

    #         # 去重并截断
    #         seen = set()
    #         result: List[str] = []
    #         for _, _, t in ranked:
    #             k = re.sub(r"\s+", " ", t.lower()).strip()
    #             if k in seen:
    #                 continue
    #             seen.add(k)
    #             result.append(t)
    #             if len(result) >= top_n:
    #                 break

    #         return result if result else None

    #     except Exception as e:
    #         logger.warning(f"字体法提取标题候选失败: {e}")
    #         return None
    
    # def _pick_best_title_with_ai(
    #     self,
    #     title_candidates: Optional[List[str]],
    #     abstract: str,
    #     keywords: List[str]
    # ) -> Tuple[str, str]:
    #     """
    #     使用 AI 根据摘要和关键词，从候选标题中选最可能的一个。
    #     失败时返回 fallback。
    #     """
    #     if not title_candidates:
    #         return "（未提取到标题）", abstract
    #     if len(title_candidates) == 1:
    #         return title_candidates[0], abstract

    #     try:
    #         kw_text = "、".join(keywords) if keywords else "无"
    #         cands = "\n".join([f"{i+1}. {t}" for i, t in enumerate(title_candidates)])

    #         prompt = ChatPromptTemplate.from_messages([
    #             ("system",
    #              "请帮助用户判定论文标题。根据摘要与关键词，从候选标题中选出最匹配的一项。"
    #              "请只输出候选编号（阿拉伯数字），如果摘要是英文将其翻译成中文后换行输出，不要输出其他内容。"),
    #             ("human",
    #              "摘要：\n{abstract}\n\n"
    #              "关键词：{keywords}\n\n"
    #              "候选标题：\n{cands}\n\n"
    #              "请选择最匹配的标题编号。")
    #         ])

    #         chain = prompt | self.model | StrOutputParser()
    #         ans = chain.invoke({
    #             "abstract": abstract[:3000],
    #             "keywords": kw_text,
    #             "cands": cands
    #         }).split('\n\n')

    #         if len(ans) > 1:
    #             # 如果有两行，第一行为编号，第二行为摘要
    #             abstract += "\n\n" + ans[1]
                
    #         m = re.search(r"\d+", ans[0].strip())
    #         if m:
    #             idx = int(m.group()) - 1
    #             if 0 <= idx < len(title_candidates):
    #                 return title_candidates[idx], abstract

    #         # 若模型返回异常，回退第一候选
    #         return title_candidates[0], abstract
    #     except Exception as e:
    #         logger.warning(f"AI 标题判定失败，使用回退标题。原因: {e}")
    #         return title_candidates[0], abstract if title_candidates else "（未提取到标题）", abstract

 
    
    def _extract_title_abstract_keywords_by_ai(self, full_text: str, fallback_title: str) -> Tuple[str, str, List[str]]:
        """
        使用 AI 从全文中提取 标题/摘要/关键词。
        返回: (title, abstract, keywords)
        """
        # 控制输入长度，避免超长
        text_for_llm = (full_text or "")[:18000]

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "你是学术论文信息抽取助手。"
             "请从给定论文文本中提取: title(标题), abstract(摘要), keywords(关键词列表)。"
             "只输出 JSON，尽量保留原文，英文摘要和关键词换行追加中文翻译（如果中英文的标题、摘要、关键词都存在，仅保留中文版本即可）不要输出任何解释。\n"
             "JSON schema: {{\"title\": str, \"abstract\": str, \"keywords\": [str, ...]}}"),
            ("human",
             "请提取以下论文文本中的标题、摘要和关键词：\n\n"
             "{text}\n\n"
             "注意：\n"
             "1) 若标题不确定，选择最像论文题目的一行；\n"
             "2) 摘要尽量完整、连贯；\n"
             "3) 关键词最多输出 10 个；\n"
             "4) 若缺失字段，用空字符串或空数组。")
        ])

        chain = prompt | self.model | StrOutputParser()
        raw = chain.invoke({"text": text_for_llm}).strip()

        # 尝试提取 JSON 主体
        try:
            m = re.search(r"\{[\s\S]*\}", raw)
            obj = json.loads(m.group(0) if m else raw)

            title = str(obj.get("title", "")).strip() or fallback_title
            abstract = str(obj.get("abstract", "")).strip() or "（未提取到摘要）"
            keywords = obj.get("keywords", [])
            if not isinstance(keywords, list):
                keywords = []

            # 清洗关键词
            cleaned = []
            seen = set()
            for k in keywords:
                ks = re.sub(r"\s+", " ", str(k)).strip(" \t\r\n,;，；")
                if not ks:
                    continue
                lk = ks.lower()
                if lk in seen:
                    continue
                seen.add(lk)
                cleaned.append(ks)
                if len(cleaned) >= 10:
                    break

            return title, abstract, cleaned
        except Exception as e:
            logger.warning(f"AI提取标题/摘要/关键词失败，回退规则法: {e}")
            # 回退
            # title_candidates = self._extract_title_candidates_by_font(fallback_title if fallback_title.endswith(".pdf") else "")
            # 上面这行不可靠，不用文件路径就不要调，直接用兜底：
            return fallback_title, "（未提取到摘要）", []

    def generate_review(self,research_area)->str:
        """
        生成文献综述Markdown内容，并在文中引用论文（使用序号）
        """
        if not self.papers:
            return ""

        # 构建论文摘要列表（用于LLM上下文）
        abstracts_text = []
        for p in self.papers:
            abstracts_text.append(f"标题：{p.title}\n摘要：{p.abstract}\n")

        abstracts_combined = "\n".join(abstracts_text)

        prompt = f"""
        研究领域：{research_area}

        以下是相关论文的标题和中文摘要：
        {abstracts_combined}

        请根据以上信息，撰写一篇该领域的文献综述，应包括以下部分：
        1. 引言：简要介绍研究背景和意义
        2. 研究进展：分类总结各篇论文的主要贡献和创新点
        3. 讨论与展望：指出现有研究的不足和未来方向
        4. 参考文献：按引用顺序列出综述中提到的论文，格式为 [序号] 论文标题

        要求在正文中适当引用相关论文，引用格式为右上标[序号]（序号为引用的顺序从[1]开始编号）。综述语言为中文，结构清晰，使用Markdown格式（标题用 ##，子标题用 ###）。
        """
        try:
            response = self.model.invoke(prompt)
            review_content = response.content
            with open(config.REVIEW_FILE, 'w', encoding='utf-8') as f:
                f.write(review_content)
                logger.info(f"综述已保存至 {config.REVIEW_FILE}")
            return review_content
        except Exception as e:
            logger.error(f"生成综述失败: {e}")
            return ""

    def update_database(self,paper):
        title_md5 = hashlib.md5(paper.title.encode("utf-8")).hexdigest()
        idx_offset = 0
        # 读取已有 MD5 字典
        if os.path.exists(config.MD5_FILE):
            with open(config.MD5_FILE, "a", encoding="utf-8") as f:
                for line in f:
                    md5_value = line.strip().lower()
                    if md5_value==title_md5:
                        print(f"跳过已存在论文: {paper.title}")
                        return
                    idx_offset += 1
                f.write(title_md5 + "\n")

        """生成数据库索引Markdown内容"""
        with open(config.INDEX_FILE, 'a', encoding='utf-8') as f:
            if idx_offset == 0:
                f.write("| 序号 | 标题 | 链接 |\n")
                f.write("|------|------|------|\n")

            f.write(f"| {idx_offset} | {paper.title} | {paper.url} |\n")
            self.chroma.add_texts([paper.content], metadatas=[{"title": paper.title, "abstract": paper.abstract, "keywords": paper.keywords}],ids=idx_offset)

        logger.info(f"数据库更新: {paper.title} 已添加到索引")
        return 

    def run(self, pdf_folder:str, research_area: str):
        """
        完整流程：加载论文 -> 构建知识库 -> 生成综述 -> 生成索引
        返回 (综述内容, 索引内容)
        """
        logger.info("开始加载论文...")
        pdf_paths = [str(p) for p in Path(pdf_folder).glob("*.pdf")]
        self.load_papers(pdf_paths)
        if not self.paper_id_to_title:
            raise Exception("没有成功加载任何论文")

        # logger.info("构建知识库...")
        # self.build_knowledge_base()

        logger.info("生成文献综述...")
        review = self.generate_review(research_area)

        return


def print_prompt(prompt):
    print(prompt.to_string())
    print("=" * 20)
    return prompt

# 示例使用
if __name__ == "__main__":
    # 研究领域描述
    research_area = "DQN算法在列车自动控制中的应用与优化，特别是在虚拟编组场景下生成列车的速度曲线方面的最新研究进展。"

    agent = LiteratureReviewAgent()
    agent.run(config.PAPER_FOLDER, research_area)


# model = ChatTongyi(model="qwen3-max")
# prompt = ChatPromptTemplate.from_messages(
#     [
#         ("system", "以用户提供的参考资料为主，生成{input}领域的最新研究进展综述，要求内容翔实，专业且简洁。参考资料:{context}。"),
#         #("user", "{input}")
#     ]
# )

# chain = prompt | print_prompt | model | StrOutputParser()
# input=config.TOPIC
# context=fetch_arxiv_papers().__str__()
# res = chain.invoke({"input": input, "context": context})
# print(res)
