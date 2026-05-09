# ML Models Research

## Source Notes

Research used public model cards and official documentation. Metrics are included only where the source states them. Absence of latency/memory numbers is recorded as unknown rather than inferred.

Key sources:

- Meta Prompt Guard 86M model card: https://huggingface.co/meta-llama/Prompt-Guard-86M
- Llama Prompt Guard 2 docs/model card: https://www.llama.com/docs/model-cards-and-prompt-formats/prompt-guard/ and https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M
- ProtectAI DeBERTa prompt injection model card: https://huggingface.co/protectai/deberta-v3-base-prompt-injection
- Neuralchemy prompt-injection DeBERTa model card: https://huggingface.co/neuralchemy/prompt-injection-deberta
- OpenAI Moderation docs: https://platform.openai.com/docs/guides/moderation/overview
- DistilBERT SST-2 model card: https://huggingface.co/distilbert-base-uncased-finetuned-sst-2-english
- CardiffNLP Twitter RoBERTa sentiment model family: https://github.com/cardiffnlp/tweeteval
- Sentence Transformers efficiency docs: https://www.sbert.net/docs/sentence_transformer/usage/efficiency.html

## Prompt Injection / Harmful Prompt Detection

| Option | Strengths | Weaknesses | CPU/GPU | Explainability | License Notes | MVP Fit |
| --- | --- | --- | --- | --- | --- | --- |
| Llama Prompt Guard 2 22M/86M and earlier Prompt Guard 86M | Purpose-built for prompt injection and jailbreak detection; compact BERT-class classifier variants | Llama license constraints must be reviewed before product use | 22M/86M class models are plausible CPU candidates; exact latency depends on hardware and runtime | Low native explainability; can add rule hits and score display | Llama license family | Strong production upgrade candidate |
| ProtectAI DeBERTa v3 base prompt injection | Popular HF baseline; directly targets prompt injection | Base-size transformer is heavier than small models; binary focus may need label mapping | CPU possible but may be slower; GPU improves throughput | Low native explainability | Check HF card/license before commercial use | Good comparison/upgrade candidate |
| Neuralchemy prompt-injection DeBERTa small | Source card states DeBERTa-v3-small, 44M params, binary safe/attack; card reports dataset-specific metrics | Model card itself notes classical TF-IDF Random Forest outperformed it on that dataset | Better CPU fit than base models; card mentions around 50ms in its environment | Low native explainability | Check HF card/license | Good MVP ML baseline after rule baseline |
| OpenAI Moderation API | Managed moderation categories, no self-hosting or GPU ops | External dependency, network latency, data governance, not prompt-injection-specific | No local compute | Category scores are explainable at category level | API terms, not an OSS model | Optional external validator, not core MVP |
| Llama Guard | Strong safety taxonomy moderation model family | LLM-sized guard models are heavier and less suitable for cheap CPU MVP | Typically GPU-oriented for practical latency | Natural-language policy output possible | Llama license family | Better as advanced/offline evaluator |
| Rule-based layer | Very fast, deterministic, explainable, no model dependency | Easy to evade; high false negatives on paraphrases | CPU trivial | High | Internal code | Best MVP baseline and first-layer defense |

## Recommended Prompt Safety Strategy

Use a layered approach:

1. Rule-based baseline for MVP and explainability.
2. Upgrade to small encoder classifier for semantic detection.
3. Optional ensemble with external moderation or Llama Guard for high-risk/advanced mode.

Do not present the rule baseline as high-quality security. It is an architectural baseline that proves plugin, billing and async flows while leaving the ML plugin replaceable.

## Sentiment / Tone Classification

| Option | Strengths | Weaknesses | CPU/GPU | Explainability | MVP Fit |
| --- | --- | --- | --- | --- | --- |
| DistilBERT SST-2 | Compact, widely used, binary sentiment baseline | English/movie-review domain; no urgency/toxic labels | CPU-friendly relative to BERT/RoBERTa | Low | Good simple sentiment baseline |
| CardiffNLP RoBERTa/TweetEval | Strong social text sentiment/emotion ecosystem | Twitter domain; license/restrictions can vary by task | CPU possible, heavier than DistilBERT | Low | Good social/support text candidate |
| DeBERTa sentiment models | Often strong accuracy in classification tasks | Larger models increase latency/memory | Better with GPU for throughput | Low | Production upgrade candidate |
| Sentence-transformers + sklearn | Fast embeddings with simple classifiers; easy to cache embeddings | Needs labeled product-domain data; two-stage pipeline | CPU-friendly with MiniLM-style encoders | Medium: linear coefficients/neighbors possible | Good custom training path |
| Multilingual models | Required if Russian/English support is mandatory | Larger memory and possible lower domain fit | CPU cost varies by model size | Low | Use when multilingual scope is explicit |
| Rule-based urgency/toxicity signals | Cheap and explainable for product demos | Not robust enough alone | CPU trivial | High | Good MVP supplement |

## Recommended TextMood Strategy

- MVP baseline: rule supplement plus DistilBERT/RoBERTa-compatible plugin interface.
- Production model: domain-finetuned encoder classifier with labels `positive`, `neutral`, `negative`, `angry`, `urgent`, `toxic`.
- If multilingual support is required, prefer multilingual MiniLM/mDeBERTa-style models and validate on Russian support messages.

## Cross-Cutting Model Decisions

- Encoder classifiers are preferred over generative LLMs for MVP classification because they are cheaper, easier to batch, easier to version, and simpler to deploy on CPU.
- ONNX export is the recommended optimization path after model selection.
- Rules remain useful as transparent features and guardrails, not as the only defense.
