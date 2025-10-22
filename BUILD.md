# 로그 수집 유틸리티 빌드 가이드

## 사전 요구사항

- Python 3.13
- PyInstaller 설치 완료
- 모든 의존성 패키지 설치 완료

## 빌드 방법

### 1. 개발 환경에서 실행

```bash
python main.py
```

### 2. PyInstaller로 실행 파일 생성

#### 방법 1: spec 파일 사용 (권장)

```bash
pyinstaller log_collector.spec --clean
```

#### 방법 2: 명령줄 옵션 사용

```bash
pyinstaller ^
  --name LogCollector ^
  --onefile ^
  --noconsole ^
  --hidden-import=paramiko ^
  --hidden-import=cryptography ^
  --hidden-import=bcrypt ^
  --hidden-import=pynacl ^
  --hidden-import=wx ^
  --exclude-module=matplotlib ^
  --exclude-module=pandas ^
  --exclude-module=scipy ^
  --exclude-module=tk ^
  --exclude-module=tcl ^
  --exclude-module=_tkinter ^
  --exclude-module=tkinter ^
  main.py
```

### 3. 빌드 결과 확인

빌드가 완료되면 다음 위치에 실행 파일이 생성됩니다:

```
dist/LogCollector.exe
```

### 4. 배포 파일 구성

배포 시 다음 구조로 제공:

```
LogCollector/
├── LogCollector.exe       (실행 파일)
├── README.md              (사용자 가이드)
└── config/                (최초 실행 시 자동 생성)
    └── config.json
```

## 빌드 옵션 설명

- `--onefile`: 단일 실행 파일로 빌드
- `--noconsole`: 콘솔 창 숨김 (Windows GUI 앱)
- `--clean`: 이전 빌드 캐시 삭제 후 재빌드
- `--hidden-import`: 동적으로 로드되는 모듈 명시
- `--exclude-module`: 불필요한 모듈 제외 (파일 크기 감소)
- `--upx`: UPX로 압축하여 실행 파일 크기 감소

## 빌드 최적화

### 실행 파일 크기 줄이기

1. UPX 설치 (선택사항)
   - https://github.com/upx/upx/releases
   - upx.exe를 PATH에 추가
   - spec 파일에서 `upx=True` 설정

2. 불필요한 모듈 제외
   - spec 파일의 `excludes` 리스트에 추가

### 실행 속도 향상

1. `--onefile` 대신 `--onedir` 사용 (압축 해제 시간 제거)
   - 단, 배포 시 폴더 전체를 배포해야 함

2. 바이러스 백신 예외 처리
   - PyInstaller로 생성된 실행 파일은 백신이 오진할 수 있음
   - 빌드 후 백신 예외 등록 권장

## 테스트

빌드 후 다음 항목을 테스트:

1. [ ] 실행 파일 더블클릭 실행
2. [ ] 콘솔 창이 표시되지 않는지 확인
3. [ ] 실행 시간이 3초 이내인지 확인
4. [ ] SSH 연결 테스트
5. [ ] 파일 수집 테스트
6. [ ] config/config.json 자동 생성 확인
7. [ ] logs/ 디렉토리 자동 생성 확인

## 문제 해결

### 실행 파일이 실행되지 않을 때

1. 백신 프로그램 확인
2. Windows Defender 예외 등록
3. --debug 옵션으로 재빌드하여 오류 확인

### 모듈을 찾을 수 없다는 오류

1. spec 파일의 `hiddenimports`에 모듈 추가
2. --hidden-import 옵션으로 재빌드

### 실행 파일 크기가 너무 클 때

1. spec 파일의 `excludes`에 불필요한 모듈 추가
2. UPX 압축 활성화
3. --onedir 모드 고려

## 버전 관리

빌드 시 버전 정보 추가:

```bash
pyinstaller log_collector.spec ^
  --clean ^
  --version-file version.txt
```

version.txt 예시:

```
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', 'Your Company'),
        StringStruct('FileDescription', 'Log Collection Utility'),
        StringStruct('FileVersion', '1.0.0.0'),
        StringStruct('ProductName', 'LogCollector'),
        StringStruct('ProductVersion', '1.0.0.0')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
```
