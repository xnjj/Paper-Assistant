# paper-source-mcp-server

这是一个面向论文检索场景的 MCP 服务骨架，目标是把不同外部来源的论文检索能力统一封装为标准工具，再供本项目中的 `MCPExternalSearchService` 调用。

当前这版骨架包含：

- 统一的工具 schema
- 统一的 provider 抽象
- `arXivProvider` 示例实现
- 与具体 MCP SDK 解耦的工具路由层

后续可以继续扩展的数据源包括：

- `Semantic Scholar`
- `Zotero`
- 浏览器搜索或网页自动化检索

## 推荐目录结构

```text
paper_source_mcp_server/
  README.md
  __init__.py
  schemas.py
  registry.py
  providers/
    __init__.py
    base.py
    arxiv_provider.py
```

## 统一工具名

为了和项目现有后端适配器保持一致，建议 MCP 服务统一暴露以下 3 个工具：

- `search_external_papers`
- `get_external_paper_detail`
- `resolve_external_fulltext`

## 推荐返回字段

### search_external_papers

返回：

```json
{
  "results": [
    {
      "source": "arxiv",
      "external_id": "2401.01234",
      "title": "Example Title",
      "authors": ["Alice", "Bob"],
      "year": "2024",
      "venue": "arXiv",
      "doi": "",
      "url": "https://arxiv.org/abs/2401.01234",
      "abstract": "....",
      "pdf_url": "https://arxiv.org/pdf/2401.01234.pdf",
      "relevance_score": 0.91
    }
  ]
}
```

### get_external_paper_detail

返回单篇论文的完整元数据，字段与 `results[]` 中的结构一致。

### resolve_external_fulltext

返回：

```json
{
  "source": "arxiv",
  "external_id": "2401.01234",
  "title": "Example Title",
  "pdf_url": "https://arxiv.org/pdf/2401.01234.pdf",
  "download_url": "https://arxiv.org/pdf/2401.01234.pdf",
  "landing_page_url": "https://arxiv.org/abs/2401.01234",
  "content_type": "application/pdf",
  "license": "",
  "is_open_access": true
}
```

## 与主项目的关系

主项目后端已经有：

- `app_backend/services/mcp_external_search_service.py`

这个适配器默认会调用上面 3 个工具名，因此这里的 MCP 服务工具名建议保持一致。

## 安装依赖

本项目已经在 [requirements.txt](/d:/vscode_workplace/python/RAG_Agent/requirements.txt) 中加入：

```txt
mcp[cli]
```

安装后即可直接运行。

## 启动方式

### 1. 直接以 stdio 方式启动

```bash
python -m paper_source_mcp_server
```

或显式指定：

```bash
python -m paper_source_mcp_server --transport stdio
```

### 2. 以 Streamable HTTP 方式启动

```bash
python -m paper_source_mcp_server --transport streamable-http --host 127.0.0.1 --port 8000
```

默认挂载路径为 `/mcp`，因此客户端连接地址通常是：

```text
http://127.0.0.1:8000/mcp
```

### 3. 配合 MCP 官方 CLI 使用

如果已经安装 MCP Python SDK 自带的 CLI，也可以使用：

```bash
mcp run paper_source_mcp_server/server.py
```

或开发模式：

```bash
mcp dev paper_source_mcp_server/server.py
```

## 可用环境变量

- `PAPER_SOURCE_MCP_TRANSPORT`
- `PAPER_SOURCE_MCP_HOST`
- `PAPER_SOURCE_MCP_PORT`
- `PAPER_SOURCE_MCP_NAME`
- `PAPER_SOURCE_MCP_STREAMABLE_HTTP_PATH`

这些环境变量会作为命令行参数的默认值。
