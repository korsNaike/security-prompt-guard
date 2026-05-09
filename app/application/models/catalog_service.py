from app.schemas.models import ModelInfo


def to_model_info(model) -> ModelInfo:
    active_pricing = [price for price in model.pricing if getattr(price, "is_active", True)]
    return ModelInfo(
        model_code=model.model_code,
        product_name=model.product_name,
        model_name=model.model_name,
        version=model.model_version,
        task_type=model.task_type,
        supported_modes=[price.mode for price in active_pricing],
        labels=model.labels,
        pricing={price.mode: price.cost for price in active_pricing},
    )
