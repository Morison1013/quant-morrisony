# RAG 知识库实现总结

## 文件清单

### 后端新增文件

```
backend/
├── app/
│   ├── api/
│   │   └── rag.py                 # RAG API 路由
│   ├── services/
│   │   └── rag/
│   │       ├── __init__.py        # 模块导出
│   │       ├── embedding.py       # Embedding 服务
│   │       ├── vectorstore.py     # ChromaDB 管理
│   │       ├── generator.py       # LLM 生成服务
│   │       ├── retriever.py       # 检索辅助
│   │       ├── indexer.py         # 文档索引服务
│   │       └── rag_pipeline.py    # RAG 主流程
│   └── schemas/
│       └── rag.py                 # RAG Schema
├── scripts/
│   └── index_knowledge.py         # 索引脚本
├── data/
│   └── chroma/                    # ChromaDB 存储目录
└── .env.example                   # 环境配置模板
```

### 后端修改文件

- `app/config.py` - 添加 RAG 配置项
- `app/api/router.py` - 注册 RAG 路由
- `requirements.txt` - 添加 chromadb 依赖

### 前端新增文件

```
frontend/src/
├── components/
│   └── rag/
│       ├── index.ts               # 组件导出
│       ├── FloatingChatButton.tsx # 悬浮按钮
│       ├── ChatPanel.tsx          # 聊天面板
│       ├── ChatMessage.tsx        # 消息组件
│       └── QueryInput.tsx         # 输入框
├── lib/
│   ├── ragTypes.ts                # 类型定义
│   ├── ragApi.ts                  # API 封装
│   └── ragStore.tsx               # 状态管理
└── .env.example                   # 环境配置模板
```

### 前端修改文件

- `app/layout.tsx` - 集成悬浮组件

### 知识库文档

```
docs/knowledge/
├── strategies/
│   ├── MA_Bullish.md              # 均线多头策略
│   ├── MACD_GoldenCross.md        # MACD金叉策略
│   ├── Overnight_Arbitrage.md     # 隔日套利策略
│   ├── RubbingLine.md             # 揉搓线洗盘策略
│   └── index.md                   # 策略索引
├── concepts/                      # 基础概念 (待补充)
├── guides/                        # 操作指南 (待补充)
└── faq/                           # 常见问题 (待补充)
```

## 使用步骤

### 1. 配置环境

```bash
# 后端
cd backend
cp .env.example .env
# 编辑 .env 填写 DEEPSEEK_API_KEY 和 EMBEDDING_API_KEY

# 前端
cd frontend
cp .env.example .env.local
```

### 2. 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 3. 索引知识库

```bash
cd backend
python scripts/index_knowledge.py
```

### 4. 启动服务

```bash
# 后端
cd backend
python run.py

# 前端
cd frontend
npm run dev
```

### 5. 使用问答

- 打开前端页面
- 点击右下角蓝色悬浮按钮
- 输入问题进行问答

## API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/rag/query` | POST | RAG 问答查询 |
| `/api/rag/status` | GET | 获取索引状态 |
| `/api/rag/index` | POST | 触发文档索引 |
| `/api/rag/suggestions` | GET | 获取查询建议 |