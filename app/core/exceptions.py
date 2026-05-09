class UniClassifyError(Exception):
    """Base application exception."""


class ModelNotFoundError(UniClassifyError):
    def __init__(self, model_code: str) -> None:
        super().__init__(f"Model '{model_code}' is not registered")
        self.model_code = model_code


class UnsupportedModeError(UniClassifyError):
    def __init__(self, model_code: str, mode: str) -> None:
        super().__init__(f"Mode '{mode}' is not supported by model '{model_code}'")
        self.model_code = model_code
        self.mode = mode
