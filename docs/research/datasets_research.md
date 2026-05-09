# Datasets Research

## Source Notes

Dataset licenses are listed only where visible in public dataset cards or official pages. If a source page does not clearly state a license, the license is marked as "not clearly stated" and must be checked before redistribution or commercial use.

Sources:

- Necent AI security dataset: https://huggingface.co/datasets/Necent/ai-security-dataset
- deepset prompt-injections: https://huggingface.co/datasets/deepset/prompt-injections
- Neuralchemy Prompt Injection Dataset: https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset
- Lakera public evaluation dataset list: https://docs.lakera.ai/docs/datasets
- HackAPrompt: https://www.hackaprompt.com/
- Jigsaw Toxic Comment challenge: https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge
- SST-2 HF card: https://huggingface.co/datasets/stanfordnlp/sst2
- GoEmotions TFDS page: https://tensorflow.google.cn/datasets/catalog/goemotions
- TweetEval repository: https://github.com/cardiffnlp/tweeteval
- DAIR emotion dataset: https://huggingface.co/datasets/emotion

## Dataset Candidates

| Dataset | Use | Size | Classes / Fields | License | Pros | Cons | MVP Fit |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| Necent AI Security Dataset | harmful prompts, prompt injection, jailbreak, toxicity | 691,331 rows per HF card | `prompt_type`, `category`, `is_dangerous`, language | Not clearly stated in search snippet; verify card | Broad multilingual aggregate with many safety sources | Aggregated data needs dedup/quality audit and license review | Good research/evaluation pool, cautious for training |
| deepset/prompt-injections | prompt injection | Size must be checked from HF card | likely binary injection/non-injection | Not clearly stated in snippet | Simple, focused dataset | Narrow taxonomy | Good MVP fine-tuning candidate after license check |
| neuralchemy/Prompt-injection-dataset | prompt injection + jailbreak | Card/model source references around 14K examples for related model | safe vs attack plus attack types depending config | Not clearly stated in snippet | Purpose-built and small enough for course experiments | Dataset-specific metrics may not generalize | Strong MVP candidate |
| HackAPrompt dataset | prompt injection/jailbreak | Public challenge data; exact size must be checked from HF/Kaggle mirror | challenge attacks and defenses | Must verify | Real adversarial challenge prompts | May be biased toward game mechanics | Good evaluation set |
| Lakera-listed Salad-Data | prompt injection | 21,318 per Lakera docs | attack-enhanced prompts across harm categories | Must verify source dataset | Categorized prompt injection data | Secondary listing, follow original dataset | Good evaluation candidate |
| Jigsaw Toxic Comment | toxic comments | Large Kaggle challenge dataset | toxic, severe toxic, obscene, threat, insult, identity hate | Kaggle competition terms | Standard moderation benchmark | Online comment domain; identity bias concerns | Good toxic label source |
| SST-2 | sentiment | 67.3K train rows on HF | positive/negative | Dataset card license must be checked | Standard sentiment baseline | Binary only, movie-review domain | Good baseline, not enough for TextMood |
| GoEmotions | emotion/urgency proxy | 58K Reddit comments | 27 emotions + neutral | TFDS page indicates CC BY 4.0 content / Apache 2.0 code samples | Fine-grained emotion labels; useful for angry/sad style | Reddit domain; label overlap and imbalance | Good for emotion component |
| TweetEval sentiment | sentiment/tone | Task-specific; sentiment has 3 classes | negative/neutral/positive | Repo says released without restrictions, but individual task/Twitter restrictions may apply | Social text domain | Twitter terms and task restrictions | Good evaluation/training with caution |
| DAIR emotion | emotion | HF card generated size around 47.62 MB | sadness, joy, love, anger, fear, surprise | Not clearly stated in snippet | Simple emotion labels including anger | No urgency/toxic class | Useful supplement |

## Dataset Strategy

For SecurePrompt Guard:

- Use neuralchemy/deepset/HackAPrompt-style datasets for injection/jailbreak fine-tuning.
- Use Jigsaw and safety datasets for harmful/toxic signal.
- Keep an evaluation split from a different source than training to reduce overfitting to prompt templates.

For TextMood Analytics:

- Use SST-2 or TweetEval for base sentiment.
- Use GoEmotions/DAIR emotion for anger-related labels.
- Create a small product-specific urgency set from support-ticket phrases because urgency is business-domain-specific and not always present as a clean public label.

## Risks

- Public jailbreak/prompt-injection datasets age quickly as attack patterns evolve.
- Aggregated datasets may mix licenses and label schemas.
- Toxicity datasets can encode social bias and require threshold review.
- Sentiment datasets often do not map cleanly to support prioritization.

