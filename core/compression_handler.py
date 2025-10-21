"""
Compression Handler for Log Collector

파일 압축/압축 해제를 담당하는 모듈
"""

import zipfile
import os
from pathlib import Path
from typing import List, Optional

from utils.logger import get_logger

logger = get_logger("CompressionHandler")


class CompressionHandler:
    """파일 압축 핸들러"""

    @staticmethod
    def compress_file(source_path: str,
                     archive_path: str,
                     compression_level: int = 6) -> bool:
        """
        단일 파일 압축

        Args:
            source_path: 압축할 파일 경로
            archive_path: 압축 파일 저장 경로 (.zip)
            compression_level: 압축 레벨 (0-9, 기본 6)

        Returns:
            압축 성공 여부

        Raises:
            FileNotFoundError: 원본 파일이 존재하지 않음
        """
        logger.info(f"파일 압축: {source_path} -> {archive_path}")

        # 원본 파일 확인
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {source_path}")

        if not source.is_file():
            raise ValueError(f"파일이 아닙니다: {source_path}")

        # 압축 파일 디렉토리 생성
        archive = Path(archive_path)
        archive.parent.mkdir(parents=True, exist_ok=True)

        try:
            # ZIP 파일 생성
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED,
                               compresslevel=compression_level) as zipf:
                zipf.write(source_path, source.name)

            # 압축 결과 확인
            original_size = source.stat().st_size
            compressed_size = archive.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

            logger.info(f"파일 압축 완료: {archive_path}")
            logger.info(f"압축률: {ratio:.1f}% (원본: {original_size}, 압축: {compressed_size})")

            return True

        except Exception as e:
            logger.error(f"파일 압축 실패: {e}")
            raise

    @staticmethod
    def compress_files(source_paths: List[str],
                      archive_path: str,
                      compression_level: int = 6,
                      preserve_structure: bool = False) -> bool:
        """
        여러 파일을 하나의 압축 파일로 압축

        Args:
            source_paths: 압축할 파일 경로 리스트
            archive_path: 압축 파일 저장 경로 (.zip)
            compression_level: 압축 레벨 (0-9, 기본 6)
            preserve_structure: 디렉토리 구조 유지 여부

        Returns:
            압축 성공 여부
        """
        logger.info(f"파일 일괄 압축: {len(source_paths)}개 -> {archive_path}")

        if not source_paths:
            logger.warning("압축할 파일이 없습니다.")
            return False

        # 압축 파일 디렉토리 생성
        archive = Path(archive_path)
        archive.parent.mkdir(parents=True, exist_ok=True)

        try:
            total_original_size = 0
            compressed_count = 0

            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED,
                               compresslevel=compression_level) as zipf:
                for source_path in source_paths:
                    source = Path(source_path)

                    if not source.exists():
                        logger.warning(f"파일을 찾을 수 없습니다: {source_path}")
                        continue

                    if not source.is_file():
                        logger.warning(f"파일이 아닙니다: {source_path}")
                        continue

                    # 압축 파일 내 경로 결정
                    if preserve_structure:
                        arcname = str(source)
                    else:
                        arcname = source.name

                    zipf.write(source_path, arcname)
                    total_original_size += source.stat().st_size
                    compressed_count += 1

            # 압축 결과
            compressed_size = archive.stat().st_size
            ratio = (1 - compressed_size / total_original_size) * 100 if total_original_size > 0 else 0

            logger.info(f"파일 일괄 압축 완료: {compressed_count}개 파일")
            logger.info(f"압축률: {ratio:.1f}% (원본: {total_original_size}, 압축: {compressed_size})")

            return True

        except Exception as e:
            logger.error(f"파일 일괄 압축 실패: {e}")
            raise

    @staticmethod
    def decompress_file(archive_path: str,
                       extract_path: str) -> List[str]:
        """
        압축 파일 압축 해제

        Args:
            archive_path: 압축 파일 경로
            extract_path: 압축 해제 디렉토리

        Returns:
            압축 해제된 파일 경로 리스트

        Raises:
            FileNotFoundError: 압축 파일이 존재하지 않음
        """
        logger.info(f"파일 압축 해제: {archive_path} -> {extract_path}")

        # 압축 파일 확인
        archive = Path(archive_path)
        if not archive.exists():
            raise FileNotFoundError(f"압축 파일을 찾을 수 없습니다: {archive_path}")

        # 압축 해제 디렉토리 생성
        extract_dir = Path(extract_path)
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            extracted_files = []

            with zipfile.ZipFile(archive_path, 'r') as zipf:
                # 압축 파일 내용 확인
                namelist = zipf.namelist()
                logger.info(f"압축 파일 내 파일 수: {len(namelist)}개")

                # 압축 해제
                zipf.extractall(extract_path)

                # 압축 해제된 파일 경로 생성
                for name in namelist:
                    extracted_file = os.path.join(extract_path, name)
                    extracted_files.append(extracted_file)

            logger.info(f"파일 압축 해제 완료: {len(extracted_files)}개")
            return extracted_files

        except Exception as e:
            logger.error(f"파일 압축 해제 실패: {e}")
            raise

    @staticmethod
    def list_archive_contents(archive_path: str) -> List[dict]:
        """
        압축 파일 내용 목록 조회

        Args:
            archive_path: 압축 파일 경로

        Returns:
            파일 정보 리스트 [{name, size, compressed_size}, ...]

        Raises:
            FileNotFoundError: 압축 파일이 존재하지 않음
        """
        logger.debug(f"압축 파일 내용 조회: {archive_path}")

        # 압축 파일 확인
        archive = Path(archive_path)
        if not archive.exists():
            raise FileNotFoundError(f"압축 파일을 찾을 수 없습니다: {archive_path}")

        try:
            contents = []

            with zipfile.ZipFile(archive_path, 'r') as zipf:
                for info in zipf.infolist():
                    contents.append({
                        'name': info.filename,
                        'size': info.file_size,
                        'compressed_size': info.compress_size,
                        'is_dir': info.is_dir()
                    })

            logger.debug(f"압축 파일 내 항목 수: {len(contents)}개")
            return contents

        except Exception as e:
            logger.error(f"압축 파일 내용 조회 실패: {e}")
            raise

    @staticmethod
    def is_valid_archive(archive_path: str) -> bool:
        """
        유효한 압축 파일인지 확인

        Args:
            archive_path: 압축 파일 경로

        Returns:
            유효 여부
        """
        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                # 압축 파일 무결성 테스트
                bad_file = zipf.testzip()
                return bad_file is None

        except Exception as e:
            logger.debug(f"유효하지 않은 압축 파일: {archive_path} - {e}")
            return False

    @staticmethod
    def get_compression_ratio(archive_path: str) -> float:
        """
        압축률 계산

        Args:
            archive_path: 압축 파일 경로

        Returns:
            압축률 (0.0 ~ 1.0)
        """
        try:
            total_size = 0
            compressed_size = 0

            with zipfile.ZipFile(archive_path, 'r') as zipf:
                for info in zipf.infolist():
                    if not info.is_dir():
                        total_size += info.file_size
                        compressed_size += info.compress_size

            if total_size == 0:
                return 0.0

            ratio = 1.0 - (compressed_size / total_size)
            logger.debug(f"압축률: {ratio:.2%}")
            return ratio

        except Exception as e:
            logger.error(f"압축률 계산 실패: {e}")
            return 0.0

    @staticmethod
    def create_archive_name(log_source_type: str, timestamp: bool = True) -> str:
        """
        압축 파일 이름 생성

        Args:
            log_source_type: 로그 소스 타입 ("linux_kernel", "linux_server", "windows_client")
            timestamp: 타임스탬프 포함 여부

        Returns:
            압축 파일 이름
        """
        from datetime import datetime

        # 로그 타입별 파일명 매핑
        name_map = {
            "linux_kernel": ("controller_kernel_log", ".gz"),
            "linux_server": ("controller_log", ".tar.gz"),
            "windows_client": ("user_app_log", ".zip")
        }

        base_name, extension = name_map.get(log_source_type, ("log", ".zip"))

        if timestamp:
            ts = datetime.now().strftime('%Y-%m-%d %H.%M.%S')
            return f"{base_name}_{{{ts}}}{extension}"
        else:
            return f"{base_name}{extension}"
