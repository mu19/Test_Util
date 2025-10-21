"""
File Collector for Log Collector

파일 수집을 조정하는 핵심 모듈 (Controller)
모든 서비스와 핸들러를 통합하여 로그 수집 워크플로우를 관리
"""

import os
from typing import List, Optional, Callable
from pathlib import Path

from core.models import (
    LogSourceConfig,
    FileInfo,
    CollectionResult,
    CancelToken,
    ProgressInfo
)
from core.filter_engine import FilterEngine
from core.compression_handler import CompressionHandler
from core.ssh_manager import SSHManager
from services.local_service import LocalFileService
from services.remote_service import RemoteFileService
from utils.logger import get_logger

logger = get_logger("FileCollector")


class FileCollector:
    """
    파일 수집 조정자

    로그 파일 수집의 전체 워크플로우를 관리:
    1. 파일 목록 조회
    2. 필터 적용
    3. 다운로드/복사
    4. 압축 (옵션)
    5. 원본 삭제 (옵션)
    """

    def __init__(self, ssh_manager: Optional[SSHManager] = None):
        """
        초기화

        Args:
            ssh_manager: SSH 관리자 인스턴스 (원격 파일 수집용, 선택사항)
        """
        self.ssh_manager = ssh_manager
        self.local_service = LocalFileService()
        self.remote_service = RemoteFileService(ssh_manager) if ssh_manager else None
        self.filter_engine = FilterEngine()
        self.compression_handler = CompressionHandler()

        logger.debug("FileCollector 초기화")

    def get_file_list(self, config: LogSourceConfig) -> List[FileInfo]:
        """
        로그 소스의 파일 목록 조회

        Args:
            config: 로그 소스 설정

        Returns:
            파일 정보 리스트
        """
        logger.info(f"파일 목록 조회 시작: {config.get_display_name()}")

        try:
            # 원격 또는 로컬에서 파일 목록 조회
            if config.is_remote():
                if not self.remote_service:
                    raise ValueError("SSH 관리자가 설정되지 않았습니다.")
                files = self.remote_service.list_files(config.path)
            else:
                files = self.local_service.list_files(config.path)

            logger.info(f"파일 목록 조회 완료: {len(files)}개")

            # 필터 적용
            filtered_files = self.filter_engine.apply_filter(files, config)
            logger.info(f"필터 적용 후: {len(filtered_files)}개")

            return filtered_files

        except Exception as e:
            logger.error(f"파일 목록 조회 실패: {e}")
            raise

    def collect_logs(self,
                    config: LogSourceConfig,
                    save_path: str,
                    progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
                    cancel_token: Optional[CancelToken] = None) -> CollectionResult:
        """
        로그 파일 수집

        Args:
            config: 로그 소스 설정
            save_path: 저장 경로
            progress_callback: 진행률 콜백 함수
            cancel_token: 취소 토큰

        Returns:
            수집 결과
        """
        logger.info(f"로그 수집 시작: {config.get_display_name()}")
        logger.info(f"저장 경로: {save_path}")

        result = CollectionResult(success=False)

        try:
            # 파일 목록 조회 및 필터링
            files = self.get_file_list(config)

            if not files:
                logger.warning("수집할 파일이 없습니다.")
                result.success = True
                return result

            result.total_files = len(files)
            result.total_size = sum(f.size for f in files)

            logger.info(f"수집 대상: {result.total_files}개 파일, {FilterEngine.get_size_str(result.total_size)}")

            # 저장 디렉토리 생성
            self.local_service.create_directory(save_path)

            # 파일 수집
            collected_files = []

            for idx, file_info in enumerate(files, 1):
                # 취소 확인
                if cancel_token and cancel_token.is_cancelled():
                    logger.warning("사용자에 의해 취소되었습니다.")
                    result.error_message = "사용자 취소"
                    return result

                # 진행률 업데이트
                if progress_callback:
                    progress = ProgressInfo(
                        current_file=file_info.name,
                        current_index=idx,
                        total_files=result.total_files,
                        total_progress=int((idx / result.total_files) * 100)
                    )
                    progress_callback(progress)

                try:
                    # 파일 수집 (다운로드 또는 복사)
                    local_path = os.path.join(save_path, file_info.name)

                    if config.is_remote():
                        self.remote_service.download_file(
                            file_info.get_full_path(),
                            local_path
                        )
                    else:
                        self.local_service.copy_file(
                            file_info.get_full_path(),
                            local_path
                        )

                    collected_files.append((file_info, local_path))
                    result.collected_files += 1
                    result.file_list.append(local_path)

                    logger.info(f"[{idx}/{result.total_files}] 수집 완료: {file_info.name}")

                except Exception as e:
                    logger.error(f"파일 수집 실패: {file_info.name} - {e}")
                    result.failed_files += 1

            # 압축 처리
            if config.compress and collected_files:
                logger.info("압축 시작...")
                archive_name = self.compression_handler.create_archive_name(
                    config.source_type.value,
                    timestamp=True
                )
                archive_path = os.path.join(save_path, archive_name)

                try:
                    file_paths = [local_path for _, local_path in collected_files]
                    self.compression_handler.compress_files(
                        file_paths,
                        archive_path
                    )

                    logger.info(f"압축 완료: {archive_name}")

                    # 압축 후 원본 파일 삭제
                    for _, local_path in collected_files:
                        try:
                            os.remove(local_path)
                        except Exception as e:
                            logger.warning(f"압축 후 원본 삭제 실패: {local_path} - {e}")

                    # 압축 파일을 결과에 추가
                    result.file_list = [archive_path]

                except Exception as e:
                    logger.error(f"압축 실패: {e}")
                    result.error_message = f"압축 실패: {str(e)}"

            # 원본 파일 삭제 (원격 또는 로컬)
            if config.delete_after and collected_files:
                logger.info("원본 파일 삭제 시작...")

                delete_success = 0
                delete_fail = 0

                for file_info, _ in collected_files:
                    try:
                        if config.is_remote():
                            self.remote_service.delete_file(file_info.get_full_path())
                        else:
                            self.local_service.delete_file(file_info.get_full_path())

                        delete_success += 1

                    except Exception as e:
                        logger.warning(f"원본 파일 삭제 실패: {file_info.name} - {e}")
                        delete_fail += 1

                logger.info(f"원본 파일 삭제 완료: 성공 {delete_success}개, 실패 {delete_fail}개")

            # 최종 진행률
            if progress_callback:
                progress = ProgressInfo(
                    current_file="",
                    current_index=result.total_files,
                    total_files=result.total_files,
                    total_progress=100,
                    is_complete=True
                )
                progress_callback(progress)

            result.success = True
            logger.info(f"로그 수집 완료: {result.get_summary()}")

            return result

        except Exception as e:
            logger.error(f"로그 수집 실패: {e}")
            result.error_message = str(e)
            return result

    def collect_selected_files(self,
                              files: List[FileInfo],
                              save_path: str,
                              progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
                              cancel_token: Optional[CancelToken] = None) -> CollectionResult:
        """
        선택한 파일들만 수집

        Args:
            files: 수집할 파일 목록
            save_path: 저장 경로
            progress_callback: 진행률 콜백
            cancel_token: 취소 토큰

        Returns:
            수집 결과
        """
        logger.info(f"선택 파일 수집 시작: {len(files)}개")

        result = CollectionResult(
            success=False,
            total_files=len(files),
            total_size=sum(f.size for f in files)
        )

        try:
            # 저장 디렉토리 생성
            self.local_service.create_directory(save_path)

            for idx, file_info in enumerate(files, 1):
                # 취소 확인
                if cancel_token and cancel_token.is_cancelled():
                    logger.warning("사용자에 의해 취소되었습니다.")
                    result.error_message = "사용자 취소"
                    return result

                # 진행률 업데이트
                if progress_callback:
                    progress = ProgressInfo(
                        current_file=file_info.name,
                        current_index=idx,
                        total_files=result.total_files,
                        total_progress=int((idx / result.total_files) * 100)
                    )
                    progress_callback(progress)

                try:
                    local_path = os.path.join(save_path, file_info.name)

                    if file_info.is_remote:
                        if not self.remote_service:
                            raise ValueError("SSH 관리자가 설정되지 않았습니다.")
                        self.remote_service.download_file(
                            file_info.get_full_path(),
                            local_path
                        )
                    else:
                        self.local_service.copy_file(
                            file_info.get_full_path(),
                            local_path
                        )

                    result.collected_files += 1
                    result.file_list.append(local_path)

                    logger.info(f"[{idx}/{result.total_files}] 수집 완료: {file_info.name}")

                except Exception as e:
                    logger.error(f"파일 수집 실패: {file_info.name} - {e}")
                    result.failed_files += 1

            # 최종 진행률
            if progress_callback:
                progress = ProgressInfo(
                    is_complete=True,
                    total_progress=100
                )
                progress_callback(progress)

            result.success = True
            logger.info(f"선택 파일 수집 완료: {result.get_summary()}")

            return result

        except Exception as e:
            logger.error(f"선택 파일 수집 실패: {e}")
            result.error_message = str(e)
            return result

    def delete_files(self, files: List[FileInfo]) -> tuple[int, int]:
        """
        파일 삭제

        Args:
            files: 삭제할 파일 목록

        Returns:
            (성공 수, 실패 수) 튜플
        """
        logger.info(f"파일 삭제 시작: {len(files)}개")

        success_count = 0
        fail_count = 0

        for file_info in files:
            try:
                if file_info.is_remote:
                    if not self.remote_service:
                        raise ValueError("SSH 관리자가 설정되지 않았습니다.")
                    self.remote_service.delete_file(file_info.get_full_path())
                else:
                    self.local_service.delete_file(file_info.get_full_path())

                success_count += 1
                logger.info(f"파일 삭제 완료: {file_info.name}")

            except Exception as e:
                logger.error(f"파일 삭제 실패: {file_info.name} - {e}")
                fail_count += 1

        logger.info(f"파일 삭제 완료: 성공 {success_count}개, 실패 {fail_count}개")
        return success_count, fail_count
