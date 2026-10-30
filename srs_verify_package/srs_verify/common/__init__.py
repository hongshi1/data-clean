"""srs_verify公共基础设施: 本地BGE客户端与LLM客户端.

两个模块均保持惰性(bge_local的torch/transformers在ensure()内import;
llm_client的配置读取推迟到调用期), import本包零I/O/零重依赖.
"""
