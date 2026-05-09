from app.domain.ml.classifier_contracts import (
    BaseClassifier,
    ClassificationInput,
    ClassificationOutput,
)
from app.infrastructure.ml.common.preprocessing import normalize_text

ACTION_BY_LABEL = {
    "positive": "normal_priority",
    "neutral": "normal_priority",
    "negative": "review",
    "angry": "priority_support",
    "urgent": "priority_support",
    "toxic": "moderation_required",
}

RISK_BY_LABEL = {
    "positive": "low",
    "neutral": "low",
    "negative": "medium",
    "angry": "high",
    "urgent": "high",
    "toxic": "high",
}


class TextMoodClassifier(BaseClassifier):
    model_code = "text_mood"
    product_name = "TextMood Analytics"
    model_name = "Rule-Based Text Mood Baseline"
    model_version = "0.1.0"
    task_type = "sentiment_style_classification"
    supported_modes = ["basic", "standard"]
    labels = ["positive", "neutral", "negative", "angry", "urgent", "toxic"]

    def predict(self, input_data: ClassificationInput) -> ClassificationOutput:
        normalized = normalize_text(input_data.text)
        label = "neutral"
        explanation = "No strong sentiment or urgency signal was matched."
        confidence = 0.55

        if any(word in normalized for word in ("срочно", "urgent", "asap", "немедленно")):
            label, confidence, explanation = "urgent", 0.78, "Contains urgency markers."
        elif any(word in normalized for word in ("ужас", "angry", "злюсь", "ненавижу")):
            label, confidence, explanation = (
                "angry",
                0.76,
                "Contains strong dissatisfaction markers.",
            )
        elif any(word in normalized for word in ("идиот", "stupid", "hate", "тупой")):
            label, confidence, explanation = "toxic", 0.74, "Contains toxic wording markers."
        elif any(word in normalized for word in ("плохо", "bad", "terrible", "не доволен")):
            label, confidence, explanation = "negative", 0.7, "Contains negative sentiment markers."
        elif any(word in normalized for word in ("спасибо", "great", "excellent", "отлично")):
            label, confidence, explanation = (
                "positive",
                0.72,
                "Contains positive sentiment markers.",
            )

        return ClassificationOutput(
            label=label,
            confidence=confidence,
            risk_level=RISK_BY_LABEL[label],
            recommended_action=ACTION_BY_LABEL[label],
            explanation=explanation,
            raw_scores={label: confidence},
            metadata={"baseline": "rules", "mode": input_data.mode},
        )
