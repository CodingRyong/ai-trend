"""AI 트렌드 수집기: 소스 5개 -> docs/data.json (+ Gemini 한국어 번역). 표준 라이브러리만 사용."""
import html, json, os, re, time
import urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "data.json")
NOW = datetime.now(timezone.utc)
UA = {"User-Agent": "ai-trend-feed (github actions)"}


def get(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def get_json(url, headers=None):
    return json.loads(get(url, headers))


def days_ago(n):
    return (NOW - timedelta(days=n)).strftime("%Y-%m-%dT%H:%M:%SZ")


def item(title, url, score, meta, published):
    return {"title": title, "url": url, "score": score, "meta": meta, "published": published}


# AI 공부 채널. 핸들: 채널 ID (채널 추가: 채널 페이지 → 정보 → 공유 → 채널 ID 복사)
CHANNELS = {
    "3blue1brown": "UCYO_jab_esuFRV4b17AJtAw",
    "AndrejKarpathy": "UCXUPKJO5MZQN11PqgIvyuvQ",
    "TwoMinutePapers": "UCbfYPyITQ-7l4upoX8nvctg",
    "YannicKilcher": "UCZHmQk67mSJgfCCTn7xBfew",
    "aiexplained-official": "UCNJ1Ymd5yFuUPtn21xtRbbw",
    "Fireship": "UCsBjURrPoezykLs9EqgamOA",
    "freecodecamp": "UC8butISFwT-Wl7EV0hUK0BQ",
    "statquest": "UCtYLUTtgS3k1Fg4y5tAhLbw",
    "sentdex": "UCfzlCWGWYyIQ0aLC5w48gBQ",
    "Deeplearningai": "UCcIXc5mJsHVYTZR1maL5l9w",
    "samwitteveenai": "UC55ODQSvARtgSyc8ThfiepQ",
    "umarjamilai": "UCtAcpQcYerN8xxZJYTfWBMw",
    "IBMTechnology": "UCKWaEZ-_VweaEx1j62do_vQ",
    "AIJasonZ": "UCrXSVX9a1mj8l0CMLwKgMVw",
    "code4AI": "UCfOvNb3xj28SNqPQ_JIbumg",
    "stanfordonline": "UCBa5G_ESCn8Yd4vw5U-gIcg",
    "mitocw": "UCEBb1b_L6zDS3xTUrIALZOw",
    "bycloudAI": "UCgfe2ooZD3VJPB6aJAnuQng",
    "AICoffeeBreak": "UCobqgqE4i5Kf7wrxRxhToQA",
    "MachineLearningStreetTalk": "UCMLtBahI5DMrt0NPvDSoIRQ",
    "SerranoAcademy": "UCgBncpylJ1kiVaPyP-PZauQ",
    "krishnaik06": "UCNU_lfiiWBdtULKOw6X0Dig",
    "NicholasRenotte": "UCHXa4OpASJEwrHrLeIzw7Yg",
    "campusx-official": "UCCWi3hpnq_Pe03nGxuS7isg",
    "daveebbelaar": "UCn8ujwUInbJkBhffxqAPBVQ",
    "ColeMedin": "UCMwVTLZIRRUyyVrkjDpn4pA",
    "jocoding": "UCQNE2JmbasNYbjGAcuBiRRg",
    "nomadcoders": "UCUpJs89fSBXNolQGOYKn0YQ",
    "teddynote": "UCt2wAAXgm87ACiQnDHQEW6Q",
    "bbanghyong": "UC9PB9nKYqKEx_N3KM-JVTpg",
    "unrealtech": "UCeN2YeJcBCRJoXgzF_OU3qw",
    "codingapple": "UCSLrpBAzr-ROVGHQ5EmxnUg",
    "TheEasyoung": "UCxP77kNgVfiiG6CXZ5WMuAQ",
    "suanlab": "UCFfALXX0DOx7zv6VeR5U_Bg",
    "coohde": "UCvc8kv-i5fvFTJBFAk6n1SA",
    "dongbinna": "UChflhu32f5EUHlY7_SetNWw",
}
def _secs(iso):  # ISO 8601 "PT1H2M3S" -> 초. 라이브(P0D) 등 비정형은 0
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    return sum(int(x or 0) * k for x, k in zip(m.groups(), (3600, 60, 1))) if m else 0


def youtube():
    # 채널 RSS는 2026-10-24부터 404라 Data API로 각 채널 업로드 목록을 읽는다 (채널당 1 unit, 하루 약 120 units).
    # 전체 검색은 조회수순이면 예능·주식 영상이 상위라 채널을 직접 고른다.
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY secret not set")
    base, since, ids, last_err = "https://www.googleapis.com/youtube/v3/", days_ago(14), [], None
    for cid in CHANNELS.values():
        q = urllib.parse.urlencode({"part": "contentDetails", "playlistId": "UU" + cid[2:], "maxResults": 10, "key": key})
        try:
            ids += [x["contentDetails"]["videoId"] for x in get_json(base + "playlistItems?" + q)["items"]
                    if x["contentDetails"].get("videoPublishedAt", "") >= since]
        except Exception as e:  # 채널 하나가 죽어도 나머지는 보여준다
            last_err = e
    if not ids and last_err:
        raise last_err  # 전부 실패면 진짜 원인(키 오류 등)을 화면에 보여준다
    out = []
    for n in range(0, len(ids), 50):
        q = urllib.parse.urlencode({"part": "snippet,statistics,contentDetails", "id": ",".join(ids[n:n + 50]), "key": key})
        for v in get_json(base + "videos?" + q)["items"]:
            secs = _secs(v["contentDetails"]["duration"])
            if secs < 180:  # 쇼츠(최대 3분)·라이브 제외
                continue
            it = item(v["snippet"]["title"], "https://www.youtube.com/watch?v=" + v["id"], int(v["statistics"].get("viewCount", 0)),
                      v["snippet"]["channelTitle"], v["snippet"]["publishedAt"])
            it["duration"] = secs
            out.append(it)
    return sorted(out, key=lambda x: -x["score"])[:30]


def github():
    # GitHub Trending 비공식 RSS(정적 Pages라 인증·rate limit 없음). Search API는 Actions에서 토큰 있으면 0건, 없으면 403이었다.
    # shortcut: 피드에 스타 수·날짜가 없음, 필요하면 PAT 시크릿 + Search API로 교체
    out = []
    for it in ET.fromstring(get("https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml")).findall("./channel/item"):
        m = re.search(r"<p>(.*?)</p>", it.findtext("description") or "", re.S)
        desc = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
        out.append(item(it.findtext("title"), it.findtext("link"), None, desc[:120], ""))
    return out


def hf_papers():
    seen, out = set(), []
    for d in ("", "&date=" + (NOW - timedelta(days=1)).strftime("%Y-%m-%d")):  # 오늘 + 어제 (UTC 이른 시간엔 오늘이 비어있음)
        for p in get_json("https://huggingface.co/api/daily_papers?limit=50" + d):
            pid = p["paper"]["id"]
            if pid in seen:
                continue
            seen.add(pid)
            out.append(item(p["paper"]["title"], "https://huggingface.co/papers/" + pid, p["paper"].get("upvotes", 0),
                            (p["paper"].get("summary") or "")[:160], p.get("publishedAt") or p["paper"].get("publishedAt", "")))
    return sorted(out, key=lambda x: -x["score"])[:30]


def hackernews():
    q = urllib.parse.urlencode({"query": "AI", "tags": "story", "hitsPerPage": 30,
                                "numericFilters": f"created_at_i>{int(time.time()) - 7 * 86400},points>30"})
    hits = get_json("https://hn.algolia.com/api/v1/search?" + q)["hits"]
    return sorted((item(h["title"], h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}", h["points"],
                        f"{h['num_comments']} comments · {h['author']}", h["created_at"]) for h in hits),
                  key=lambda x: -x["score"])


