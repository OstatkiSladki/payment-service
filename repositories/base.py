from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
  def __init__(self, session: AsyncSession, model_type: type[ModelT]) -> None:
    self.session = session
    self.model_type = model_type

  async def get_by_id(self, entity_id: int) -> ModelT | None:
    result = await self.session.execute(
      select(self.model_type).where(self.model_type.id == entity_id)
    )
    return result.scalar_one_or_none()

  async def add(self, instance: ModelT) -> ModelT:
    self.session.add(instance)
    await self.session.flush()
    return instance
