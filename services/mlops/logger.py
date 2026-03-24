"""Structured logging for LLM operations."""
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class LogEntry:
    level: str
    service: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict = field(default_factory=dict)


class StructuredLogger:
    """Centralized structured logger for all microservices."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._logs = []
        return cls._instance

    def log(self, level: str, service: str, message: str, **metadata):
        entry = LogEntry(
            level=level, service=service, message=message, metadata=metadata
        )
        self._logs.append(entry)
        print(
            json.dumps(
                {
                    "level": level,
                    "service": service,
                    "msg": message,
                    "ts": entry.timestamp,
                    **metadata,
                }
            )
        )

    def info(self, service: str, message: str, **kw):
        self.log("INFO", service, message, **kw)

    def warn(self, service: str, message: str, **kw):
        self.log("WARN", service, message, **kw)

    def error(self, service: str, message: str, **kw):
        self.log("ERROR", service, message, **kw)

    def get_logs(
        self, service: str = None, level: str = None, limit: int = 100
    ) -> list[dict]:
        filtered = self._logs
        if service:
            filtered = [l for l in filtered if l.service == service]
        if level:
            filtered = [l for l in filtered if l.level == level]
        return [
            {
                "level": l.level,
                "service": l.service,
                "message": l.message,
                "timestamp": l.timestamp,
                "metadata": l.metadata,
            }
            for l in filtered[-limit:]
        ]

    def clear(self):
        self._logs.clear()
        StructuredLogger._instance = None
