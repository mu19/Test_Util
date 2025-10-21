"""
Settings Manager for Log Collector

설정 파일 로드, 저장, 관리를 담당하는 모듈
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from core.models import (
    SSHConfig,
    LogSourceConfig,
    LogSourceType,
    FilterType
)
from utils.logger import get_logger

logger = get_logger("Settings")


class SettingsManager:
    """설정 관리자 - 싱글톤 패턴"""
    _instance = None
    _config: Optional[Dict[str, Any]] = None
    _config_file: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """초기화"""
        if self._config is None:
            self._initialize()

    def _initialize(self):
        """설정 초기화"""
        # 설정 파일 경로 설정: 프로그램 실행 폴더/config/config.json
        import sys
        if getattr(sys, 'frozen', False):
            # PyInstaller로 패키징된 경우
            app_dir = os.path.dirname(sys.executable)
        else:
            # 개발 환경
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        config_dir = os.path.join(app_dir, 'config')
        Path(config_dir).mkdir(parents=True, exist_ok=True)
        self._config_file = os.path.join(config_dir, 'config.json')

        # 설정 로드
        self.load()

    def load(self) -> bool:
        """
        설정 파일 로드

        Returns:
            로드 성공 여부
        """
        try:
            # 사용자 설정 파일이 존재하면 로드
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                logger.info(f"설정 파일 로드 성공: {self._config_file}")
            else:
                # 없으면 기본 설정 로드
                self._load_default_config()
                # 기본 설정을 사용자 설정 파일로 저장
                self.save()

            return True

        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            # 실패하면 기본 설정 로드
            self._load_default_config()
            return False

    def _load_default_config(self):
        """기본 설정 로드"""
        # 프로젝트 루트의 config/default_config.json 로드
        default_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config',
            'default_config.json'
        )

        try:
            with open(default_config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            logger.info("기본 설정 로드 완료")
        except Exception as e:
            logger.error(f"기본 설정 로드 실패: {e}")
            # 최소한의 하드코딩된 기본값
            self._config = self._get_minimal_config()

    def _get_minimal_config(self) -> Dict[str, Any]:
        """최소 기본 설정"""
        return {
            "version": "1.0.0",
            "ssh": {
                "username": "root",
                "password": "",
                "port": 22,
                "timeout": 300,
                "keep_alive": True,
                "keep_alive_interval": 30
            },
            "log_sources": {
                "linux_kernel": {
                    "enabled": True,
                    "path": "/var/log/",
                    "filter_type": "all",
                    "filter_value": None,
                    "compress": False,
                    "delete_after": False
                },
                "linux_server": {
                    "enabled": True,
                    "path": "/opt/myapp/logs/",
                    "filter_type": "all",
                    "filter_value": None,
                    "compress": False,
                    "delete_after": False
                },
                "windows_client": {
                    "enabled": True,
                    "path": "C:\\Program Files\\MyApp\\Logs\\",
                    "filter_type": "all",
                    "filter_value": None,
                    "compress": False,
                    "delete_after": False
                }
            },
            "common": {
                "save_path": "C:\\Logs\\collected",
                "max_concurrent_downloads": 3,
                "buffer_size": 32768,
                "compression_level": 6
            },
            "last_connection": {
                "ip": "192.168.1.100",
                "port": 22
            }
        }

    def save(self) -> bool:
        """
        설정 파일 저장

        Returns:
            저장 성공 여부
        """
        if self._config is None or self._config_file is None:
            logger.error("설정이 초기화되지 않았습니다.")
            return False

        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"설정 파일 저장 성공: {self._config_file}")
            return True

        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
            return False

    def get_ssh_config(self, host: str = "") -> SSHConfig:
        """
        SSH 설정 반환

        Args:
            host: 연결할 호스트 IP

        Returns:
            SSHConfig 인스턴스
        """
        ssh_data = self._config.get('ssh', {})
        last_conn = self._config.get('last_connection', {})

        return SSHConfig(
            host=host or last_conn.get('ip', ''),
            port=ssh_data.get('port', 22),
            username=ssh_data.get('username', 'root'),
            password=ssh_data.get('password', ''),
            timeout=ssh_data.get('timeout', 300),
            keep_alive=ssh_data.get('keep_alive', True),
            keep_alive_interval=ssh_data.get('keep_alive_interval', 30)
        )

    def get_log_source_config(self, source_type: LogSourceType) -> LogSourceConfig:
        """
        로그 소스 설정 반환

        Args:
            source_type: 로그 소스 타입

        Returns:
            LogSourceConfig 인스턴스
        """
        sources = self._config.get('log_sources', {})
        source_data = sources.get(source_type.value, {})

        filter_type_str = source_data.get('filter_type', 'all')
        filter_type = FilterType(filter_type_str)

        return LogSourceConfig(
            source_type=source_type,
            path=source_data.get('path', ''),
            enabled=source_data.get('enabled', True),
            filter_type=filter_type,
            filter_value=source_data.get('filter_value'),
            compress=source_data.get('compress', False),
            delete_after=source_data.get('delete_after', False)
        )

    def update_ssh_config(self, ssh_config: SSHConfig):
        """
        SSH 설정 업데이트

        Args:
            ssh_config: 업데이트할 SSH 설정
        """
        self._config['ssh'] = {
            'username': ssh_config.username,
            'password': ssh_config.password,
            'port': ssh_config.port,
            'timeout': ssh_config.timeout,
            'keep_alive': ssh_config.keep_alive,
            'keep_alive_interval': ssh_config.keep_alive_interval
        }

    def update_log_source_config(self, log_config: LogSourceConfig):
        """
        로그 소스 설정 업데이트

        Args:
            log_config: 업데이트할 로그 소스 설정
        """
        source_key = log_config.source_type.value
        if 'log_sources' not in self._config:
            self._config['log_sources'] = {}

        self._config['log_sources'][source_key] = {
            'enabled': log_config.enabled,
            'path': log_config.path,
            'filter_type': log_config.filter_type.value,
            'filter_value': log_config.filter_value,
            'compress': log_config.compress,
            'delete_after': log_config.delete_after
        }

    def update_last_connection(self, host: str, port: int):
        """
        마지막 연결 정보 업데이트

        Args:
            host: 연결한 호스트 IP
            port: 연결한 포트
        """
        self._config['last_connection'] = {
            'ip': host,
            'port': port
        }

    def get_save_path(self) -> str:
        """저장 경로 반환"""
        return self._config.get('common', {}).get('save_path', 'C:\\Logs\\collected')

    def set_save_path(self, path: str):
        """저장 경로 설정"""
        if 'common' not in self._config:
            self._config['common'] = {}
        self._config['common']['save_path'] = path

    def get_max_concurrent_downloads(self) -> int:
        """최대 동시 다운로드 수 반환"""
        return self._config.get('common', {}).get('max_concurrent_downloads', 3)

    def get_buffer_size(self) -> int:
        """버퍼 크기 반환"""
        return self._config.get('common', {}).get('buffer_size', 32768)

    def get_compression_level(self) -> int:
        """압축 레벨 반환 (0-9)"""
        return self._config.get('common', {}).get('compression_level', 6)

    def get_config(self) -> Dict[str, Any]:
        """전체 설정 딕셔너리 반환"""
        return self._config.copy() if self._config else {}

    def update_config(self, key: str, value: Any):
        """
        설정값 업데이트

        Args:
            key: 설정 키 (점 표기법 지원, 예: 'ssh.username')
            value: 설정값
        """
        keys = key.split('.')
        config = self._config

        # 중첩된 딕셔너리 탐색
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # 마지막 키에 값 설정
        config[keys[-1]] = value

    def reset_to_default(self):
        """설정을 기본값으로 초기화"""
        self._load_default_config()
        self.save()
        logger.info("설정이 기본값으로 초기화되었습니다.")
