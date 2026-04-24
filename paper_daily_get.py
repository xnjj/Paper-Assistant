#!/usr/bin/env python3
"""
论文检索 Agent
每天上午8点从 arXiv 指定分类中检索前一天发布的论文，
使用 OpenAI 嵌入进行主题筛选，生成摘要文件与全局索引。
"""

import os
import sys
import time
import schedule
import arxiv
from openai import OpenAI
from datetime import datetime
from typing import List, Dict, Any, Tuple
import numpy as np
from langchain_community.embeddings import DashScopeEmbeddings
import config_data as config
import hashlib

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=config.OPENAI_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
completion = client.chat.completions.create(
    model="qwen-plus",
    messages=[{'role': 'system', 'content': '你是{}领域的专家，帮助用户筛选该领域的论文。'.format(config.TOPIC)}],
)
# ---------------------------- 工具函数 ----------------------------
def ensure_dir(directory: str) -> None:
    """确保目录存在，若不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_dot(vec_a, vec_b):
    """计算2个向量的点积，2个向量同维度数字乘积之和"""
    if len(vec_a) != len(vec_b):
        raise ValueError("2个向量必须维度数量相同")

    dot_sum = 0
    for a, b in zip(vec_a, vec_b):
        dot_sum += a * b

    return dot_sum


def get_norm(vec):
    """计算单个向量的模长：对向量的每个数字求平方在求和在开根号"""
    sum_square = 0
    for v in vec:
        sum_square += v * v

    # numpy sqrt函数完成开根号
    return np.sqrt(sum_square)


def cosine_similarity(vec_a, vec_b):
    """余弦相似度：2个向量的点积 除以 2个向量模长的乘积"""

    result = get_dot(vec_a, vec_b) / (get_norm(vec_a) * get_norm(vec_b))
    return result

# def cosine_similarity(a: List[float], b: List[float]) -> float:
#     """计算余弦相似度"""
#     a = np.array(a)
#     b = np.array(b)
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def fetch_arxiv_papers(target_date: datetime.date) -> List[Dict[str, Any]]:
    """
    从 arXiv 获取指定日期发布的论文（按提交日期排序，取前 MAX_RESULTS 篇）
    返回列表，每项包含 title, summary, link, published 等字段
    """
    client = arxiv.Client()
    # arXiv API 查询：按分类检索，按提交日期降序排序
    search = arxiv.Search(
        query=f'ti:{config.TOPIC.replace(" ", "+")} AND cat:{config.ARXIV_CATEGORY}',
        max_results=config.MAX_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )

    papers = []
    # 目标日期范围（0:00 到 23:59 UTC）
    start_dt = datetime(target_date.year, target_date.month, target_date.day-7, 0, 0, 0)
    
    #end_dt = start_dt + timedelta(days=1)
    for result in client.results(search):
        # arXiv 的 published 字段是发布时间（UTC）
        pub_date = result.published.replace(tzinfo=None)  # 去除时区信息，转为 naive datetime
        # 由于按时间降序，遇到更早的论文就可以停止
        if pub_date < start_dt:
            break
        else:
            papers.append({
                "title": result.title,
                "summary": result.summary,
                "link": result.entry_id,  # arXiv 文章页 URL
                "published": pub_date
            })
    return papers

def filter_papers_by_count(papers: List[Dict], phrases: List[str]) -> List[Dict]:
    """
    使用短语词频进行打分：
    统计每篇论文 title+summary 中，phrases 列表里各短语出现次数总和
    """
    if not papers:
        return []

    normalized_phrases = list({
        p.strip().lower() for p in phrases
        if isinstance(p, str) and p.strip()
    })
    if not normalized_phrases:
        print("短语列表为空，无法进行匹配")
        return []

    filtered = []
    for paper in papers:
        text = f"{paper.get('title', '')}\n{paper.get('summary', '')}".lower()
        match_count = sum(text.count(phrase) for phrase in normalized_phrases)
        if match_count > 1:
            paper['similarity'] = float(match_count)
            paper['match_count'] = match_count
            filtered.append(paper)
            print(f"find new paper: {paper.get('title', '')} | match_count={match_count}")

    # 按匹配次数降序排序，并仅保留前 5 篇
    filtered.sort(key=lambda x: x['match_count'], reverse=True)
    return filtered[:5]

def filter_new_papers_by_md5(papers: List[Dict]) -> List[Dict]:
    """
    基于 MD5 字典去重：
    1) 从 md5_file 读取已有 MD5（每行一个）
    2) 过滤掉已存在的论文
    3) 将新论文 MD5 写回 md5_file（全量覆盖写入，按字典序）
    返回：仅包含“新论文”的列表
    """
    
    # 读取已有 MD5 字典
    existing_md5 = set()
    if os.path.exists(config.MD5_FILE):
        with open(config.MD5_FILE, "r", encoding="utf-8") as f:
            for line in f:
                md5_value = line.strip().lower()
                if md5_value:
                    existing_md5.add(md5_value)

    new_papers = []
    added_md5 = set()

    for paper in papers:
        title = str(paper.get("title", "")).strip()
        paper_md5 = hashlib.md5(title.encode("utf-8")).hexdigest()

        # 字典中已有则跳过
        if paper_md5 in existing_md5:
            print(f"跳过已存在论文: {title}")
            continue

        # 新论文：保留并记录
        new_papers.append(paper)
        added_md5.add(paper_md5)

    # 合并并回写 md5 字典
    if added_md5:
        #existing_md5.update(added_md5)
        with open(config.MD5_FILE, "a", encoding="utf-8") as f:
            for md5_value in added_md5:
                f.write(md5_value + "\n")

    print(f"MD5 去重完成：输入 {len(papers)} 篇，新增 {len(new_papers)} 篇，字典总量 {len(existing_md5)}")
    return new_papers

def save_daily_summary(papers: List[Dict], date: datetime.date) -> str:
    """
    生成当天的摘要文件（Markdown 格式），序号从 0 开始
    返回文件名，若无文章返回 None
    """
    if not papers:
        return None

    ensure_dir(config.OUTPUT_DIR)
    filename = os.path.join(config.OUTPUT_DIR, f"{date.isoformat()}.md")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {date.isoformat()} 相关论文摘要\n\n")
        for idx, paper in enumerate(papers):
            f.write(f"## {idx}. {paper['title']}\n\n")
            f.write(f"{paper['summary']}\n\n")
            f.write(f"短语命中次数: {paper.get('match_count', int(paper.get('similarity', 0)))}\n\n")
            f.write("---\n\n")
    print(f"已生成摘要文件: {filename}")
    return filename

def update_global_index(papers: List[Dict], date: datetime.date) -> None:
    """
    更新全局索引文件（papers_index.md）
    格式为 Markdown 表格：序号 | 标题 | 链接
    序号从上次最大值后连续递增
    """
    if not papers:
        return

    # 读取现有索引，确定当前最大序号
    existing_entries = []
    last_index = 0
    if os.path.exists(config.INDEX_FILE):
        with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # 查找最后一行有效数据（跳过表头和分隔线）
        for line in reversed(lines):
            if line.startswith("|") and "---" not in line:
                parts = line.strip().split("|")
                if len(parts) >= 2:
                    try:
                        last_index = int(parts[1].strip())
                        break
                    except:
                        continue

    # 准备新条目
    new_entries = []
    for i, paper in enumerate(papers):
        new_index = last_index + 1 + i
        title = paper['title'].replace("|", "\\|")  # 转义 Markdown 表格中的竖线
        link = paper['link']
        new_entries.append(f"| {new_index} | {title} | {link} |\n")

    # 写入文件（如果不存在则创建表头）
    with open(config.INDEX_FILE, "a", encoding="utf-8") as f:
        if last_index == 0:
            f.write("| 序号 | 标题 | 链接 |\n")
            f.write("|------|------|------|\n")
        f.writelines(new_entries)

    print(f"已更新全局索引，新增 {len(new_entries)} 条记录")

# ---------------------------- 主任务 ----------------------------
def daily_job():
    """每日执行的任务：检索、筛选、生成文件"""
    # 计算当天日期（UTC 时间）
    target_date = datetime.now().date()
    print(f"\n--- 开始执行每日任务: {target_date} ---")

    # 1. 从 arXiv 获取当天论文
    print(f"{target_date}正在获取最新发布的论文...")
    raw_papers = fetch_arxiv_papers(target_date)
    print(f"获取到 {len(raw_papers)} 篇原始论文")

    # 2. 主题筛选
    filtered_papers = filter_papers_by_count(raw_papers, config.CONTENT)
    filtered_papers = filter_new_papers_by_md5(filtered_papers)
    print(f"主题筛选后剩余 {len(filtered_papers)} 篇相关论文")

    # 3. 生成每日摘要文件（若无相关文章则跳过）
    daily_file = save_daily_summary(filtered_papers, target_date)
    if daily_file:
        # 4. 更新全局索引
        update_global_index(filtered_papers, target_date)
    else:
        print(f"{target_date} 无相关文章，不生成摘要文件")

    print("--- 任务执行完毕 ---\n")

# ---------------------------- 调度器 ----------------------------
def run_scheduler():
    """设置定时任务并启动循环"""
    schedule.every().day.at("08:00").do(daily_job)
    print("调度器已启动，等待每天 08:00 执行...")

    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

# ---------------------------- 主入口 ----------------------------
if __name__ == "__main__":
    # 如果命令行参数包含 --once，则立即执行一次（用于测试）
    if len(sys.argv) > 1 and sys.argv[1] == "--scheduler":
        run_scheduler()
    else:
        daily_job()  # 直接执行一次，适合测试和调试