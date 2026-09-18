# CHAT CONTEXT

Този файл е стартов контекст за нови разговори по Corporate AI.

Проектът е отделен от ZlaCloud.

Изграждаме локален Corporate AI върху NVIDIA DGX Spark GB10. Основният модел е Qwen3.6-35B-A3B-NVFP4 с vLLM, 262144 context, GPU utilization 0.65, KV FP8, Qwen3 reasoning parser, tool calling и qwen3_coder tool parser.

Преди system update-а работеха: vllm_qwen36, qwen3_embedding_4b, qdrant с 12+ collections, qwen3-reranker-cpu на 8002, office-tools на 8080/8092, open-webui, caddy, ingestion, RAG, router, compose/document generation, traceability matrix, watcher и attachment auto-ingest. След update контейнерите са спрени, но images/volumes/configs са запазени.

Целевата архитектура е Open WebUI → Corporate AI Gateway/Agent → Router → LLM / Knowledge / Tools / Vision.

Knowledge layer: Qwen3-Embedding-4B, Qdrant, Qwen3-Reranker-0.6B, hybrid retrieval, metadata filtering, conditional reranking, evidence fusion, citations и grounded answers. Knowledge Graph се добавя там, където носи реална стойност.

Document intelligence: PDF, DOCX, DOC, XLSX, PPTX, CSV, TXT и изображения. Universal ingestion → format router → specialized extraction → structure → chunking → metadata → embedding → Qdrant/Graph.

Tools: Word, Excel, PowerPoint, PDF, file operations и вътрешни AI tools. Tool Gateway има schema, policy, validation, logging, traceability и confirmation при рискови действия.

Corporate AI Console показва application services, status, version, image, port, network, health, ресурси, зависимости и връзки. Новите services трябва да се откриват автоматично.

NVIDIA DGX Dashboard остава системният dashboard. JupyterLab е dev/lab среда, не production component.

Текущ kernel след update: 7.0.0-1019-nvidia. Има актуален NVIDIA форумен доклад за NCCL/RoCE multi-node поведение при този kernel. Не се прави rollback на сляпо.

Работен ред: baseline → inventory → runtime → knowledge → ingestion → RAG/Graph → vision → tools → agent → UI → console → security → backup/recovery → evaluation → production readiness.

При неизвестно се проверява, не се измисля. Българският е основен език.