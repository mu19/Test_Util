"""
SSH Manager for Log Collector

SSH/SFTP 연결 관리 및 원격 파일 작업을 담당하는 모듈
"""

import paramiko
import threading
import time
import os
from typing import Optional, List, Callable
from datetime import datetime
from pathlib import Path

from core.models import SSHConfig, FileInfo
from utils.logger import get_logger

logger = get_logger("SSHManager")


class SSHConnectionError(Exception):
    """SSH 연결 오류"""
    pass


class SSHManager:
    """SSH/SFTP 연결 관리자"""

    def __init__(self):
        """초기화"""
        self._ssh_client: Optional[paramiko.SSHClient] = None
        self._sftp_client: Optional[paramiko.SFTPClient] = None
        self._config: Optional[SSHConfig] = None
        self._connected = False
        self._keep_alive_thread: Optional[threading.Thread] = None
        self._keep_alive_stop_event = threading.Event()
        self._lock = threading.Lock()

    def connect(self, config: SSHConfig) -> bool:
        """
        SSH 서버에 연결

        Args:
            config: SSH 연결 설정

        Returns:
            연결 성공 여부

        Raises:
            SSHConnectionError: 연결 실패시
        """
        if not config.is_valid():
            raise SSHConnectionError("SSH 설정이 유효하지 않습니다.")

        try:
            logger.info(f"SSH 연결 시도: {config.username}@{config.host}:{config.port}")

            # SSH 클라이언트 생성
            self._ssh_client = paramiko.SSHClient()
            self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # 연결
            self._ssh_client.connect(
                hostname=config.host,
                port=config.port,
                username=config.username,
                password=config.password,
                timeout=config.timeout,
                allow_agent=False,
                look_for_keys=False
            )

            # SFTP 클라이언트 생성
            self._sftp_client = self._ssh_client.open_sftp()

            self._config = config
            self._connected = True

            logger.info(f"SSH 연결 성공: {config.host}:{config.port}")

            # Keep-alive 시작
            if config.keep_alive:
                self._start_keep_alive()

            return True

        except paramiko.AuthenticationException as e:
            logger.error(f"SSH 인증 실패: {e}")
            raise SSHConnectionError(f"인증 실패: 사용자명 또는 비밀번호를 확인해주세요.")

        except paramiko.SSHException as e:
            logger.error(f"SSH 연결 실패: {e}")
            raise SSHConnectionError(f"SSH 연결 실패: {str(e)}")

        except Exception as e:
            logger.error(f"예기치 않은 오류: {e}")
            raise SSHConnectionError(f"연결 실패: {str(e)}")

    def disconnect(self):
        """SSH 연결 종료"""
        logger.info("SSH 연결 종료 시작")

        # Keep-alive 중지
        self._stop_keep_alive()

        # SFTP 클라이언트 종료
        if self._sftp_client:
            try:
                self._sftp_client.close()
            except Exception as e:
                logger.warning(f"SFTP 클라이언트 종료 중 오류: {e}")
            finally:
                self._sftp_client = None

        # SSH 클라이언트 종료
        if self._ssh_client:
            try:
                self._ssh_client.close()
            except Exception as e:
                logger.warning(f"SSH 클라이언트 종료 중 오류: {e}")
            finally:
                self._ssh_client = None

        self._connected = False
        self._config = None

        logger.info("SSH 연결 종료 완료")

    def is_connected(self) -> bool:
        """
        연결 상태 확인

        Returns:
            연결 여부
        """
        if not self._connected or not self._ssh_client:
            return False

        try:
            # 연결 상태 확인을 위한 간단한 명령 실행
            transport = self._ssh_client.get_transport()
            if transport and transport.is_active():
                return True
        except Exception as e:
            logger.warning(f"연결 상태 확인 중 오류: {e}")

        return False

    def _start_keep_alive(self):
        """Keep-alive 데몬 시작"""
        if self._keep_alive_thread and self._keep_alive_thread.is_alive():
            logger.warning("Keep-alive 스레드가 이미 실행 중입니다.")
            return

        self._keep_alive_stop_event.clear()
        self._keep_alive_thread = threading.Thread(
            target=self._keep_alive_worker,
            daemon=True,
            name="SSHKeepAlive"
        )
        self._keep_alive_thread.start()
        logger.info("Keep-alive 데몬 시작")

    def _stop_keep_alive(self):
        """Keep-alive 데몬 중지"""
        if self._keep_alive_thread and self._keep_alive_thread.is_alive():
            self._keep_alive_stop_event.set()
            self._keep_alive_thread.join(timeout=5)
            logger.info("Keep-alive 데몬 중지")

    def _keep_alive_worker(self):
        """Keep-alive 워커 스레드"""
        if not self._config:
            return

        interval = self._config.keep_alive_interval
        logger.info(f"Keep-alive 워커 시작 (간격: {interval}초)")

        while not self._keep_alive_stop_event.is_set():
            try:
                # 연결 상태 확인
                if self.is_connected():
                    # Keep-alive 패킷 전송
                    transport = self._ssh_client.get_transport()
                    if transport:
                        transport.send_ignore()
                        logger.debug("Keep-alive 패킷 전송")
                else:
                    logger.warning("SSH 연결이 끊어졌습니다. 재연결 시도...")
                    if self._config:
                        try:
                            self.connect(self._config)
                            logger.info("SSH 재연결 성공")
                        except Exception as e:
                            logger.error(f"SSH 재연결 실패: {e}")

            except Exception as e:
                logger.error(f"Keep-alive 중 오류: {e}")

            # 대기 (중지 이벤트 확인하면서)
            self._keep_alive_stop_event.wait(interval)

        logger.info("Keep-alive 워커 종료")

    def list_files(self, remote_path: str, recursive: bool = True) -> List[FileInfo]:
        """
        원격 디렉토리의 파일 목록 조회 (재귀적)

        Args:
            remote_path: 원격 디렉토리 경로
            recursive: 하위 디렉토리 포함 여부 (기본값: True)

        Returns:
            파일 정보 리스트

        Raises:
            SSHConnectionError: 연결되지 않은 경우
            Exception: 파일 목록 조회 실패
        """
        if not self.is_connected():
            raise SSHConnectionError("SSH에 연결되지 않았습니다.")

        try:
            logger.info(f"파일 목록 조회: {remote_path} (재귀: {recursive})")

            # 경로가 디렉토리인지 확인
            try:
                stat = self._sftp_client.stat(remote_path)
                import stat as stat_module
                if not stat_module.S_ISDIR(stat.st_mode):
                    raise Exception(f"{remote_path}는 디렉토리가 아닙니다.")
            except FileNotFoundError:
                raise Exception(f"경로를 찾을 수 없습니다: {remote_path}")

            # 파일 목록 조회
            file_list = []

            if recursive:
                # 재귀적으로 하위 디렉토리 포함
                self._list_files_recursive(remote_path, remote_path, file_list)
            else:
                # 현재 디렉토리만 조회
                for attr in self._sftp_client.listdir_attr(remote_path):
                    # 디렉토리는 제외
                    import stat as stat_module
                    if stat_module.S_ISDIR(attr.st_mode):
                        continue

                    # FileInfo 생성
                    file_info = FileInfo(
                        name=attr.filename,
                        path=remote_path,
                        size=attr.st_size,
                        modified_time=datetime.fromtimestamp(attr.st_mtime),
                        is_remote=True
                    )
                    file_list.append(file_info)

            logger.info(f"파일 목록 조회 완료: {len(file_list)}개")
            return file_list

        except Exception as e:
            logger.error(f"파일 목록 조회 실패: {e}")
            raise

    def _list_files_recursive(self, current_path: str, base_path: str, file_list: List[FileInfo]):
        """
        재귀적으로 파일 목록 조회 (내부 메서드)

        Args:
            current_path: 현재 탐색 중인 경로
            base_path: 기본 경로 (상대 경로 계산용)
            file_list: 파일 목록을 추가할 리스트
        """
        import stat as stat_module
        import posixpath  # 원격 경로는 항상 POSIX 형식

        try:
            for attr in self._sftp_client.listdir_attr(current_path):
                full_path = posixpath.join(current_path, attr.filename)

                if stat_module.S_ISDIR(attr.st_mode):
                    # 디렉토리면 재귀 호출
                    try:
                        self._list_files_recursive(full_path, base_path, file_list)
                    except PermissionError:
                        logger.warning(f"권한 없음 (스킵): {full_path}")
                    except Exception as e:
                        logger.warning(f"디렉토리 접근 실패 (스킵): {full_path} - {e}")
                else:
                    # 파일이면 리스트에 추가
                    try:
                        # 상대 경로 계산
                        if current_path == base_path:
                            relative_path = attr.filename
                        else:
                            # base_path를 기준으로 상대 경로 계산
                            relative_path = posixpath.relpath(full_path, base_path)

                        file_info = FileInfo(
                            name=relative_path,  # 하위 폴더 포함한 상대 경로
                            path=base_path,
                            size=attr.st_size,
                            modified_time=datetime.fromtimestamp(attr.st_mtime),
                            is_remote=True
                        )
                        file_list.append(file_info)
                    except Exception as e:
                        logger.warning(f"파일 정보 조회 실패 (스킵): {full_path} - {e}")

        except PermissionError:
            logger.warning(f"권한 없음 (스킵): {current_path}")
        except Exception as e:
            logger.warning(f"디렉토리 목록 조회 실패 (스킵): {current_path} - {e}")

    def download_file(self,
                     remote_path: str,
                     local_path: str,
                     progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        원격 파일 다운로드

        Args:
            remote_path: 원격 파일 경로
            local_path: 로컬 저장 경로
            progress_callback: 진행률 콜백 함수 (전송된 바이트, 전체 바이트)

        Returns:
            다운로드 성공 여부

        Raises:
            SSHConnectionError: 연결되지 않은 경우
        """
        if not self.is_connected():
            raise SSHConnectionError("SSH에 연결되지 않았습니다.")

        try:
            logger.info(f"파일 다운로드 시작: {remote_path} -> {local_path}")

            # 로컬 디렉토리 생성
            local_dir = os.path.dirname(local_path)
            if local_dir:
                Path(local_dir).mkdir(parents=True, exist_ok=True)

            # 파일 크기 확인
            file_stat = self._sftp_client.stat(remote_path)
            file_size = file_stat.st_size

            # 진행률 콜백 래퍼
            def callback_wrapper(transferred, total):
                if progress_callback:
                    progress_callback(transferred, total)

            # 파일 다운로드
            self._sftp_client.get(
                remote_path,
                local_path,
                callback=callback_wrapper
            )

            logger.info(f"파일 다운로드 완료: {local_path} ({file_size} bytes)")
            return True

        except FileNotFoundError:
            logger.error(f"원격 파일을 찾을 수 없습니다: {remote_path}")
            raise

        except Exception as e:
            logger.error(f"파일 다운로드 실패: {e}")
            raise

    def delete_file(self, remote_path: str) -> bool:
        """
        원격 파일 삭제

        Args:
            remote_path: 삭제할 원격 파일 경로

        Returns:
            삭제 성공 여부

        Raises:
            SSHConnectionError: 연결되지 않은 경우
        """
        if not self.is_connected():
            raise SSHConnectionError("SSH에 연결되지 않았습니다.")

        try:
            logger.info(f"파일 삭제: {remote_path}")
            self._sftp_client.remove(remote_path)
            logger.info(f"파일 삭제 완료: {remote_path}")
            return True

        except FileNotFoundError:
            logger.error(f"파일을 찾을 수 없습니다: {remote_path}")
            raise

        except Exception as e:
            logger.error(f"파일 삭제 실패: {e}")
            raise

    def get_file_stat(self, remote_path: str) -> FileInfo:
        """
        원격 파일 정보 조회

        Args:
            remote_path: 원격 파일 경로

        Returns:
            파일 정보

        Raises:
            SSHConnectionError: 연결되지 않은 경우
        """
        if not self.is_connected():
            raise SSHConnectionError("SSH에 연결되지 않았습니다.")

        try:
            stat = self._sftp_client.stat(remote_path)
            filename = os.path.basename(remote_path)
            dirpath = os.path.dirname(remote_path)

            return FileInfo(
                name=filename,
                path=dirpath,
                size=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                is_remote=True
            )

        except Exception as e:
            logger.error(f"파일 정보 조회 실패: {e}")
            raise

    def is_directory(self, remote_path: str) -> bool:
        """
        원격 경로가 디렉토리인지 확인

        Args:
            remote_path: 원격 경로

        Returns:
            디렉토리 여부

        Raises:
            SSHConnectionError: 연결되지 않은 경우
        """
        if not self.is_connected():
            raise SSHConnectionError("SSH에 연결되지 않았습니다.")

        try:
            stat = self._sftp_client.stat(remote_path)
            import stat as stat_module
            return stat_module.S_ISDIR(stat.st_mode)

        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"디렉토리 확인 실패: {e}")
            return False

    def execute_command(self, command: str, timeout: int = 30) -> tuple[str, str, int]:
        """
        SSH 명령 실행

        Args:
            command: 실행할 명령
            timeout: 타임아웃 (초)

        Returns:
            (stdout, stderr, exit_code) 튜플

        Raises:
            SSHConnectionError: 연결되지 않은 경우
        """
        if not self.is_connected():
            raise SSHConnectionError("SSH에 연결되지 않았습니다.")

        try:
            logger.debug(f"명령 실행: {command}")

            stdin, stdout, stderr = self._ssh_client.exec_command(
                command,
                timeout=timeout
            )

            # 출력 읽기
            stdout_str = stdout.read().decode('utf-8')
            stderr_str = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()

            logger.debug(f"명령 실행 완료: exit_code={exit_code}")

            return stdout_str, stderr_str, exit_code

        except Exception as e:
            logger.error(f"명령 실행 실패: {e}")
            raise

    def __enter__(self):
        """컨텍스트 매니저 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.disconnect()

    def __del__(self):
        """소멸자"""
        try:
            self.disconnect()
        except:
            pass
