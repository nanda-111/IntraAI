# RAG 评估框架

## 概述

本框架用于评估 IntraAI RAG 系统的检索质量、生成质量和端到端性能。

## 文件结构

```
eval/
├── test_dataset.py      # 测试数据集定义
├── metrics.py           # 指标计算模块
├── run_eval_v3.py       # 主评估脚本（检索+生成+RAGAS+报告）
├── README.md            # 本文件
└── results/             # 评估结果目录
    ├── eval_results.json
    └── RAG_Evaluation_Report.md
```

## 测试数据集

### 数据集统计

| 数据集 | 样本数 | 说明 |
|--------|--------|------|
| RETRIEVAL_TEST_SET | 40条 | 检索质量评估，覆盖5类问题 |
| GENERATION_TEST_SET | 25条 | 生成质量评估，包含可答/不可答/部分可答 |
| MULTI_TURN_TEST_SET | 5组 | 多轮对话评估，共20轮 |
| E2E_TEST_SET | 10条 | 端到端评估 |
| ADVERSARIAL_TEST_SET | 10条 | 对抗性测试，检测幻觉 |
| CROSS_KB_TEST_SET | 8条 | 跨知识库测试 |

### 问题类别

检索测试类别:
- `simple_facts`: 简单事实查询
- `ip_address`: IP地址查询
- `config_commands`: 配置命令查询
- `verification`: 验证/故障排查
- `comprehensive`: 综合理解
- `edge_cases`: 边界情况

难度级别:
- `easy`: 简单
- `medium`: 中等
- `hard`: 困难

## 使用方法

### 运行完整评估

```bash
cd F:/IntraAI/backend
PYTHONIOENCODING=utf-8 python eval/run_eval_v3.py
```

评估包含2个阶段：
1. Phase 1: 检索质量评估（Hit Rate、MRR、Recall、NDCG）
2. Phase 2: 生成质量评估（忠实度、关键词覆盖、拒答准确率、RAGAS answer_relevancy）

评估完成后自动生成 Markdown 报告到 `results/RAG_Evaluation_Report.md`。

## 评估指标

### 检索指标

| 指标 | 说明 | 计算方式 |
|------|------|----------|
| Hit Rate@K | top-K 中是否命中至少一个相关文档 | 命中查询数 / 总查询数 |
| MRR | 第一个相关文档的倒数排名 | 平均(1/排名) |
| Recall@K | 相关文档被检索到的比例 | 检索到的相关文档数 / 总相关文档数 |
| Precision@K | 检索结果中相关文档的比例 | 相关文档数 / K |
| NDCG@K | 归一化折损累积增益 | 考虑排序位置的评分 |

### 生成指标

| 指标 | 说明 | 计算方式 |
|------|------|----------|
| Faithfulness | 答案是否基于上下文 | LLM判断或字符串匹配 |
| Keyword Coverage | 关键词覆盖率 | 匹配关键词数 / 总关键词数 |
| Refusal Accuracy | 拒答准确率 | 正确拒答数 / 不可答问题数 |

### 端到端指标

| 指标 | 说明 |
|------|------|
| Retrieval Latency | 检索延迟 |
| Generation Latency | 生成延迟 |
| Total Latency | 总延迟 |
| Multi-turn Coherence | 多轮对话连贯性 |

## 数据集设计原则

### 1. 多样性

- 问题类型: 覆盖事实查询、配置查询、验证查询、综合查询
- 难度级别: 简单、中等、困难
- 知识范围: 单知识库、跨知识库

### 2. 边界情况

- 不可答问题: 测试拒答能力
- 部分可答问题: 测试信息不足时的处理
- 模糊问题: 测试模型的理解能力

### 3. 对抗性测试

- 幻觉诱导: 诱导模型编造不存在的信息
- 陷阱问题: 测试模型是否会落入预设陷阱

### 4. 跨知识库测试

- 知识库区分: 测试模型能否正确区分不同知识库的内容
- 信息溯源: 测试模型能否正确引用来源

## 评估结果解读

### 优秀指标阈值

| 指标 | 优秀 | 良好 | 一般 | 待改进 |
|------|------|------|------|--------|
| Hit Rate@5 | ≥0.8 | ≥0.6 | ≥0.4 | <0.4 |
| MRR | ≥0.8 | ≥0.6 | ≥0.4 | <0.4 |
| Recall@5 | ≥0.8 | ≥0.6 | ≥0.4 | <0.4 |
| Faithfulness | ≥0.8 | ≥0.6 | ≥0.4 | <0.4 |
| Refusal Accuracy | ≥0.9 | ≥0.8 | ≥0.7 | <0.7 |
| Total Latency | ≤5s | ≤15s | ≤30s | >30s |

### 常见问题诊断

1. Hit Rate 低: 检索未找到相关文档
   - 检查 embedding 模型质量
   - 检查 chunk 分割是否合理
   - 检查 BM25 索引是否完整

2. MRR 低: 相关文档排名靠后
   - 优化 reranker
   - 调整混合检索权重

3. Faithfulness 低: 答案不忠实于上下文
   - 优化 prompt
   - 增加上下文约束

4. Refusal Accuracy 低: 拒答能力不足
   - 在 prompt 中增加拒答指令
   - 增加不可答问题的训练样本

## 改进历史

### v3.0 (2026-06-18)

- 重建测试数据集，基于 kb_4 的 12 个 chunk
- 扩充数据集规模：检索 40 条、生成 25 条、多轮 5 组
- 增加对抗性测试（10 条）
- 增加跨知识库测试（8 条）
- 纳入 reranker 评估
- 改进关键词覆盖率计算
- 增加按类别/难度的分析
- 新增报告生成器

### v2.0 (2026-06-17)

- 初始评估框架
- 基于 kb_9 的 38 个 chunk 构建测试集
- 实现检索、生成、端到端三阶段评估

## 注意事项

1. 知识库索引: 测试数据集的 `relevant_chunk_ids` 基于 kb_4 的 12 个 chunk（0-11）
2. Reranker: 评估脚本默认使用 reranker，与生产环境一致
3. LLM 调用: 评估过程会多次调用 LLM，注意 API 配额
4. 结果缓存: 评估结果保存在 `results/` 目录，可重复运行覆盖
