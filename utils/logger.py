"""
Logging utility for Log Collector

애플리케이션 전체의 로깅을 관리하는 유틸리티
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable


class UILogHandler(logging.Handler):
    """UI 로그 윈도우로 로그를 출력하는 핸들러"""

    def __init__(self, log_callback: Callable[[str, str], None]):
        """
        초기화

        Args:
            log_callback: 로그 메시지를 UI로 전달할 콜백 함수 (message, level)
        """
        super().__init__()
        self.log_callback = log_callback

    def emit(self, record):
        """로그 레코드를 UI로 전달"""
        try:
            # 로그 레벨 이름 가져오기
            level = record.levelname

            # 로그 메시지 포맷팅
            msg = self.format(record)

            # UI 콜백 호출
            if self.log_callback:
                self.log_callback(msg, level)
        except Exception:
            self.handleError(record)


class LoggerManager:
    """로거 관리자 - 싱글톤 패턴"""
    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def setup_logger(cls,
                     name: str = "LogCollector",
                     log_level: int = logging.INFO,
                     log_to_file: bool = True,
                     log_dir: Optional[str] = None) -> logging.Logger:
        """
        로거 설정

        Args:
            name: 로거 이름
            log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: 파일 로깅 여부
            log_dir: 로그 파일 저장 디렉토리

        Returns:
            설정된 로거 인스턴스
        """
        if cls._logger is not None:
            return cls._logger

        # 로거 생성
        logger = logging.getLogger(name)
        logger.setLevel(log_level)

        # 기존 핸들러 제거
        logger.handlers.clear()

        # 로그 포맷 설정
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 콘솔 핸들러 추가
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 파일 핸들러 추가
        if log_to_file:
            if log_dir is None:
                # 기본 로그 디렉토리: 프로그램 실행 폴더/logs
                import sys
                if getattr(sys, 'frozen', False):
                    # PyInstaller로 패키징된 경우
                    app_dir = os.path.dirname(sys.executable)
                else:
                    # 개발 환경
                    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

                log_dir = os.path.join(app_dir, 'logs')

            # 로그 디렉토리 생성
            Path(log_dir).mkdir(parents=True, exist_ok=True)

            # 로그 파일 이름: log_collector_YYYYMMDD.log
            log_filename = f"log_collector_{datetime.now().strftime('%Y%m%d')}.log"
            log_filepath = os.path.join(log_dir, log_filename)

            file_handler = logging.FileHandler(
                log_filepath,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            logger.info(f"로그 파일: {log_filepath}")

        cls._logger = logger
        return logger

    @classmethod
    def get_logger(cls, name: Optional[str] = None) -> logging.Logger:
        """
        로거 인스턴스 반환

        Args:
            name: 하위 로거 이름 (선택사항)

        Returns:
            로거 인스턴스
        """
        if cls._logger is None:
            cls.setup_logger()

        if name:
            return logging.getLogger(f"LogCollector.{name}")
        return cls._logger

    @classmethod
    def add_ui_handler(cls, log_callback: Callable[[str, str], None]) -> None:
        """
        UI 로그 핸들러 추가

        Args:
            log_callback: 로그 메시지를 UI로 전달할 콜백 함수
        """
        if cls._logger is None:
            cls.setup_logger()

        # UI 핸들러 생성
        ui_handler = UILogHandler(log_callback)
        ui_handler.setLevel(logging.DEBUG)

        # 포맷터 설정 (타임스탬프 제외 - UI에서 추가)
        formatter = logging.Formatter(
            fmt='%(name)s | %(message)s'
        )
        ui_handler.setFormatter(formatter)

        # 루트 로거에 핸들러 추가
        cls._logger.addHandler(ui_handler)

    @classmethod
    def remove_ui_handler(cls) -> None:
        """UI 로그 핸들러 제거"""
        if cls._logger is None:
            return

        # UILogHandler 타입의 핸들러만 제거
        handlers_to_remove = [h for h in cls._logger.handlers if isinstance(h, UILogHandler)]
        for handler in handlers_to_remove:
            cls._logger.removeHandler(handler)


# 편의 함수
def setup_logger(name: str = "LogCollector",
                log_level: int = logging.INFO,
                log_to_file: bool = True,
                log_dir: Optional[str] = None) -> logging.Logger:
    """
    로거 설정 편의 함수

    Args:
        name: 로거 이름
        log_level: 로그 레벨
        log_to_file: 파일 로깅 여부
        log_dir: 로그 파일 저장 디렉토리

    Returns:
        설정된 로거 인스턴스
    """
    return LoggerManager.setup_logger(name, log_level, log_to_file, log_dir)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    로거 인스턴스 반환 편의 함수

    Args:
        name: 하위 로거 이름 (선택사항)

    Returns:
        로거 인스턴스
    """
    return LoggerManager.get_logger(name)


def add_ui_handler(log_callback: Callable[[str, str], None]) -> None:
    """
    UI 로그 핸들러 추가 편의 함수

    Args:
        log_callback: 로그 메시지를 UI로 전달할 콜백 함수
    """
    LoggerManager.add_ui_handler(log_callback)


def remove_ui_handler() -> None:
    """UI 로그 핸들러 제거 편의 함수"""
    LoggerManager.remove_ui_handler()


# 로그 레벨 상수
LOG_LEVEL_DEBUG = logging.DEBUG
LOG_LEVEL_INFO = logging.INFO
LOG_LEVEL_WARNING = logging.WARNING
LOG_LEVEL_ERROR = logging.ERROR
LOG_LEVEL_CRITICAL = logging.CRITICAL
