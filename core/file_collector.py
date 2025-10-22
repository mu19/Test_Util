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

            # 원격 파일의 경우 먼저 압축한 후 다운로드
            if config.is_remote() and len(files) > 0:
                result = self._collect_remote_with_compression(
                    files, config, save_path, progress_callback, cancel_token, result
                )
                return result

            # 로컬 파일 수집 (기존 로직)
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

                    # 하위 디렉토리 생성 (file_info.name에 경로가 포함된 경우)
                    local_dir = os.path.dirname(local_path)
                    if local_dir and not os.path.exists(local_dir):
                        os.makedirs(local_dir, exist_ok=True)

                    if config.is_remote():
                        # 원격 파일 다운로드 (개별 파일)
                        self.remote_service.download_file(
                            file_info.get_full_path(),
                            local_path
                        )
                    else:
                        # 로컬 파일 복사
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
                    # 파일 경로와 압축 파일 내 경로(arcname) 매핑
                    file_paths = []
                    arcnames = []
                    for file_info, local_path in collected_files:
                        file_paths.append(local_path)
                        # file_info.name에는 이미 하위 폴더 경로가 포함되어 있음
                        arcnames.append(file_info.name)

                    self.compression_handler.compress_files_with_structure(
                        file_paths,
                        arcnames,
                        archive_path
                    )

                    logger.info(f"압축 완료: {archive_name}")

                    # 압축 후 원본 파일 삭제 (폴더 구조도 함께 정리)
                    for _, local_path in collected_files:
                        try:
                            os.remove(local_path)
                            # 빈 디렉토리 정리 시도
                            parent_dir = os.path.dirname(local_path)
                            while parent_dir != save_path and os.path.exists(parent_dir):
                                try:
                                    if not os.listdir(parent_dir):  # 빈 디렉토리인 경우
                                        os.rmdir(parent_dir)
                                        parent_dir = os.path.dirname(parent_dir)
                                    else:
                                        break
                                except:
                                    break
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

    def _collect_remote_with_compression(self,
                                        files: List[FileInfo],
                                        config: LogSourceConfig,
                                        save_path: str,
                                        progress_callback: Optional[Callable[[ProgressInfo], None]],
                                        cancel_token: Optional[CancelToken],
                                        result: CollectionResult) -> CollectionResult:
        """
        원격 파일 수집 (원격 압축 → 다운로드 → 원격 삭제)

        Args:
            files: 수집할 파일 목록
            config: 로그 소스 설정
            save_path: 로컬 저장 경로
            progress_callback: 진행률 콜백
            cancel_token: 취소 토큰
            result: 수집 결과 (진행중)

        Returns:
            최종 수집 결과
        """
        from datetime import datetime

        try:
            # 진행률 업데이트
            if progress_callback:
                progress = ProgressInfo(
                    current_file="원격 서버에서 파일 압축 중...",
                    current_index=0,
                    total_files=result.total_files,
                    total_progress=10
                )
                progress_callback(progress)

            # 압축 파일명 생성
            archive_name = self.compression_handler.create_archive_name(
                config.source_type.value,
                timestamp=True
            )

            # 원격 압축 파일 경로 (원격 서버의 /tmp 디렉토리 사용)
            remote_archive_path = f"/tmp/{archive_name}"

            # 원격에서 파일 압축
            logger.info(f"원격 서버에서 파일 압축 시작: {len(files)}개 파일")

            # 파일 경로 리스트 생성
            file_paths = [f.get_full_path() for f in files]

            # 압축 타입 결정 (Linux 커널: gz, 서버 앱: tar.gz)
            from core.models import LogSourceType
            if config.source_type == LogSourceType.LINUX_KERNEL:
                archive_type = "tar.gz"  # 커널 로그도 여러 파일일 수 있으므로 tar.gz 사용
            else:
                archive_type = "tar.gz"

            # 원격 압축 실행
            compress_success = self.remote_service.compress_files_remote(
                file_paths,
                remote_archive_path,
                archive_type
            )

            if not compress_success:
                raise Exception("원격 파일 압축 실패")

            logger.info(f"원격 압축 완료: {remote_archive_path}")

            # 진행률 업데이트
            if progress_callback:
                progress = ProgressInfo(
                    current_file="압축 파일 다운로드 중...",
                    current_index=0,
                    total_files=result.total_files,
                    total_progress=50
                )
                progress_callback(progress)

            # 압축 파일 다운로드
            local_archive_path = os.path.join(save_path, archive_name)
            logger.info(f"압축 파일 다운로드: {remote_archive_path} -> {local_archive_path}")

            self.remote_service.download_file(
                remote_archive_path,
                local_archive_path
            )

            logger.info("압축 파일 다운로드 완료")

            # 진행률 업데이트
            if progress_callback:
                progress = ProgressInfo(
                    current_file="원격 압축 파일 삭제 중...",
                    current_index=0,
                    total_files=result.total_files,
                    total_progress=80
                )
                progress_callback(progress)

            # 원격 압축 파일 삭제
            logger.info("원격 압축 파일 삭제 시작")
            try:
                self.remote_service.delete_file(remote_archive_path)
                logger.info("원격 압축 파일 삭제 완료")
            except Exception as e:
                logger.warning(f"원격 압축 파일 삭제 실패: {e}")

            # 원본 파일 삭제 (옵션)
            if config.delete_after:
                logger.info("원격 원본 파일 삭제 시작...")

                delete_success = 0
                delete_fail = 0

                for file_info in files:
                    try:
                        self.remote_service.delete_file(file_info.get_full_path())
                        delete_success += 1
                    except Exception as e:
                        logger.warning(f"원본 파일 삭제 실패: {file_info.name} - {e}")
                        delete_fail += 1

                logger.info(f"원본 파일 삭제 완료: 성공 {delete_success}개, 실패 {delete_fail}개")

            # 결과 업데이트
            result.collected_files = len(files)
            result.file_list = [local_archive_path]
            result.success = True

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

            logger.info(f"원격 파일 수집 완료: {result.get_summary()}")
            return result

        except Exception as e:
            logger.error(f"원격 파일 수집 중 오류: {e}")
            result.error_message = str(e)
            result.success = False
            return result
