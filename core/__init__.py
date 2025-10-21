"""
Core module for Log Collector
"""

from .models import (
    LogSourceType,
    FilterType,
    FileInfo,
    LogSourceConfig,
    SSHConfig,
    CollectionResult
)

__all__ = [
    'LogSourceType',
    'FilterType',
    'FileInfo',
    'LogSourceConfig',
    'SSHConfig',
    'CollectionResult'
]
