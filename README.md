# AI 트렌드

AI 공부 채널 36개의 YouTube 영상 · GitHub Trending · Hugging Face Papers · Hacker News · GeekNews를 한 페이지에서 보는 정적 사이트.
GitHub Actions가 8시간마다 `fetch.py`를 실행해 `docs/data.json`을 만들고 GitHub Pages로 배포한다.
제목·설명은 Gemini로 한국어 번역해 원문과 함께 보여준다.

사이트: https://codingryong.github.io/ai-trend/

## 설정

1. 저장소 Settings → Secrets and variables → Actions → `GEMINI_API_KEY` 등록
   (https://aistudio.google.com/apikey 에서 결제 없이 발급. 없으면 번역만 빠지고 나머지는 동작)
2. Settings → Pages → Source가 **GitHub Actions**인지 확인
3. Actions 탭에서 `fetch` 워크플로를 수동 실행(Run workflow)하면 바로 반영

YouTube는 `YOUTUBE_API_KEY` 시크릿(YouTube Data API v3 키)으로 채널 업로드 목록을 읽는다. 채널 RSS는 2026-10-24부터 막혔다.

## 채널 추가·삭제

`fetch.py`의 `CHANNELS`를 고친다. 채널 ID는 유튜브 채널 페이지 → 정보 → 공유 → **채널 ID 복사**.

## 로컬 실행

```bash
python fetch.py
python -m http.server 8123 -d docs
```
