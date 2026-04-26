# 일정 캘린더 앱 (Streamlit)

한국어 UI 기반의 일정 관리 앱입니다.  
날짜별 일정(거래처, 업무내용, 금액)을 관리하고, 자동 저장/불러오기 및 수익 요약 시각화를 제공합니다.

## 주요 기능

- 월/주/일 캘린더 보기
- 일정 추가/수정/삭제 (팝업)
- 거래처별 색상 박스 표시
- 데이터 자동 저장: `schedule.csv`
- CSV 불러오기 지원
- 수익 요약:
  - 이번 주/이번 달 총 수익
  - 거래처별 수익 막대차트
  - 월별 수익 및 전월 대비 증감 그래프

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run calendar_app.py
```

## 데이터 파일

- 앱 데이터는 실행 폴더의 `schedule.csv`에 자동 저장됩니다.
- `schedule.csv`는 개인/업무 데이터 보호를 위해 `.gitignore`에 포함되어 Git 추적에서 제외됩니다.

## GitHub 업로드 준비

아래 명령으로 바로 업로드할 수 있습니다.

```bash
git init
git add .
git commit -m "Initial commit: Streamlit calendar app"
```

원격 저장소를 만든 뒤:

```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
git branch -M main
git push -u origin main
```
