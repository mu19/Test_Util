"""
Local File Service for Log Collector

Windows 로컬 파일 시스템 작업을 담당하는 모듈
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime

from core.models import FileInfo
from utils.logger import get_logger

logger = get_logger("LocalService")


class LocalFileService:
    """로컬 파일 시스템 서비스"""

    @staticmethod
    def list_files(local_path: str, recursive: bool = True) -> List[FileInfo]:
        """
        로컬 디렉토리의 파일 목록 조회 (재귀적)

        Args:
            local_path: 로컬 디렉토리 경로
            recursive: 하위 디렉토리 포함 여부 (기본값: True)

        Returns:
            파일 정보 리스트

        Raises:
            FileNotFoundError: 경로가 존재하지 않음
            NotADirectoryError: 경로가 디렉토리가 아님
        """
        logger.info(f"파일 목록 조회: {local_path} (재귀: {recursive})")

        # 경로 확인
        path_obj = Path(local_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"경로를 찾을 수 없습니다: {local_path}")

        if not path_obj.is_dir():
            raise NotADirectoryError(f"디렉토리가 아닙니다: {local_path}")

        # 파일 목록 조회
        file_list = []
        try:
            if recursive:
                # 재귀적으로 하위 디렉토리 포함
                for item in path_obj.rglob('*'):
                    # 디렉토리는 제외, 파일만 포함
                    if item.is_dir():
                        continue

                    try:
                        # 파일 정보 가져오기
                        stat = item.stat()

                        # 상대 경로 계산 (루트 경로 기준)
                        relative_path = item.relative_to(path_obj)

                        file_info = FileInfo(
                            name=str(relative_path),  # 하위 폴더 포함한 상대 경로
                            path=str(path_obj),
                            size=stat.st_size,
                            modified_time=datetime.fromtimestamp(stat.st_mtime),
                            is_remote=False
                        )
                        file_list.append(file_info)

                    except PermissionError:
                        # 권한 없는 파일은 경고 후 스킵
                        logger.warning(f"권한 없음 (스킵): {item}")
                        continue
                    except Exception as e:
                        # 기타 오류도 경고 후 스킵
                        logger.warning(f"파일 정보 조회 실패 (스킵): {item} - {e}")
                        continue
            else:
                # 현재 디렉토리만 조회 (하위 디렉토리 제외)
                for item in path_obj.iterdir():
                    # 디렉토리는 제외
                    if item.is_dir():
                        continue

                    # 파일 정보 가져오기
                    stat = item.stat()

                    file_info = FileInfo(
                        name=item.name,
                        path=str(path_obj),
                        size=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime),
                        is_remote=False
                    )
                    file_list.append(file_info)

            logger.info(f"파일 목록 조회 완료: {len(file_list)}개")
            return file_list

        except PermissionError as e:
            logger.error(f"권한 오류: {e}")
            raise PermissionError(f"디렉토리 접근 권한이 없습니다: {local_path}")

        except Exception as e:
            logger.error(f"파일 목록 조회 실패: {e}")
            raise

    @staticmethod
    def copy_file(source_path: str,
                 dest_path: str,
                 progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        로컬 파일 복사

        Args:
            source_path: 원본 파일 경로
            dest_path: 대상 파일 경로
            progress_callback: 진행률 콜백 함수 (전송된 바이트, 전체 바이트)

        Returns:
            복사 성공 여부

        Raises:
            FileNotFoundError: 원본 파일이 존재하지 않음
        """
        logger.info(f"파일 복사: {source_path} -> {dest_path}")

        # 원본 파일 확인
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"원본 파일을 찾을 수 없습니다: {source_path}")

        if not source.is_file():
            raise ValueError(f"파일이 아닙니다: {source_path}")

        # 대상 디렉토리 생성
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            file_size = source.stat().st_size

            # 진행률 콜백이 있으면 청크 단위로 복사
            if progress_callback:
                LocalFileService._copy_with_progress(
                    source_path,
                    dest_path,
                    file_size,
                    progress_callback
                )
            else:
                # 일반 복사
                shutil.copy2(source_path, dest_path)

            logger.info(f"파일 복사 완료: {dest_path} ({file_size} bytes)")
            return True

        except Exception as e:
            logger.error(f"파일 복사 실패: {e}")
            raise

    @staticmethod
    def _copy_with_progress(source_path: str,
                          dest_path: str,
                          total_size: int,
                          progress_callback: Callable[[int, int], None],
                          buffer_size: int = 1024 * 1024):  # 1MB 버퍼
        """
        진행률을 추적하며 파일 복사

        Args:
            source_path: 원본 파일 경로
            dest_path: 대상 파일 경로
            total_size: 전체 파일 크기
            progress_callback: 진행률 콜백
            buffer_size: 버퍼 크기 (기본 1MB)
        """
        transferred = 0

        with open(source_path, 'rb') as src:
            with open(dest_path, 'wb') as dst:
                while True:
                    chunk = src.read(buffer_size)
                    if not chunk:
                        break

                    dst.write(chunk)
                    transferred += len(chunk)

                    # 진행률 콜백 호출
                    if progress_callback:
                        progress_callback(transferred, total_size)

        # 메타데이터 복사 (수정 시간 등)
        shutil.copystat(source_path, dest_path)

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        로컬 파일 삭제

        Args:
            file_path: 삭제할 파일 경로

        Returns:
            삭제 성공 여부

        Raises:
            FileNotFoundError: 파일이 존재하지 않음
        """
        logger.info(f"파일 삭제: {file_path}")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        if not path.is_file():
            raise ValueError(f"파일이 아닙니다: {file_path}")

        try:
            path.unlink()
            logger.info(f"파일 삭제 완료: {file_path}")
            return True

        except Exception as e:
            logger.error(f"파일 삭제 실패: {e}")
            raise

    @staticmethod
    def get_file_info(file_path: str) -> FileInfo:
        """
        로컬 파일 정보 조회

        Args:
            file_path: 파일 경로

        Returns:
            파일 정보

        Raises:
            FileNotFoundError: 파일이 존재하지 않음
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        if not path.is_file():
            raise ValueError(f"파일이 아닙니다: {file_path}")

        stat = path.stat()

        return FileInfo(
            name=path.name,
            path=str(path.parent),
            size=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
            is_remote=False
        )

    @staticmethod
    def create_directory(dir_path: str) -> bool:
        """
        디렉토리 생성 (중간 경로 포함)

        Args:
            dir_path: 생성할 디렉토리 경로

        Returns:
            생성 성공 여부
        """
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"디렉토리 생성 완료: {dir_path}")
            return True

        except Exception as e:
            logger.error(f"디렉토리 생성 실패: {e}")
            raise

    @staticmethod
    def directory_exists(dir_path: str) -> bool:
        """
        디렉토리 존재 여부 확인

        Args:
            dir_path: 디렉토리 경로

        Returns:
            존재 여부
        """
        path = Path(dir_path)
        return path.exists() and path.is_dir()

    @staticmethod
    def file_exists(file_path: str) -> bool:
        """
        파일 존재 여부 확인

        Args:
            file_path: 파일 경로

        Returns:
            존재 여부
        """
        path = Path(file_path)
        return path.exists() and path.is_file()

    @staticmethod
    def get_available_space(path: str) -> int:
        """
        사용 가능한 디스크 공간 확인

        Args:
            path: 확인할 경로

        Returns:
            사용 가능한 공간 (bytes)
        """
        try:
            import shutil
            stat = shutil.disk_usage(path)
            logger.debug(f"디스크 여유 공간: {stat.free} bytes")
            return stat.free

        except Exception as e:
            logger.error(f"디스크 공간 확인 실패: {e}")
            return 0

    @staticmethod
    def move_file(source_path: str, dest_path: str) -> bool:
        """
        파일 이동

        Args:
            source_path: 원본 파일 경로
            dest_path: 대상 파일 경로

        Returns:
            이동 성공 여부
        """
        logger.info(f"파일 이동: {source_path} -> {dest_path}")

        # 원본 확인
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"원본 파일을 찾을 수 없습니다: {source_path}")

        # 대상 디렉토리 생성
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(source_path, dest_path)
            logger.info(f"파일 이동 완료: {dest_path}")
            return True

        except Exception as e:
            logger.error(f"파일 이동 실패: {e}")
            raise

    @staticmethod
    def get_temp_directory() -> str:
        """
        임시 디렉토리 경로 반환

        Returns:
            임시 디렉토리 경로
        """
        import tempfile
        temp_dir = tempfile.gettempdir()
        logger.debug(f"임시 디렉토리: {temp_dir}")
        return temp_dir
