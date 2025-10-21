"""
Remote File Service for Log Collector

SSH/SFTP를 통한 원격 파일 작업을 담당하는 모듈
"""

from typing import List, Optional, Callable

from core.models import FileInfo
from core.ssh_manager import SSHManager, SSHConnectionError
from utils.logger import get_logger

logger = get_logger("RemoteService")


class RemoteFileService:
    """원격 파일 시스템 서비스 (SSH/SFTP 기반)"""

    def __init__(self, ssh_manager: SSHManager):
        """
        초기화

        Args:
            ssh_manager: SSH 관리자 인스턴스
        """
        self.ssh_manager = ssh_manager
        logger.debug("RemoteFileService 초기화")

    def list_files(self, remote_path: str) -> List[FileInfo]:
        """
        원격 디렉토리의 파일 목록 조회

        Args:
            remote_path: 원격 디렉토리 경로

        Returns:
            파일 정보 리스트

        Raises:
            SSHConnectionError: SSH 연결되지 않음
            Exception: 파일 목록 조회 실패
        """
        logger.info(f"원격 파일 목록 조회: {remote_path}")

        if not self.ssh_manager.is_connected():
            raise SSHConnectionError("SSH에 연결되지 않았습니다.")

        try:
            files = self.ssh_manager.list_files(remote_path)
            logger.info(f"원격 파일 목록 조회 완료: {len(files)}개")
            return files

        except Exception as e:
            logger.error(f"원격 파일 목록 조회 실패: {e}")
            raise

    def download_file(self,
                     remote_path: str,
                     local_path: str,
                     progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        원격 파일 다운로드

        Args:
            remote_path: 원격 파일 경로
            local_path: 로컬 저장 경로
            progress_callback: 진행률 콜백 함수

        Returns:
            다운로드 성공 여부

        Raises:
            SSHConnectionError: SSH 연결되지 않음
        """
        logger.info(f"원격 파일 다운로드: {remote_path} -> {local_path}")

        if not self.ssh_manager.is_connected():
            raise SSHConnectionError("SSH에 연결되지 않았습니다.")

        try:
            result = self.ssh_manager.download_file(
                remote_path,
                local_path,
                progress_callback
            )
            logger.info(f"원격 파일 다운로드 완료: {local_path}")
            return result

        except Exception as e:
            logger.error(f"원격 파일 다운로드 실패: {e}")
            raise

    def delete_file(self, remote_path: str) -> bool:
        """
        원격 파일 삭제

        Args:
            remote_path: 삭제할 원격 파일 경로

        Returns:
            삭제 성공 여부

        Raises:
            SSHConnectionError: SSH 연결되지 않음
        """
        logger.info(f"원격 파일 삭제: {remote_path}")

        if not self.ssh_manager.is_connected():
            raise SSHConnectionError("SSH에 연결되지 않았습니다.")

        try:
            result = self.ssh_manager.delete_file(remote_path)
            logger.info(f"원격 파일 삭제 완료: {remote_path}")
            return result

        except Exception as e:
            logger.error(f"원격 파일 삭제 실패: {e}")
            raise

    def get_file_info(self, remote_path: str) -> FileInfo:
        """
        원격 파일 정보 조회

        Args:
            remote_path: 원격 파일 경로

        Returns:
            파일 정보

        Raises:
            SSHConnectionError: SSH 연결되지 않음
        """
        logger.debug(f"원격 파일 정보 조회: {remote_path}")

        if not self.ssh_manager.is_connected():
            raise SSHConnectionError("SSH에 연결되지 않았습니다.")

        try:
            file_info = self.ssh_manager.get_file_stat(remote_path)
            return file_info

        except Exception as e:
            logger.error(f"원격 파일 정보 조회 실패: {e}")
            raise

    def execute_command(self, command: str, timeout: int = 30) -> tuple[str, str, int]:
        """
        원격 명령 실행

        Args:
            command: 실행할 명령
            timeout: 타임아웃 (초)

        Returns:
            (stdout, stderr, exit_code) 튜플

        Raises:
            SSHConnectionError: SSH 연결되지 않음
        """
        logger.info(f"원격 명령 실행: {command}")

        if not self.ssh_manager.is_connected():
            raise SSHConnectionError("SSH에 연결되지 않았습니다.")

        try:
            stdout, stderr, exit_code = self.ssh_manager.execute_command(command, timeout)
            logger.debug(f"원격 명령 실행 완료: exit_code={exit_code}")
            return stdout, stderr, exit_code

        except Exception as e:
            logger.error(f"원격 명령 실행 실패: {e}")
            raise

    def check_directory_exists(self, remote_path: str) -> bool:
        """
        원격 디렉토리 존재 여부 확인

        Args:
            remote_path: 원격 디렉토리 경로

        Returns:
            존재 여부
        """
        logger.debug(f"원격 디렉토리 확인: {remote_path}")

        try:
            # test 명령으로 디렉토리 존재 확인
            command = f'test -d "{remote_path}" && echo "exists"'
            stdout, stderr, exit_code = self.execute_command(command)

            exists = exit_code == 0 and "exists" in stdout
            logger.debug(f"원격 디렉토리 존재 여부: {exists}")
            return exists

        except Exception as e:
            logger.warning(f"원격 디렉토리 확인 실패: {e}")
            return False

    def check_file_exists(self, remote_path: str) -> bool:
        """
        원격 파일 존재 여부 확인

        Args:
            remote_path: 원격 파일 경로

        Returns:
            존재 여부
        """
        logger.debug(f"원격 파일 확인: {remote_path}")

        try:
            # test 명령으로 파일 존재 확인
            command = f'test -f "{remote_path}" && echo "exists"'
            stdout, stderr, exit_code = self.execute_command(command)

            exists = exit_code == 0 and "exists" in stdout
            logger.debug(f"원격 파일 존재 여부: {exists}")
            return exists

        except Exception as e:
            logger.warning(f"원격 파일 확인 실패: {e}")
            return False

    def get_available_space(self, remote_path: str) -> int:
        """
        원격 디스크 여유 공간 확인

        Args:
            remote_path: 확인할 경로

        Returns:
            사용 가능한 공간 (bytes), 실패시 0
        """
        logger.debug(f"원격 디스크 공간 확인: {remote_path}")

        try:
            # df 명령으로 디스크 공간 확인
            command = f'df -B1 "{remote_path}" | tail -1 | awk \'{{print $4}}\''
            stdout, stderr, exit_code = self.execute_command(command)

            if exit_code == 0 and stdout.strip().isdigit():
                available = int(stdout.strip())
                logger.debug(f"원격 디스크 여유 공간: {available} bytes")
                return available

            return 0

        except Exception as e:
            logger.warning(f"원격 디스크 공간 확인 실패: {e}")
            return 0

    def batch_delete_files(self, file_paths: List[str]) -> tuple[int, int]:
        """
        여러 원격 파일 일괄 삭제

        Args:
            file_paths: 삭제할 파일 경로 리스트

        Returns:
            (성공 수, 실패 수) 튜플
        """
        logger.info(f"원격 파일 일괄 삭제 시작: {len(file_paths)}개")

        success_count = 0
        fail_count = 0

        for file_path in file_paths:
            try:
                self.delete_file(file_path)
                success_count += 1
            except Exception as e:
                logger.warning(f"파일 삭제 실패: {file_path} - {e}")
                fail_count += 1

        logger.info(f"원격 파일 일괄 삭제 완료: 성공 {success_count}개, 실패 {fail_count}개")
        return success_count, fail_count

    def batch_download_files(self,
                            files: List[FileInfo],
                            local_base_path: str,
                            progress_callback: Optional[Callable[[int, int, str], None]] = None) -> tuple[int, int]:
        """
        여러 원격 파일 일괄 다운로드

        Args:
            files: 다운로드할 파일 목록
            local_base_path: 로컬 기본 저장 경로
            progress_callback: 진행률 콜백 (현재 파일 인덱스, 전체 파일 수, 파일명)

        Returns:
            (성공 수, 실패 수) 튜플
        """
        import os
        from pathlib import Path

        logger.info(f"원격 파일 일괄 다운로드 시작: {len(files)}개")

        success_count = 0
        fail_count = 0

        for idx, file_info in enumerate(files, 1):
            try:
                # 진행률 콜백
                if progress_callback:
                    progress_callback(idx, len(files), file_info.name)

                # 로컬 저장 경로
                local_path = os.path.join(local_base_path, file_info.name)

                # 다운로드
                self.download_file(file_info.get_full_path(), local_path)
                success_count += 1

            except Exception as e:
                logger.warning(f"파일 다운로드 실패: {file_info.name} - {e}")
                fail_count += 1

        logger.info(f"원격 파일 일괄 다운로드 완료: 성공 {success_count}개, 실패 {fail_count}개")
        return success_count, fail_count
