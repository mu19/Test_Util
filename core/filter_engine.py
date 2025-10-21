"""
Filter Engine for Log Collector

파일 필터링 로직을 담당하는 모듈
- 전체 파일 선택
- 정규식 패턴 매칭
- 날짜 기반 필터링
"""

import re
from typing import List
from datetime import datetime

from core.models import FileInfo, FilterType, LogSourceConfig
from utils.logger import get_logger

logger = get_logger("FilterEngine")


class FilterEngine:
    """파일 필터링 엔진"""

    @staticmethod
    def filter_all(files: List[FileInfo]) -> List[FileInfo]:
        """
        모든 파일 반환 (필터링 없음)

        Args:
            files: 파일 목록

        Returns:
            동일한 파일 목록
        """
        logger.debug(f"필터: ALL - {len(files)}개 파일")
        return files

    @staticmethod
    def filter_by_regex(files: List[FileInfo], pattern: str) -> List[FileInfo]:
        """
        정규식 패턴으로 파일 필터링

        Args:
            files: 파일 목록
            pattern: 정규식 패턴

        Returns:
            필터링된 파일 목록
        """
        if not pattern:
            logger.warning("정규식 패턴이 비어있습니다. 모든 파일 반환")
            return files

        try:
            regex = re.compile(pattern)
            filtered = [f for f in files if regex.search(f.name)]
            logger.info(f"필터: REGEX '{pattern}' - {len(files)}개 중 {len(filtered)}개 선택")
            return filtered

        except re.error as e:
            logger.error(f"잘못된 정규식 패턴: {pattern} - {e}")
            raise ValueError(f"잘못된 정규식 패턴: {e}")

    @staticmethod
    def filter_by_date(files: List[FileInfo], after_date: datetime) -> List[FileInfo]:
        """
        특정 날짜 이후에 수정된 파일만 필터링

        Args:
            files: 파일 목록
            after_date: 기준 날짜/시간

        Returns:
            필터링된 파일 목록
        """
        if not after_date:
            logger.warning("기준 날짜가 없습니다. 모든 파일 반환")
            return files

        filtered = [f for f in files if f.modified_time >= after_date]
        logger.info(f"필터: DATE after {after_date} - {len(files)}개 중 {len(filtered)}개 선택")
        return filtered

    @staticmethod
    def apply_filter(files: List[FileInfo], config: LogSourceConfig) -> List[FileInfo]:
        """
        설정에 따라 필터 적용

        Args:
            files: 파일 목록
            config: 로그 소스 설정

        Returns:
            필터링된 파일 목록
        """
        if not files:
            logger.info("필터링할 파일이 없습니다.")
            return []

        logger.info(f"필터 적용 시작: {config.filter_type.value}")

        if config.filter_type == FilterType.ALL:
            return FilterEngine.filter_all(files)

        elif config.filter_type == FilterType.REGEX:
            if not config.filter_value:
                logger.warning("정규식 필터가 선택되었지만 패턴이 없습니다.")
                return files
            return FilterEngine.filter_by_regex(files, config.filter_value)

        elif config.filter_type == FilterType.DATE:
            if not config.filter_value:
                logger.warning("날짜 필터가 선택되었지만 날짜가 없습니다.")
                return files

            # 날짜 문자열을 datetime으로 변환
            try:
                # ISO 8601 형식 지원: YYYY-MM-DD 또는 YYYY-MM-DD HH:MM:SS
                if 'T' in config.filter_value or ' ' in config.filter_value:
                    # 시간 포함
                    date_str = config.filter_value.replace('T', ' ')
                    after_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    # 날짜만
                    after_date = datetime.strptime(config.filter_value, '%Y-%m-%d')

                return FilterEngine.filter_by_date(files, after_date)

            except ValueError as e:
                logger.error(f"날짜 형식 오류: {config.filter_value} - {e}")
                logger.info("지원 형식: YYYY-MM-DD 또는 YYYY-MM-DD HH:MM:SS")
                raise ValueError(f"날짜 형식 오류: {e}")

        else:
            logger.warning(f"알 수 없는 필터 타입: {config.filter_type}")
            return files

    @staticmethod
    def sort_files(files: List[FileInfo],
                   by: str = 'name',
                   reverse: bool = False) -> List[FileInfo]:
        """
        파일 목록 정렬

        Args:
            files: 파일 목록
            by: 정렬 기준 ('name', 'size', 'date')
            reverse: 역순 정렬 여부

        Returns:
            정렬된 파일 목록
        """
        if not files:
            return []

        if by == 'name':
            sorted_files = sorted(files, key=lambda f: f.name.lower(), reverse=reverse)
        elif by == 'size':
            sorted_files = sorted(files, key=lambda f: f.size, reverse=reverse)
        elif by == 'date':
            sorted_files = sorted(files, key=lambda f: f.modified_time, reverse=reverse)
        else:
            logger.warning(f"알 수 없는 정렬 기준: {by}, 이름으로 정렬")
            sorted_files = sorted(files, key=lambda f: f.name.lower(), reverse=reverse)

        logger.debug(f"파일 정렬: {by} (역순={reverse})")
        return sorted_files

    @staticmethod
    def get_total_size(files: List[FileInfo]) -> int:
        """
        파일 목록의 총 크기 계산

        Args:
            files: 파일 목록

        Returns:
            총 크기 (bytes)
        """
        total = sum(f.size for f in files)
        logger.debug(f"총 파일 크기: {total} bytes ({len(files)}개 파일)")
        return total

    @staticmethod
    def get_size_str(size_bytes: int) -> str:
        """
        바이트를 사람이 읽기 쉬운 형태로 변환

        Args:
            size_bytes: 바이트 크기

        Returns:
            변환된 문자열 (예: "1.5 MB")
        """
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    @staticmethod
    def filter_by_extension(files: List[FileInfo], extensions: List[str]) -> List[FileInfo]:
        """
        파일 확장자로 필터링

        Args:
            files: 파일 목록
            extensions: 허용할 확장자 목록 (예: ['.log', '.txt'])

        Returns:
            필터링된 파일 목록
        """
        if not extensions:
            return files

        # 확장자를 소문자로 변환
        extensions_lower = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
                           for ext in extensions]

        filtered = [f for f in files
                   if any(f.name.lower().endswith(ext) for ext in extensions_lower)]

        logger.info(f"필터: 확장자 {extensions} - {len(files)}개 중 {len(filtered)}개 선택")
        return filtered

    @staticmethod
    def filter_by_size_range(files: List[FileInfo],
                            min_size: int = 0,
                            max_size: int = None) -> List[FileInfo]:
        """
        파일 크기 범위로 필터링

        Args:
            files: 파일 목록
            min_size: 최소 크기 (bytes)
            max_size: 최대 크기 (bytes), None이면 제한 없음

        Returns:
            필터링된 파일 목록
        """
        filtered = [f for f in files if f.size >= min_size]

        if max_size is not None:
            filtered = [f for f in filtered if f.size <= max_size]

        logger.info(f"필터: 크기 범위 [{min_size}, {max_size}] - {len(files)}개 중 {len(filtered)}개 선택")
        return filtered
