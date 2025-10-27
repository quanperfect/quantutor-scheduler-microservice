import asyncio
import json
from typing import Any, Callable, Dict, Optional
from aio_pika import (
    connect_robust,
    Message,
    Channel,
    Connection,
    ExchangeType,
    Exchange,
    Queue,
)
from aio_pika.abc import AbstractIncomingMessage
from scheduler.config import RABBITMQ_EXCHANGE
from custom_logging.custom_logger import get_logger

clogger = get_logger()
MODULE_NAME = "RabbitMQController"


class RabbitMQController:
    _instance: Optional["RabbitMQController"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._connection: Optional[Connection] = None
            self._channel: Optional[Channel] = None
            self._exchange: Optional[Exchange] = None
            self._rabbitmq_url: Optional[str] = None
            self._exchange_name: str = RABBITMQ_EXCHANGE
            self._initialized = True

    async def connect(self, rabbitmq_url: str) -> None:
        async with self._lock:
            if self._connection and not self._connection.is_closed:
                clogger.info(f"[{MODULE_NAME}] Already connected to RabbitMQ")
                return

            try:
                self._rabbitmq_url = rabbitmq_url
                self._connection = await connect_robust(rabbitmq_url)
                self._channel = await self._connection.channel()
                await self._channel.set_qos(prefetch_count=10)

                self._exchange = await self._channel.declare_exchange(
                    self._exchange_name, ExchangeType.TOPIC, durable=True
                )

                clogger.info(f"[{MODULE_NAME}] Connected to RabbitMQ at {rabbitmq_url}")
            except Exception as e:
                clogger.error(f"[{MODULE_NAME}] Failed to connect to RabbitMQ: {e}")
                raise

    async def disconnect(self) -> None:
        async with self._lock:
            if self._connection and not self._connection.is_closed:
                try:
                    await self._connection.close()
                    clogger.info(f"[{MODULE_NAME}] Disconnected from RabbitMQ")
                except Exception as e:
                    clogger.error(
                        f"[{MODULE_NAME}] Error disconnecting from RabbitMQ: {e}"
                    )
            self._connection = None
            self._channel = None
            self._exchange = None

    async def publish(
        self,
        routing_key: Optional[str] = None,
        message: Optional[Dict[str, str]] = None,
        persistent: bool = True,
    ) -> bool:
        try:
            if not routing_key:
                clogger.error(
                    f"[{MODULE_NAME}] Bad argument (routing_key) passed for publishing, cannot publish."
                )
                return False
            if not message:
                clogger.error(
                    f"[{MODULE_NAME}] Bad argument (message) passed for publishing, cannot publish."
                )
                return False
            if not self._exchange:
                clogger.error(
                    f"[{MODULE_NAME}] Not connected to RabbitMQ, cannot publish."
                )
                return False

            message_body = json.dumps(message).encode()
            aio_message = Message(
                body=message_body,
                content_type="application/json",
                delivery_mode=2 if persistent else 1,
            )

            await self._exchange.publish(aio_message, routing_key=routing_key)

            clogger.info(f"[{MODULE_NAME}] Published message to {routing_key}")
            return True
        except Exception as e:
            clogger.error(
                f"[{MODULE_NAME}] Failed to publish message to {routing_key}: {e}",
                exc_info=True,
            )
            return False

    async def consume(
        self,
        queue_name: str,
        routing_keys: list[str],
        callback: Callable[[dict], asyncio.coroutine],
        auto_ack: bool = False,
    ) -> None:
        if not self._channel or not self._exchange:
            raise RuntimeError(f"[{MODULE_NAME}] Not connected to RabbitMQ")

        try:
            queue: Queue = await self._channel.declare_queue(queue_name, durable=True)

            for routing_key in routing_keys:
                await queue.bind(self._exchange, routing_key=routing_key)
                clogger.info(
                    f"[{MODULE_NAME}] Bound queue '{queue_name}' to routing key '{routing_key}'"
                )

            async def _on_message(message: AbstractIncomingMessage) -> None:
                try:
                    body = json.loads(message.body.decode())
                    clogger.info(
                        f"[{MODULE_NAME}] Received message from queue '{queue_name}': {body.get('event_type', 'unknown')}"
                    )

                    await callback(body)

                    if not auto_ack:
                        await message.ack()
                except json.JSONDecodeError as e:
                    clogger.error(f"[{MODULE_NAME}] Failed to decode message: {e}")
                    await message.reject(requeue=False)
                except Exception as e:
                    clogger.error(f"[{MODULE_NAME}] Error processing message: {e}")
                    await message.reject(requeue=True)

            await queue.consume(_on_message, no_ack=auto_ack)
            clogger.info(f"[{MODULE_NAME}] Consuming from queue '{queue_name}'")

        except Exception as e:
            clogger.error(
                f"[{MODULE_NAME}] Failed to setup consumer for queue '{queue_name}': {e}"
            )
            raise


# singleton instance
rabbitmq_controller = RabbitMQController()
