# PyInstaller 빌드 가이드

## 빌드 방법

### 1. 기본 빌드 (spec 파일 사용)
```bash
pyinstaller build_exe.spec
```

### 2. 직접 빌드 (spec 파일 없이)
```bash
pyinstaller --name=StudyWith ^
    --onefile ^
    --windowed ^
    --add-data "src/study_with/resources;resources" ^
    --hidden-import=PIL._webp ^
    --hidden-import=flask ^
    --hidden-import=flask_cors ^
    --hidden-import=psutil ^
    main.py
```

## 확인 사항

### ✅ 이미 처리된 부분
1. **리소스 경로 처리**: `_MEIPASS` 체크가 `app.py`와 `ui.py`에 모두 구현되어 있음
2. **폰트 로드**: `resource_path("font.ttf")` 사용으로 PyInstaller에서도 정상 작동
3. **이미지 로드**: Pillow를 통한 webp 이미지 로드가 구현되어 있음

### ⚠️ 주의사항

1. **Flask 서버**: 백그라운드에서 실행되는 Flask 서버가 exe에서도 정상 작동하는지 테스트 필요
2. **관리자 권한**: Windows에서 관리자 권한 요청이 exe에서도 정상 작동하는지 확인
3. **리소스 파일**: 모든 리소스 파일이 포함되었는지 확인
   - `resources/font.ttf`
   - `resources/images/*.webp`
   - `resources/sounds/*.mp3`
   - `resources/presets/Default.txt`

### 🔍 테스트 체크리스트

빌드 후 다음을 확인하세요:

- [ ] 프로그램이 정상적으로 시작되는가?
- [ ] 커스텀 폰트가 적용되는가?
- [ ] 티어 이미지가 표시되는가?
- [ ] 사운드가 재생되는가?
- [ ] 세션 기록이 저장/로드되는가?
- [ ] 통계 창이 정상 작동하는가?
- [ ] Flask API 서버가 정상 작동하는가? (확장 프로그램 연동)
- [ ] 관리자 권한 요청이 정상 작동하는가?

## 문제 해결

### 리소스 파일을 찾을 수 없는 경우
- `build_exe.spec`의 `datas` 항목 확인
- 빌드된 exe와 같은 폴더에 `resources` 폴더가 있는지 확인

### Pillow webp 지원 문제
- `--hidden-import=PIL._webp` 추가 확인
- 또는 `pip install pillow`로 최신 버전 설치

### Flask 서버 문제
- 백그라운드 스레드가 exe에서도 정상 작동하는지 확인
- 포트 충돌이 없는지 확인
