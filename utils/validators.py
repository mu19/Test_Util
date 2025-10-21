"""
Input validation utilities for Log Collector

사용자 입력 및 설정값 검증 유틸리티
"""

import re
import os
from pathlib import Path
from typing import Tuple


def validate_ip_address(ip: str) -> Tuple[bool, str]:
    """
    IP 주소 유효성 검증

    Args:
        ip: 검증할 IP 주소 문자열

    Returns:
        (유효 여부, 에러 메시지)
    """
    if not ip:
        return False, "IP 주소를 입력해주세요."

    # IPv4 패턴
    ipv4_pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
    match = re.match(ipv4_pattern, ip)

    if not match:
        return False, "올바른 IP 주소 형식이 아닙니다. (예: 192.168.1.100)"

    # 각 옥텟이 0-255 범위인지 확인
    octets = [int(octet) for octet in match.groups()]
    if any(octet < 0 or octet > 255 for octet in octets):
        return False, "IP 주소의 각 부분은 0-255 사이여야 합니다."

    return True, ""


def validate_port(port: str) -> Tuple[bool, str]:
    """
    포트 번호 유효성 검증

    Args:
        port: 검증할 포트 번호 문자열

    Returns:
        (유효 여부, 에러 메시지)
    """
    if not port:
        return False, "포트 번호를 입력해주세요."

    try:
        port_num = int(port)
    except ValueError:
        return False, "포트 번호는 숫자여야 합니다."

    if port_num < 1 or port_num > 65535:
        return False, "포트 번호는 1-65535 사이여야 합니다."

    return True, ""


def validate_path(path: str, is_remote: bool = False, must_exist: bool = False) -> Tuple[bool, str]:
    """
    경로 유효성 검증

    Args:
        path: 검증할 경로 문자열
        is_remote: 원격 경로 여부 (True면 존재 여부 검사 안함)
        must_exist: 경로가 존재해야 하는지 여부

    Returns:
        (유효 여부, 에러 메시지)
    """
    if not path:
        return False, "경로를 입력해주세요."

    # 원격 경로는 기본 형식만 확인
    if is_remote:
        # Linux 경로 형식
        if not path.startswith('/'):
            return False, "Linux 경로는 /로 시작해야 합니다."
        return True, ""

    # 로컬 Windows 경로 검증
    # 경로 트래버설 시도 방지
    if '..' in path:
        return False, "경로에 '..'를 사용할 수 없습니다."

    # Windows 드라이브 문자 확인
    if len(path) >= 2 and path[1] == ':':
        drive_letter = path[0].upper()
        if not drive_letter.isalpha():
            return False, "올바른 Windows 드라이브 경로가 아닙니다."
    else:
        return False, "Windows 경로는 드라이브 문자로 시작해야 합니다. (예: C:\\)"

    # 존재 여부 확인
    if must_exist:
        path_obj = Path(path)
        if not path_obj.exists():
            return False, f"경로가 존재하지 않습니다: {path}"

    return True, ""


def validate_regex_pattern(pattern: str) -> Tuple[bool, str]:
    """
    정규식 패턴 유효성 검증

    Args:
        pattern: 검증할 정규식 패턴 문자열

    Returns:
        (유효 여부, 에러 메시지)
    """
    if not pattern:
        return False, "정규식 패턴을 입력해주세요."

    try:
        re.compile(pattern)
        return True, ""
    except re.error as e:
        return False, f"올바르지 않은 정규식 패턴입니다: {str(e)}"


def validate_username(username: str) -> Tuple[bool, str]:
    """
    사용자명 유효성 검증

    Args:
        username: 검증할 사용자명

    Returns:
        (유효 여부, 에러 메시지)
    """
    if not username:
        return False, "사용자명을 입력해주세요."

    # Linux 사용자명 규칙: 영문자, 숫자, 하이픈, 언더스코어
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "사용자명은 영문자, 숫자, 하이픈, 언더스코어만 사용할 수 있습니다."

    if len(username) > 32:
        return False, "사용자명은 32자 이하여야 합니다."

    return True, ""


def validate_timeout(timeout: str) -> Tuple[bool, str]:
    """
    타임아웃 값 유효성 검증

    Args:
        timeout: 검증할 타임아웃 값 (초)

    Returns:
        (유효 여부, 에러 메시지)
    """
    if not timeout:
        return False, "타임아웃 값을 입력해주세요."

    try:
        timeout_val = int(timeout)
    except ValueError:
        return False, "타임아웃 값은 숫자여야 합니다."

    if timeout_val < 10:
        return False, "타임아웃은 최소 10초 이상이어야 합니다."

    if timeout_val > 3600:
        return False, "타임아웃은 최대 3600초(1시간) 이하여야 합니다."

    return True, ""


def sanitize_filename(filename: str) -> str:
    """
    파일명에서 불법 문자 제거

    Args:
        filename: 원본 파일명

    Returns:
        정제된 파일명
    """
    # Windows에서 불법인 문자들
    illegal_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(illegal_chars, '_', filename)

    # 공백을 언더스코어로 변경
    sanitized = sanitized.replace(' ', '_')

    # 연속된 언더스코어 제거
    sanitized = re.sub(r'_+', '_', sanitized)

    return sanitized


def validate_save_path(path: str, create_if_not_exists: bool = True) -> Tuple[bool, str]:
    """
    저장 경로 유효성 검증 및 생성

    Args:
        path: 검증할 저장 경로
        create_if_not_exists: 경로가 없을 경우 생성할지 여부

    Returns:
        (유효 여부, 에러 메시지)
    """
    is_valid, error_msg = validate_path(path, is_remote=False, must_exist=False)
    if not is_valid:
        return False, error_msg

    path_obj = Path(path)

    # 경로가 존재하지 않으면 생성 시도
    if not path_obj.exists():
        if create_if_not_exists:
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
                return True, ""
            except Exception as e:
                return False, f"경로 생성 실패: {str(e)}"
        else:
            return False, f"경로가 존재하지 않습니다: {path}"

    # 디렉토리인지 확인
    if not path_obj.is_dir():
        return False, f"경로가 디렉토리가 아닙니다: {path}"

    # 쓰기 권한 확인
    if not os.access(path, os.W_OK):
        return False, f"경로에 쓰기 권한이 없습니다: {path}"

    return True, ""
