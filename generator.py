import os
import json
import re
import urllib.request
from datetime import datetime

API_KEY = os.environ.get("GEMINI_API_KEY")
CUSTOM_IDEA = os.environ.get("CUSTOM_IDEA", "").strip()
BASE_URL = "https://mysmarttools.midonageeb94.workers.dev"

def load_tools():
    if os.path.exists("tools.json"):
        with open("tools.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def call_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        data = json.loads(response.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("لم يتم العثور على JSON صالح في رد Gemini")

def main():
    existing_tools = load_tools()
    existing_slugs = [t["slug"] for t in existing_tools]

    idea_instruction = (
        f"صمم هذه الأداة تحديداً: {CUSTOM_IDEA}"
        if CUSTOM_IDEA
        else f"اقترح فكرة أداة ويب مجانية جديدة عليها بحث عالٍ في جوجل (بالعربية أو الإنجليزية) ومنافسة متوسطة أو ضعيفة، وتجنب تكرار هذه الأدوات الموجودة مسبقاً: {existing_slugs}"
    )

    prompt = f"""
أنت خبير SEO ومطور ويب محترف. {idea_instruction}
الشروط الإلزامية للأداة:
1. تعمل بالكامل في المتصفح بـ HTML و Tailwind CSS (عبر CDN) و JavaScript بدون أي API خارجي.
2. تصميم عصري متجاوب مع الموبايل (استخدم خط Cairo من Google Fonts إذا كانت عربية).
3. يجب أن تحتوي الصفحة في المكان المناسب أعلى الأداة على:
   <div id="ad-slot-top" class="w-full min-h-[90px] bg-slate-100 border border-dashed border-slate-300 rounded-xl flex items-center justify-center text-xs text-slate-400 my-6">مساحة إعلانية</div>
4. ويجب أن تحتوي أسفل الأداة على:
   <div id="ad-slot-bottom" class="w-full min-h-[250px] bg-slate-100 border border-dashed border-slate-300 rounded-xl flex items-center justify-center text-xs text-slate-400 my-6">مساحة إعلانية</div>
5. يجب أن تحتوي قبل إغلاق </body> مباشرة على:
   <script src="/ads.js"></script>
6. تحتوي على رابط للعودة للرئيسية (<a href="/">الرئيسية</a>) ومقال SEO تعريفي بالأداة أسفلها.

أعد النتيجة بصيغة JSON فقط بدون أي نص إضافي خارج JSON، وبنفس المفاتيح التالية بالضبط:
{{
  "slug": "english-url-slug-like-qr-generator",
  "title": "عنوان الأداة المختصر للبطاقة",
  "category": "تصنيف الأداة مثل: أدوات النصوص أو حاسبات",
  "description": "وصف جذاب من سطرين للأداة",
  "html_code": "كود HTML الكامل للصفحة من <!DOCTYPE html> إلى </html>"
}}
"""

    print("جاري التواصل مع Gemini لتوليد الأداة...")
    raw_response = call_gemini(prompt)
    tool_data = extract_json(raw_response)

    slug = re.sub(r"[^a-z0-9-]", "", tool_data["slug"].lower().strip())
    if not slug or slug in existing_slugs:
        slug = f"tool-{int(datetime.now().timestamp())}"

    # 1. إنشاء مجلد الأداة وحفظ index.html
    os.makedirs(slug, exist_ok=True)
    with open(f"{slug}/index.html", "w", encoding="utf-8") as f:
        f.write(tool_data["html_code"])

    # 2. تحديث tools.json
    new_entry = {
        "slug": slug,
        "title": tool_data["title"],
        "category": tool_data["category"],
        "description": tool_data["description"],
        "url": f"{BASE_URL}/{slug}/",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    existing_tools.insert(0, new_entry)
    with open("tools.json", "w", encoding="utf-8") as f:
        json.dump(existing_tools, f, ensure_ascii=False, indent=2)

    # 3. تحديث sitemap.xml تلقائياً
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        f'  <url><loc>{BASE_URL}/</loc><priority>1.0</priority></url>'
    ]
    for t in existing_tools:
        sitemap_lines.append(f'  <url><loc>{BASE_URL}/{t["slug"]}/</loc><priority>0.8</priority></url>')
    sitemap_lines.append('</urlset>')

    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write("\n".join(sitemap_lines))

    print(f"تم توليد ونشر الأداة بنجاح: {BASE_URL}/{slug}/")

if __name__ == "__main__":
    main()
