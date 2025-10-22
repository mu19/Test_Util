# Log Collector

Windows 기반 로그 수집 유틸리티 - 원격 Linux 서버와 로컬 Windows 시스템의 로그 파일을 손쉽게 수집

## 개요

소프트웨어 디버깅을 위해 Linux 서버와 Windows 클라이언트의 로그 파일을 효율적으로 수집하는 GUI 기반 유틸리티입니다.

## 주요 기능

### 파일 수집
- **원격 수집**: SSH/SFTP를 통한 Linux 서버 로그 파일 다운로드
- **로컬 수집**: Windows 시스템의 로그 파일 복사
- **재귀 수집**: 하위 디렉토리 포함 전체 파일 수집
- **구조 유지**: 원본 폴더 구조를 유지한 채로 압축

### 필터링
- **전체 수집**: 모든 파일 수집
- **정규식 필터**: 파일명 패턴 기반 선택적 수집
- **날짜 필터**: 특정 날짜 이후 수정된 파일만 수집

### 압축 및 삭제
- **자동 압축**: 수집된 파일을 타임스탬프 기반 압축 파일로 생성
- **원본 삭제**: 수집 후 원본 파일 자동 삭제 옵션
- **원격 압축**: 서버에서 압축 후 다운로드하여 네트워크 전송량 최소화

### 사용자 편의
- **SSH 연결 관리**: 연결 유지 및 자동 재연결
- **실시간 진행률**: 프로그레스 바 및 로그 출력
- **파일 선택**: 목록에서 특정 파일만 선택하여 수집
- **작업 취소**: 수집 중 언제든지 중단 가능

## 수집 대상

1. **제어기 커널 로그**: Linux 시스템 커널 로그 (원격)
2. **제어기 로그**: 사용자 서버 애플리케이션 로그 (원격)
3. **사용자 SW 로그**: Windows 클라이언트 애플리케이션 로그 (로컬)

## 시스템 요구사항

- **OS**: Windows 11
- **Python**: 3.13 (개발 환경)
- **배포**: 단독 실행 가능한 .exe 파일

## 기술 스택

- **GUI**: wxPython 4.2.3
- **SSH/SFTP**: Paramiko 4.0.0
- **압축**: zipfile, tar.gz
- **빌드**: PyInstaller

## 설치 및 실행

### 실행 파일 사용 (권장)
1. LogCollector.exe 다운로드
2. 더블 클릭하여 실행
3. 옵션 메뉴에서 SSH 및 경로 설정

### 소스 코드 실행
```bash
# 의존성 설치
pip install -r requirements.txt

# 프로그램 실행
python main.py
```

### 빌드
```bash
# PyInstaller로 .exe 빌드
pyinstaller log_collector.spec
```

## 기본 사용법

1. **초기 설정**
   - 메뉴 > 설정 > SSH 연결 정보 입력
   - 로그 소스별 경로 설정
   - 저장 경로 설정

2. **SSH 연결**
   - "연결" 버튼 클릭하여 원격 서버 연결

3. **로그 수집**
   - 수집할 로그 소스 선택
   - 필터 조건 설정 (선택)
   - "수집" 버튼 클릭

4. **파일 관리**
   - "목록" 버튼: 파일 목록 조회 및 선택 수집
   - "삭제" 버튼: 로그 파일 삭제

## 프로젝트 구조

```
c:\Laboratory\Test Util\
├── config/              # 설정 파일
│   └── config.json      # 사용자 설정
├── logs/                # 애플리케이션 로그
├── core/                # 핵심 로직
│   ├── ssh_manager.py   # SSH/SFTP 연결 관리
│   ├── file_collector.py # 파일 수집 조정
│   ├── filter_engine.py  # 파일 필터링
│   └── compression_handler.py # 압축 처리
├── services/            # 비즈니스 로직
│   ├── local_service.py  # 로컬 파일 처리
│   └── remote_service.py # 원격 파일 처리
├── ui/                  # 사용자 인터페이스
│   ├── main_frame.py     # 메인 윈도우
│   ├── settings_dialog.py # 설정 다이얼로그
│   └── log_window.py     # 로그 윈도우
├── utils/               # 유틸리티
│   └── logger.py         # 로깅 시스템
└── main.py              # 진입점
```

## 문서

- [사용자 가이드](USER_GUIDE.md) - 상세한 사용 방법
- [빌드 가이드](BUILD.md) - PyInstaller 빌드 절차
- [테스트 체크리스트](TEST_CHECKLIST.md) - 통합 테스트 가이드
- [수정 이력](modification.md) - 기능 개선 기록

## 주요 특징

### 안정성
- SSH Keep-alive로 장시간 연결 유지
- 권한 오류 파일 자동 건너뛰기
- 작업 중단 및 재시작 지원
- 원격 서버 빈 폴더 자동 정리

### 성능
- 비동기 파일 처리로 UI 응답성 유지
- 원격 압축으로 네트워크 전송량 감소
- 진행률 실시간 표시
- 디스크 용량 실시간 모니터링

### 유연성
- 압축 옵션에 따른 수집 방식 자동 전환
  - 압축 활성화: 원격 서버에서 압축 후 다운로드
  - 압축 비활성화: 개별 파일 다운로드, 타임스탬프 폴더에 저장
- 원격/로컬 파일 통합 관리

### 확장성
- Layer Architecture 설계
- Singleton, Factory, Observer 패턴 적용
- 향후 기능 추가 용이

## 라이선스

내부 사용 목적의 프로젝트

## 개발 환경

- **Language**: Python 3.13
- **IDE**: Visual Studio Code
- **Version Control**: Git
- **Platform**: Win 11
