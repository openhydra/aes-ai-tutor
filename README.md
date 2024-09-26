# AI-Tutor

AI-Tutor 是一个基于人工智能的智能辅导系统，旨在帮助学生更好地理解和掌握各种学科的知识。

## 功能

- **智能问答**：通过自然语言处理技术，AI-Tutor 可以回答学生提出的各种问题。
- **个性化 RAG 系统**：提供个性化的 RAG 系统，帮助学生理解他们的学习材料。
- **多学科支持**：支持数学、科学、历史等多种学科。

## 安装

1. 克隆仓库到本地：

2. 进入项目目录：
    ```bash
    cd aes-ai-tutor/libs
    ```
3. 安装依赖：
    ```bash
    poetry install --with lint,test
    ```

## 使用

1. 启动应用：
    ```bash
    cd aes-ai-tutor/libs/aitutor
    python cli.py init && python cli.py start --api
    ```
2. API 服务器运行在 `http://localhost:7861`。

## 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库。
2. 创建一个新的分支：
    ```bash
    git checkout -b feature-branch
    ```
3. 提交你的更改：
    ```bash
    git commit -am 'Add new feature'
    ```
4. 推送到分支：
    ```bash
    git push origin feature-branch
    ```
5. 创建一个 Pull Request。

## 许可证

本项目采用 Apache 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 参考

本项目参考了 [Langchain-Chatchat](https://github.com/chatchat-space/Langchain-Chatchat/tree/v0.3.1)。