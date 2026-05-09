class FakeAuditLogRepository:
    def __init__(self) -> None:
        self.events = []

    async def record(self, **kwargs):
        self.events.append(kwargs)
