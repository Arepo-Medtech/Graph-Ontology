#!/usr/bin/env python3
"""Fetch openly-published AU therapeutic/prescribing guidance -> per-section markdown + JSON.

Usage:  python3 guidance_fetch.py URL [URL ...]
Key:    $FIRECRAWL_API_KEY, else read from ~/.claude.json firecrawl MCP entry.
"""
import json, os, re, sys, urllib.request, datetime, pathlib

OUT = pathlib.Path("out/guidance")

def api_key():
    k = os.environ.get("FIRECRAWL_API_KEY")
    if k:
        return k
    cfg = json.load(open(os.path.expanduser("~/.claude.json")))
    url = cfg["mcpServers"]["firecrawl"]["url"]
    m = re.search(r"mcp\.firecrawl\.dev/(fc-[^/]+)/v2/mcp", url)
    if not m:
        sys.exit("no API key: set FIRECRAWL_API_KEY")
    return m.group(1)

def scrape(url, key):
    req = urllib.request.Request(
        "https://api.firecrawl.dev/v2/scrape",
        data=json.dumps({"url": url, "formats": ["markdown"], "onlyMainContent": True}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        body = json.load(r)
    if not body.get("success"):
        raise RuntimeError(body.get("error", "scrape failed"))
    return body["data"]

def scrape_direct(url):
    """Fallback for domains Firecrawl declines (e.g. health.gov.au). Public pages only."""
    from bs4 import BeautifulSoup
    import subprocess
    html = subprocess.run(["curl", "-sSL", "--compressed", "--max-time", "60", url],
                          capture_output=True, check=True).stdout
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "nav", "header", "footer", "aside"]):
        t.decompose()
    main = soup.find("main") or soup.find("article") or soup.body
    out = []
    for el in main.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        txt = " ".join(el.get_text(" ", strip=True).split())
        if not txt:
            continue
        if el.name.startswith("h"):
            out.append(f"\n{'#' * int(el.name[1])} {txt}\n")
        elif el.name == "li":
            out.append(f"- {txt}")
        else:
            out.append(txt)
    title = soup.title.get_text(strip=True) if soup.title else url
    return {"markdown": "\n".join(out), "metadata": {"title": title, "url": url}}

def slug(s, n=60):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return (s[:n].rstrip("-")) or "untitled"

def split_sections(md):
    """Split on H2/H3. Text before the first heading becomes 'preamble'."""
    parts, cur = [], {"heading": "preamble", "level": 0, "lines": []}
    for line in md.splitlines():
        m = re.match(r"^(#{2,3})\s+(.*)", line)
        if m:
            if any(l.strip() for l in cur["lines"]) or cur["heading"] != "preamble":
                parts.append(cur)
            cur = {"heading": m.group(2).strip(), "level": len(m.group(1)), "lines": []}
        else:
            cur["lines"].append(line)
    if any(l.strip() for l in cur["lines"]):
        parts.append(cur)
    for p in parts:
        p["content"] = "\n".join(p.pop("lines")).strip()
    return [p for p in parts if p["content"]]

def fetch(url, key):
    try:
        data = scrape(url, key)
        via = "firecrawl"
    except Exception:
        data = scrape_direct(url)   # ponytail: crude tag-walk, swap in trafilatura if layouts get messy
        via = "direct"
    meta = data.get("metadata", {})
    title = meta.get("title") or url
    doc_slug = slug(title)
    sections = split_sections(data.get("markdown", ""))
    retrieved = datetime.datetime.now(datetime.timezone.utc).isoformat()

    d = OUT / doc_slug
    d.mkdir(parents=True, exist_ok=True)

    out_sections = []
    for i, s in enumerate(sections, 1):
        fn = f"{i:02d}-{slug(s['heading'])}.md"
        # LLM-ready: each section carries its own provenance header
        (d / fn).write_text(
            f"---\nsource: {url}\ndocument: {title}\nsection: {s['heading']}\n"
            f"retrieved: {retrieved}\n---\n\n## {s['heading']}\n\n{s['content']}\n"
        )
        out_sections.append({
            "index": i, "heading": s["heading"], "level": s["level"],
            "file": str(d / fn), "chars": len(s["content"]), "content": s["content"],
        })

    doc = {
        "title": title, "source_url": url,
        "canonical_url": meta.get("url", url),
        "description": meta.get("description"),
        "retrieved_utc": retrieved,
        "fetched_via": via,
        "section_count": len(out_sections),
        "sections": out_sections,
    }
    (OUT / f"{doc_slug}.json").write_text(json.dumps(doc, indent=2))
    return doc

def demo():
    md = "intro text\n\n## A\nalpha\n\n### B\nbeta\n\n## C\ngamma"
    s = split_sections(md)
    assert [x["heading"] for x in s] == ["preamble", "A", "B", "C"], s
    assert s[0]["content"] == "intro text"
    assert s[2]["level"] == 3 and s[2]["content"] == "beta"
    assert split_sections("## Empty\n\n\n") == []
    assert slug("Dosing & Administration!") == "dosing-administration"
    print("self-check ok")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "--demo":
        demo()
        sys.exit(0)
    key = api_key()
    for u in args:
        try:
            doc = fetch(u, key)
            print(f"{doc['section_count']:3d} sections  {doc['title'][:60]}")
        except Exception as e:
            print(f"FAIL {u}: {e}", file=sys.stderr)
