"""AI 트렌드 수집기: 소스 5개 -> docs/data.json. 표준 라이브러리만 사용."""
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


def _secs(iso):  # ISO 8601 "PT1H2M3S" -> 초. 라이브(P0D) 등 비정형은 0
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


def youtube():
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY secret not set")
    base = "https://www.googleapis.com/youtube/v3/"
    # videoCategoryId 27 = 교육(강의·설명). 전체는 예능·밈, 28(과학·기술)은 제품 리뷰·뉴스가 상위를 차지했다
    q = urllib.parse.urlencode({"part": "snippet", "type": "video", "order": "viewCount", "videoCategoryId": "27",
                                "q": "AI|LLM|머신러닝|딥러닝|\"machine learning\" -shorts", "publishedAfter": days_ago(7), "maxResults": 50, "key": key})
    ids = [x["id"]["videoId"] for x in get_json(base + "search?" + q)["items"]]
    q = urllib.parse.urlencode({"part": "snippet,statistics,contentDetails", "id": ",".join(ids), "key": key})
    out = []
    for v in get_json(base + "videos?" + q)["items"]:
        if _secs(v["contentDetails"]["duration"]) < 180:  # 쇼츠(최대 3분)·라이브 제외
            continue
        out.append(item(v["snippet"]["title"], "https://www.youtube.com/watch?v=" + v["id"],
                        int(v["statistics"].get("viewCount", 0)), v["snippet"]["channelTitle"],
                        v["snippet"]["publishedAt"]))
    return sorted(out, key=lambda x: -x["score"])


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
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    assert sum(bool(s["items"]) for s in data["sources"]) >= 3, "too few sources returned data"


if __name__ == "__main__":
    assert _secs("PT1H2M3S") == 3723 and _secs("PT45S") == 45 and _secs("P0D") == 0  # 자가검사
    assert AI_KW.search("AI가 바꾸는 개발") and not AI_KW.search("Email 보내기")
    main()
