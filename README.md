# 模型之外：LLM 应用架构掰开揉碎

开源知识库系列 · 第二卷。讲清 LLM 的四个短板，以及 RAG、微调、工具调用、Agent 各自补哪一块、怎么组合；并讲多模态接入、Agent 的编排与 harness 设计。

- 在线阅读：https://feihuiwu2022.github.io/llm-app-book/ （仓库公开并启用 Pages 后可用）
- 全书规划：[BLUEPRINT.md](BLUEPRINT.md)
- 进度：全书 37 章加术语表附录，初稿已齐，待通读修订
- 配套代码：`code/` 目录，只用 Python 标准库，对应第 3、5、6、13、19、21、24、29、35 章。默认用写死规则的替身模型离线运行，换真实模型见 `code/llm.py`

## 本地预览

```bash
cargo install mdbook mdbook-mermaid
mdbook-mermaid install .
mdbook serve
```

## 许可证

文字内容 CC BY-SA 4.0，代码 MIT。
