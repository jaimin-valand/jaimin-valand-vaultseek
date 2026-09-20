from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    host: str = os.getenv('PSE_HOST', '0.0.0.0')
    port: int = int(os.getenv('PSE_PORT', '8000'))
    api_key: str = os.getenv('PSE_API_KEY', '')
    rate_limit_per_minute: int = int(os.getenv('PSE_RATE_LIMIT_PER_MINUTE', '120'))
    max_body_bytes: int = int(os.getenv('PSE_MAX_BODY_BYTES', str(1024 * 1024)))
    max_remote_nodes: int = int(os.getenv('PSE_MAX_REMOTE_NODES', '32'))
    max_trace_limit: int = int(os.getenv('PSE_MAX_TRACE_LIMIT', '1000'))
    environment: str = os.getenv('PSE_ENV', 'development')

settings = Settings()
