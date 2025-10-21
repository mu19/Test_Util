"""
Data models for Log Collector

모든 데이터 구조를 정의하는 모듈
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from datetime import datetime


class LogSourceType(Enum):
    """로그 소스 타입"""
    LINUX_KERNEL = "linux_kernel"
    LINUX_SERVER = "linux_server"
    WINDOWS_CLIENT = "windows_client"


class FilterType(Enum):
    """파일 필터 타입"""
    ALL = "all"
    REGEX = "regex"
    DATE = "date"


@dataclass
class FileInfo:
    """파일 정보"""
    name: str
    path: str
    size: int
    modified_time: datetime
    is_remote: bool

    def get_size_str(self) -> str:
        """파일 크기를 사람이 읽기 쉬운 형태로 반환"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

    def get_full_path(self) -> str:
        """전체 경로 반환"""
        if self.path.endswith('/') or self.path.endswith('\\'):
            return f"{self.path}{self.name}"
        else:
            separator = '/' if self.is_remote else '\\'
            return f"{self.path}{separator}{self.name}"

    def get_modified_time_str(self) -> str:
        """수정 시간을 문자열로 반환"""
        if isinstance(self.modified_time, datetime):
            return self.modified_time.strftime("%Y-%m-%d %H:%M:%S")
        return str(self.modified_time)


@dataclass
class SSHConfig:
    """SSH 연결 설정"""
    host: str
    port: int = 22
    username: str = "root"
    password: str = ""
    timeout: int = 300
    keep_alive: bool = True
    keep_alive_interval: int = 30

    def is_valid(self) -> bool:
        """설정이 유효한지 확인"""
        return bool(self.host and self.username and self.port > 0)


@dataclass
class LogSourceConfig:
    """로그 소스 설정"""
    source_type: LogSourceType
    path: str
    enabled: bool = True
    filter_type: FilterType = FilterType.ALL
    filter_value: Optional[str] = None
    compress: bool = False
    delete_after: bool = False

    def is_remote(self) -> bool:
        """원격 소스인지 확인"""
        return self.source_type in [LogSourceType.LINUX_KERNEL, LogSourceType.LINUX_SERVER]

    def get_display_name(self) -> str:
        """표시용 이름 반환"""
        names = {
            LogSourceType.LINUX_KERNEL: "제어기 커널 로그",
            LogSourceType.LINUX_SERVER: "제어기 로그",
            LogSourceType.WINDOWS_CLIENT: "사용자 SW 로그"
        }
        return names.get(self.source_type, "Unknown")


@dataclass
class CollectionResult:
    """파일 수집 결과"""
    success: bool
    total_files: int = 0
    collected_files: int = 0
    failed_files: int = 0
    total_size: int = 0
    error_message: Optional[str] = None
    file_list: List[str] = field(default_factory=list)

    def get_success_rate(self) -> float:
        """성공률 반환 (0.0 ~ 1.0)"""
        if self.total_files == 0:
            return 0.0
        return self.collected_files / self.total_files

    def get_summary(self) -> str:
        """결과 요약 문자열 반환"""
        if not self.success:
            return f"실패: {self.error_message}"
        return f"성공: {self.collected_files}/{self.total_files} 파일 수집 완료"


@dataclass
class ProgressInfo:
    """진행 상황 정보"""
    current_file: str = ""
    current_index: int = 0
    total_files: int = 0
    current_file_progress: int = 0  # 0-100
    total_progress: int = 0  # 0-100
    bytes_transferred: int = 0
    total_bytes: int = 0
    is_complete: bool = False
    is_cancelled: bool = False

    def get_progress_text(self) -> str:
        """진행 상황 텍스트 반환"""
        if self.is_complete:
            return "완료"
        if self.is_cancelled:
            return "취소됨"
        if self.total_files == 0:
            return "대기 중..."
        return f"{self.current_file} ({self.current_index}/{self.total_files}) - {self.total_progress}%"


class CancelToken:
    """취소 토큰 - 작업 취소를 위한 플래그"""
    def __init__(self):
        self._cancelled = False

    def cancel(self):
        """취소 요청"""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        """취소 여부 확인"""
        return self._cancelled

    def reset(self):
        """취소 상태 초기화"""
        self._cancelled = False
