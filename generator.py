import os, json, re, socket, random, urllib.request, urllib.error
from datetime import datetime, timezone

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
CUSTOM_IDEA = os.environ.get("CUSTOM_IDEA", "").strip()
BASE_URL = "https://mysmarttools.midonageeb94.workers.dev"

def load_tools():
    if os.path.exists("tools.json"):
        with open("tools.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def get_candidate_models():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    with urllib.request.urlopen(urllib.request.Request(url), timeout=30) as r:
        models = json.loads(r.read().decode("utf-8")).get("models", [])
    bad = ["omni", "audio", "image", "tts", "embedding", "aqa", "vision", "robotics", "computer-use", "deep-research"]
    flash, others, gemma = [], [], []
    for m in models:
        n, low = m["name"], m["name"].lower()
        if "generateContent" not in m.get("supportedGenerationMethods", []) or any(w in low for w in bad):
            continue
        if "gemini" in low and "flash" in low: flash.append(n)
        elif "gemini" in low: others.append(n)
        else: gemma.append(n)
    flash.sort(reverse=True)
    return flash + others + gemma

def call_gemini(prompt):
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is missing")
    last_err = ""
    for m in get_candidate_models():
        print(f"Trying: {m}")
        url = f"https://generativelanguage.googleapis.com/v1beta/{m}:generateContent?key={API_KEY}"
        cfg = {"temperature": 0.75}
        if "gemini" in m.lower():
            cfg["responseMimeType"] = "application/json"
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": cfg}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=65) as r:
                txt = json.loads(r.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"].strip()
                txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt)
                return json.loads(re.search(r"\{.*\}", txt, re.DOTALL).group(0))
        except Exception as e:
            last_err = f"{m}: {e}"
            continue
    raise RuntimeError(f"All models failed. Last error: {last_err}")

def related_html(tools, is_ar=True):
    if not tools: return ""
    head = "أدوات مجانية أخرى قد تهمك" if is_ar else "More Free Online Tools"
    cards = "".join(
        f'<a href="/{t["slug"]}/" class="block p-4 bg-white border border-slate-200 rounded-xl hover:border-emerald-400 transition">'
        f'<div class="text-xs font-semibold text-emerald-700 mb-1">{t.get("category","Tool")}</div>'
        f'<div class="font-bold text-slate-800 text-sm mb-1">{t["title"]}</div>'
        f'<div class="text-xs text-slate-500">{t["description"]}</div></a>'
        for t in random.sample(tools, min(4, len(tools)))
    )
    return f'<section class="mt-10 pt-8 border-t border-slate-200"><h2 class="text-lg font-extrabold text-slate-800 mb-4">{head}</h2><div class="grid grid-cols-1 sm:grid-cols-2 gap-4">{cards}</div></section>'

def main():
    tools = load_tools()
    slugs = [t["slug"] for t in tools]
    use_en = (len(tools) % 3 == 2) and not CUSTOM_IDEA

    if CUSTOM_IDEA:
        idea = f"Build this exact tool: {CUSTOM_IDEA}"
    elif use_en:
        idea = f"Suggest a high-search, low-competition English client-side web micro-tool (dir='ltr', lang='en'). Avoid: {slugs}."
    else:
        idea = f"اقترح أداة ويب عربية مجانية تستهدف كلمة مفتاحية محددة قليلة المنافسة في مصر والسعودية. تجنب: {slugs}."

    prompt = (
        f"You are an expert SEO web developer. {idea}\n"
        "Requirements:\n"
        "1. 100% client-side HTML + Tailwind CSS CDN + JavaScript with copy/reset button.\n"
        "2. Responsive design (Cairo font for Arabic, Inter for English), full SEO <title> and <meta description>.\n"
        "3. Include top ad slot: <div id=\"ad-slot-top\" class=\"w-full min-h-[90px] bg-slate-100 border border-dashed border-slate-300 rounded-xl flex items-center justify-center text-xs text-slate-400 my-6\">Ad Space</div>\n"
        "4. Include bottom ad slot: <div id=\"ad-slot-bottom\" class=\"w-full min-h-[250px] bg-slate-100 border border-dashed border-slate-300 rounded-xl flex items-center justify-center text-xs text-slate-400 my-6\">Ad Space</div>\n"
        "5. Add SEO guide, FAQ section with JSON-LD Schema in <head>, Home link (<a href='/'>Home</a>), and <script src=\"/ads.js\"></script> before </body>.\n"
        "Return ONLY valid JSON with keys: slug, title, category, description, is_arabic (boolean), html_code."
    )

    data = call_gemini(prompt)
    slug = re.sub(r"[^a-z0-9-]", "", data["slug"].lower().strip())
    if not slug or slug in slugs:
        slug = f"tool-{int(datetime.now().timestamp())}"

    html = data["html_code"]
    rel = related_html(tools, data.get("is_arabic", not use_en))
    if rel:
        if "</main>" in html: html = html.replace("</main>", rel + "\n</main>", 1)
        elif '<script src="/ads.js"></script>' in html: html = html.replace('<script src="/ads.js"></script>', rel + '\n<script src="/ads.js"></script>', 1)

    os.makedirs(slug, exist_ok=True)
    with open(f"{slug}/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    now = datetime.now(timezone.utc)
    tools.insert(0, {
        "slug": slug, "title": data["title"], "category": data["category"],
        "description": data["description"], "url": f"{BASE_URL}/{slug}/",
        "created_at": now.strftime("%Y-%m-%d %H:%M"),
        "pub_date_rfc822": now.strftime("%a, %d %b %Y %H:%M:%S +0000")
    })
    with open("tools.json", "w", encoding="utf-8") as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)

    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', f'  <url><loc>{BASE_URL}/</loc><priority>1.0</priority></url>']
    sm += [f'  <url><loc>{BASE_URL}/{t["slug"]}/</loc><priority>0.8</priority></url>' for t in tools]
    sm.append('</urlset>')
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write("\n".join(sm))

    items = []
    for t in tools[:20]:
        pd = t.get("pub_date_rfc822") or now.strftime("%a, %d %b %Y %H:%M:%S +0000")
        items.append(f"    <item><title><![CDATA[{t['title']}]]></title><link>{BASE_URL}/{t['slug']}/</link><guid>{BASE_URL}/{t['slug']}/</guid><description><![CDATA[{t['description']}]]></description><enclosure url=\"{BASE_URL}/icon.png\" type=\"image/png\" /><pubDate>{pd}</pubDate></item>")
    rss = f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>أدواتي الذكية</title><link>{BASE_URL}/</link><description>أدوات ويب مجانية</description>\n' + "\n".join(items) + '\n</channel></rss>'
    with open("rss.xml", "w", encoding="utf-8") as f:
        f.write(rss)

    print(f"Published: {BASE_URL}/{slug}/")

if __name__ == "__main__":
    main()
