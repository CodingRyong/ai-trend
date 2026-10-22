# AI 트렌드

YouTube · GitHub · Hugging Face Papers · Hacker News · GeekNews에서 핫한 AI 콘텐츠를 모아 보는 정적 사이트.
GitHub Actions가 8시간마다 `fetch.py`를 실행해 `docs/data.json`을 만들고 GitHub Pages로 배포한다.

## 처음 한 번 설정

1. GitHub에 저장소를 만들고 이 폴더를 `main` 브랜치로 푸시 (무료 Pages는 공개 저장소 필요)
2. Settings → Secrets and variables → Actions → `YOUTUBE_API_KEY` 등록 (YouTube Data API v3 키)
3. Settings → Pages → Source를 **GitHub Actions**로 변경
4. Actions 탭에서 `fetch` 워크플로를 한 번 수동 실행(Run workflow) → 사이트 주소는 워크플로 결과에 표시

## 로컬 실행

```bash
set YOUTUBE_API_KEY=...   # 없으면 YouTube 탭만 실패로 표시됨
python fetch.py
python -m http.server 8123 -d docs
```
