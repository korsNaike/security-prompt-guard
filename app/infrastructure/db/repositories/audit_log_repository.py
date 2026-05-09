from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import AuditLogModel


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        action: str,
        entity_type: str,
        actor_user_id: UUID | None = None,
        entity_id: UUID | str | None = None,
        metadata: dict | None = None,
    ) -> AuditLogModel:
        log = AuditLogModel(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            event_metadata=metadata,
        )
        self.session.add(log)
        await self.session.flush()
        return log
