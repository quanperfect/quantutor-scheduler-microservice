from functools import wraps
from custom_logging.custom_logger import get_logger

clogger = get_logger()


def handle_rabbitmq_publish_errors(func):
    """
    Decorator for rabbitmq publish operations
    returns False on any error (notification is secondary, should not crash app)
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            await func(*args, **kwargs)
            return True
        except ConnectionError as e:
            clogger.error(f"[RabbitMQ] Connection error during publish: {e}", exc_info=True)
            return False
        except TimeoutError as e:
            clogger.error(f"[RabbitMQ] Timeout error during publish: {e}", exc_info=True)
            return False
        except Exception as e:
            clogger.error(f"[RabbitMQ] Unexpected error during publish: {e}", exc_info=True)
            return False
    return wrapper


def handle_rabbitmq_consume_errors(func):
    """
    Decorator for rabbitmq consume callback wrapper
    eats all errors, logs them, allows consumer to continue
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            clogger.error(f"[RabbitMQ] Error in consume callback: {e}", exc_info=True)
    return wrapper