AI_KW = re.compile(r"(?<![A-Za-z])(AI|LLM|GPT|RAG|MCP)(?![A-Za-z])|Claude|Gemini|OpenAI|Anthropic|인공지능|에이전트|딥러닝|머신러닝", re.I)


def geeknews():
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(get("https://news.hada.io/rss/news")).findall("a:entry", ns):
        title = e.findtext("a:title", "", ns)
        if AI_KW.search(title):
            out.append(item(title, e.find("a:link", ns).get("href"), None, "", e.findtext("a:updated", "", ns)))
    return out[:30]


HANGUL = re.compile(r"[가-힣]")
# 소스별 번역할 필드. GitHub 제목은 저장소 이름, YouTube meta는 채널명, HN meta는 "N comments · author"라 번역 안 함
TRANSLATE = {"youtube": ("title",), "github": ("meta",), "hf": ("title", "meta"), "hn": ("title",), "geeknews": ("title",)}


def translate(data):
    """제목·설명을 Gemini로 한국어 번역해 title_ko/meta_ko에 넣는다. 이미 한글이면 건너뛴다."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY secret not set")
    # 지난 배포의 번역을 재사용해 새 항목만 보낸다. 매번 전부 보내면 무료 한도(429)에 걸린다.
    owner, _, repo = os.environ.get("GITHUB_REPOSITORY", "CodingRyong/ai-trend").partition("/")
    prev = {}
    try:
        for s in get_json(f"https://{owner.lower()}.github.io/{repo}/data.json")["sources"]:
            for i in s["items"]:
                prev.update({i[k]: i[k + "_ko"] for k in ("title", "meta") if i.get(k + "_ko")})
    except Exception:
        pass  # 첫 배포·사이트 장애면 전부 새로 번역
    todo = []
    for s in data["sources"]:
        for i in s["items"]:
            for k in TRANSLATE[s["key"]]:
                if not i[k] or HANGUL.search(i[k]):
                    continue
                if i[k] in prev:
                    i[k + "_ko"] = prev[i[k]]
                else:
                    todo.append((i, k))
    print(f"translate: {len(todo)} new strings, {len(prev)} cached")
    for n in range(0, len(todo), 30):  # 묶음이 크면 느리고(타임아웃) 길이 불일치도 잦다
        chunk = todo[n:n + 30]
        prompt = ("다음 JSON 문자열 배열을 자연스러운 한국어로 번역해, 같은 길이·같은 순서의 JSON 문자열 배열만 출력하라. "
                  "모델명·제품명·코드 식별자·사람 이름은 원문 그대로 둔다.\n" + json.dumps([i[k] for i, k in chunk], ensure_ascii=False))
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                           "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}).encode()
        req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent",
                                     data=body, headers={**UA, "Content-Type": "application/json", "x-goog-api-key": key})
        for attempt in range(3):  # 503 과부하·타임아웃·길이 불일치는 쉬었다가 다시 시도
            try:
                with urllib.request.urlopen(req, timeout=240) as r:
                    out = json.loads(json.load(r)["candidates"][0]["content"]["parts"][0]["text"])
                if len(out) != len(chunk):
                    raise ValueError(f"translation length mismatch: {len(out)} != {len(chunk)}")
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(30 * (attempt + 1))
        for (i, k), ko in zip(chunk, out):
            if ko and ko != i[k]:  # 원문 그대로면 중복 표시하지 않는다
                i[k + "_ko"] = ko


SOURCES = [("youtube", "YouTube", "조회수", youtube), ("github", "GitHub", "", github),
           ("hf", "HF Papers", "👍", hf_papers), ("hn", "Hacker News", "pt", hackernews),
           ("geeknews", "GeekNews", "", geeknews)]


def main():
    data = {"generated_at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "sources": []}
    for key, name, unit, fn in SOURCES:
        try:
            data["sources"].append({"key": key, "name": name, "unit": unit, "items": fn()})
        except Exception as e:  # 한 소스가 죽어도 나머지는 저장
            data["sources"].append({"key": key, "name": name, "unit": unit, "items": [], "error": f"{type(e).__name__}: {e}"})
        s = data["sources"][-1]
        if not s["items"]:
            s.setdefault("error", "0 items returned")
        print(f"{name}: {len(s['items'])} items {s.get('error', '')}")
    try:
        translate(data)
    except Exception as e:  # 번역이 실패해도 원문으로 배포
        data["translate_error"] = f"{type(e).__name__}: {e}"
    print("translate:", data.get("translate_error", "ok"))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    assert sum(bool(s["items"]) for s in data["sources"]) >= 3, "too few sources returned data"


if __name__ == "__main__":
    assert _secs("PT1H2M3S") == 3723 and _secs("PT45S") == 45 and _secs("P0D") == 0  # 자가검사
    assert AI_KW.search("AI가 바꾸는 개발") and not AI_KW.search("Email 보내기")
    assert HANGUL.search("AI 강의") and not HANGUL.search("AI lecture")
    main()
