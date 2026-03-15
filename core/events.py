from typing import Any

import structlog

from core.config import get_settings

logger = structlog.get_logger(__name__)


class EventPublisher:
    def __init__(self, exchange_name: str | None = None) -> None:
        settings = get_settings()
        self.exchange_name = exchange_name or settings.rabbitmq_exchange

    async def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        # TODO: publish events through RabbitMQ once async connection lifecycle is introduced.
        logger.info(
            'event.publish.skipped',
            exchange=self.exchange_name,
            routing_key=routing_key,
            payload=payload,
        )
