"""
Logging utility for Log Collector

애플리케이션 전체의 로깅을 관리하는 유틸리티
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


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
                # 기본 로그 디렉토리: %APPDATA%/LogCollector/logs
                log_dir = os.path.join(
                    os.getenv('APPDATA', '.'),
                    'LogCollector',
                    'logs'
                )

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


# 로그 레벨 상수
LOG_LEVEL_DEBUG = logging.DEBUG
LOG_LEVEL_INFO = logging.INFO
LOG_LEVEL_WARNING = logging.WARNING
LOG_LEVEL_ERROR = logging.ERROR
LOG_LEVEL_CRITICAL = logging.CRITICAL
