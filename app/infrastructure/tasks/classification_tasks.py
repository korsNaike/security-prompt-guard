from app.domain.ml.classifier_contracts import ClassificationInput
from app.infrastructure.ml.loader import model_registry
from app.infrastructure.tasks.celery_app import celery_app


@celery_app.task(
    name="classification.run",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def run_classification_task(request_id: str, model_code: str, mode: str, text: str) -> dict:
    classifier = model_registry.get(model_code)
    output = classifier.predict(ClassificationInput(text=text, model_code=model_code, mode=mode))
    return {
        "request_id": request_id,
        "model_code": model_code,
        "model_version": classifier.model_version,
        "label": output.label,
        "confidence": output.confidence,
        "risk_level": output.risk_level,
        "recommended_action": output.recommended_action,
        "explanation": output.explanation,
        "raw_scores": output.raw_scores,
        "metadata": output.metadata,
    }
