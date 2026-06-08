# 비공개 웹 배포 안내

이 앱은 Streamlit 웹앱입니다. 클라우드나 서버에 배포하면 접속하는 컴퓨터에는 Python이 필요 없습니다.

## 1. 비밀번호 설정

앱은 `APP_PASSWORD`가 설정되어 있으면 첫 화면에서 비밀번호를 요구합니다.

Streamlit Community Cloud 기준:

1. 앱 관리 화면으로 이동
2. `Settings` 또는 `App settings`
3. `Secrets`에 아래 값 추가

```toml
APP_PASSWORD = "원하는_비밀번호"
```

로컬 테스트는 PowerShell에서 이렇게 할 수 있습니다.

```powershell
$env:APP_PASSWORD="원하는_비밀번호"
& "C:\Users\user\AppData\Local\Programs\Python\Python314\python.exe" -m streamlit run app.py
```

## 2. Streamlit Cloud 배포

1. GitHub에 비공개 저장소 생성
2. 이 폴더의 파일을 저장소에 업로드
3. Streamlit Cloud에서 새 앱 생성
4. 저장소와 브랜치 선택
5. Main file path에 `app.py` 입력
6. Secrets에 `APP_PASSWORD` 추가
7. Deploy

## 3. 주의 사항

- `view_history.json`은 로컬 파일 기록입니다. 클라우드에서는 서버 재시작 시 초기화될 수 있습니다.
- 외부 사이트의 뉴스/커뮤니티 수집은 해당 사이트 정책이나 차단에 따라 실패할 수 있습니다.
- 이 앱은 투자 조언이나 자동 주문 시스템이 아니라 분석 보조 도구입니다.
