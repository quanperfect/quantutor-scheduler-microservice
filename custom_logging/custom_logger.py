import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json
import traceback


from scheduler.config import (
    APP_NAME,
    LOG_BACKUP_COUNT,
    LOG_CONSOLE,
    LOG_DIR,
    LOG_JSON,
    LOG_LEVEL,
    LOG_MAX_FILE_SIZE,
)


class ProdLogger:
    def __init__(
        self,
        name: str,
        log_level: str,
        log_dir: str,
        max_file_size: int,
        backup_count: int,
        console_output: bool,
        json_logging: bool,
    ):
        self.name = name
        self.log_level = getattr(logging, log_level.upper())
        self.log_dir = Path(log_dir)
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.console_output = console_output
        self.json_logging = json_logging

        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up the logger with appropriate handlers and formatters"""

        logger = logging.getLogger(self.name)
        logger.setLevel(self.log_level)

        logger.handlers.clear()
        logger.propagate = False

        if self.console_output:
            logger.addHandler(self._create_console_handler())

        logger.addHandler(self._create_file_handler())
        logger.addHandler(self._create_error_file_handler())

        return logger

    def _create_console_handler(self) -> logging.StreamHandler:
        """Create console handler with colored output"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self.log_level)

        if self.json_logging:
            handler.setFormatter(self._create_json_formatter())
        else:
            handler.setFormatter(self._create_colored_formatter())

        return handler

    def _create_file_handler(self) -> logging.handlers.RotatingFileHandler:
        """Create rotating file handler for all logs"""
        log_file = self.log_dir / f"{self.name.lower()}.log"

        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        handler.setLevel(self.log_level)

        if self.json_logging:
            handler.setFormatter(self._create_json_formatter())
        else:
            handler.setFormatter(self._create_detailed_formatter())

        return handler

    def _create_error_file_handler(self) -> logging.handlers.RotatingFileHandler:
        """Create separate rotating file handler for errors only"""
        error_log_file = self.log_dir / f"{self.name.lower()}_errors.log"

        handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        handler.setLevel(logging.ERROR)

        if self.json_logging:
            handler.setFormatter(self._create_json_formatter())
        else:
            handler.setFormatter(self._create_detailed_formatter())

        return handler

    def _create_colored_formatter(self) -> logging.Formatter:
        """Create formatter with colors for console output"""

        class ColoredFormatter(logging.Formatter):
            """Formatter with color support"""

            COLORS = {
                "DEBUG": "\033[36m",  # Cyan
                "INFO": "\033[32m",  # Green
                "WARNING": "\033[33m",  # Yellow
                "ERROR": "\033[31m",  # Red
                "CRITICAL": "\033[35m",  # Magenta
                "RESET": "\033[0m",  # Reset
            }

            def format(self, record):
                log_color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
                reset = self.COLORS["RESET"]

                formatter = logging.Formatter(
                    # f'{log_color}%(asctime)s - %(name)s - %(levelname)s{reset} - %(message)s',
                    f"{log_color}%(asctime)s - %(levelname)s{reset} - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )

                return formatter.format(record)

        return ColoredFormatter()

    def _create_detailed_formatter(self) -> logging.Formatter:
        """Create detailed formatter for file output"""
        return logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def _create_json_formatter(self) -> logging.Formatter:
        """Create JSON formatter for structured logging"""

        class JSONFormatter(logging.Formatter):
            """JSON formatter for structured logging"""

            def format(self, record):
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "filename": record.filename,
                    "line_number": record.lineno,
                    "function": record.funcName,
                    "process_id": record.process,
                    "thread_id": record.thread,
                }

                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)

                if hasattr(record, "extra_data"):
                    log_entry["extra"] = record.extra_data

                return json.dumps(log_entry, ensure_ascii=False)

        return JSONFormatter()

    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log info message with optional structured data"""
        self._log_with_extra(logging.INFO, message, extra_data)

    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log debug message with optional structured data"""
        self._log_with_extra(logging.DEBUG, message, extra_data)

    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log warning message with optional structured data"""
        self._log_with_extra(logging.WARNING, message, extra_data)

    def error(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ):
        """Log error message with optional structured data and exception info"""
        if exc_info:
            self.logger.error(
                message,
                exc_info=True,
                extra={"extra_data": extra_data} if extra_data else {},
            )
        else:
            self._log_with_extra(logging.ERROR, message, extra_data)

    def critical(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ):
        """Log critical messcreate_age with optional structured data and exception info"""
        if exc_info:
            self.logger.critical(
                message,
                exc_info=True,
                extra={"extra_data": extra_data} if extra_data else {},
            )
        else:
            self._log_with_extra(logging.CRITICAL, message, extra_data)

    def exception(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log exception with full traceback"""
        self.logger.error(
            message,
            exc_info=True,
            extra={"extra_data": extra_data} if extra_data else {},
        )

    def _log_with_extra(
        self, level: int, message: str, extra_data: Optional[Dict[str, Any]]
    ):
        """Internal method to log with extra structured data"""
        if extra_data:
            self.logger.log(level, message, extra={"extra_data": extra_data})
        else:
            self.logger.log(level, message)

    def log_performance(
        self,
        operation: str,
        duration: float,
        extra_data: Optional[Dict[str, Any]] = None,
    ):
        """Log performance metrics"""
        perf_data = {
            "operation": operation,
            "duration_seconds": round(duration, 3),
            "performance_log": True,
        }

        if extra_data:
            perf_data.update(extra_data)

        self.info(f"Performance: {operation} completed in {duration:.3f}s", perf_data)

    def log_api_call(
        self,
        method: str,
        url: str,
        status_code: int,
        duration: float,
        request_id: Optional[str] = None,
    ):
        """Log API call with structured data"""
        api_data = {
            "api_call": True,
            "method": method,
            "url": url,
            "status_code": status_code,
            "duration_seconds": round(duration, 3),
            "request_id": request_id,
        }

        level = logging.INFO if 200 <= status_code < 400 else logging.ERROR
        message = f"API {method} {url} -> {status_code} ({duration:.3f}s)"

        self._log_with_extra(level, message, api_data)

    def set_level(self, level: str):
        """Change logging level at runtime"""
        new_level = getattr(logging, level.upper())
        self.logger.setLevel(new_level)

        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.handlers.RotatingFileHandler
            ):
                handler.setLevel(max(new_level, logging.INFO))
            else:
                handler.setLevel(new_level)



_global_logger: Optional[ProdLogger] = None


def setup_production_logger(
    name: str = APP_NAME,
    log_level: str = LOG_LEVEL,
    log_dir: str = LOG_DIR,
    max_file_size: int = LOG_MAX_FILE_SIZE,
    backup_count: int = LOG_BACKUP_COUNT,
    console_output: bool = LOG_CONSOLE,
    json_logging: bool = LOG_JSON,
) -> ProdLogger:
    global _global_logger

    print(f"Setting up logger with level: {log_level}")

    _global_logger = ProdLogger(
        name=name,
        log_level=log_level,
        log_dir=log_dir,
        max_file_size=max_file_size,
        backup_count=backup_count,
        console_output=console_output,
        json_logging=json_logging,
    )

    return _global_logger


def get_logger() -> ProdLogger:
    """Get the global logger instance"""
    global _global_logger

    if _global_logger is None:
        _global_logger = setup_production_logger()

    return _global_logger



logger = get_logger().logger
