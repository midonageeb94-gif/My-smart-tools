import os
import json
import re
import urllib.request
import urllib.error
from datetime import datetime

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
CUSTOM_IDEA = os.environ.get("CUSTOM_IDEA", "").strip()
BASE_URL = "https://mysmarttools.midonageeb94.workers.dev"

def load_tools():
    if os.path.exists("tools.json"):
        with open("tools.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def get_working_model():
    """يجلب قائمة الموديلات النشطة في حسابك ويختار أنسب موديل Flash تلقائياً"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
        models = data.get("models", [])
        # البحث عن موديلات flash المتاحة لتوليد النصوص
        flash_models = [
            m["name"] for m in models
            if "generateContent" in m.get("supportedGenerationMethods", [])
            and "flash" in m["name"].lower()
            and "lite" not in m["name"].lower()
            and "audio" not in m["name"].lower()
            and "image" not in m["name"].lower()
        ]
        if flash_models:
            # اختيار أحدث إصدار متاح
            flash_models.sort(reverse=True)
            return flash_models[0]
        # خيار بديل إذا لم يوجد flash
        for m in models:
            if "generateContent" in m.get("supportedGenerationMethods", []):
                return m["name"]
    raise RuntimeError("لم يتم العثور على أي موديل نشط في هذا المفتاح.")

def call_gemini(prompt):
    if not API_KEY:
        raise ValueError("خطأ: مفتاح GEMINI_API_KEY غير مضاف في Secrets!")

    model_name = get_working_model()
    print(f"الموديل المختار تلقائياً: {model_name}")

    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json"
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"فشل الاتصال بـ Gemini API (كود {e.code}): {err_body}")

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

أعد كائن JSON يحتوي على المفاتيح التالية فقط:
- "slug": رابط إنجليزي قصير مفصول بشرطات مثل qr-code-generator
- "title": عنوان الأداة المختصر للبطاقة
- "category": تصنيف الأداة مثل أدوات النصوص أو حاسبات
- "description": وصف جذاب من سطرين للأداة
- "html_code": كود HTML الكامل للصفحة من <!DOCTYPE html> إلى </html>
"""

    print("جاري التواصل مع Gemini لتوليد الأداة...")
    raw_response = call_gemini(prompt)
    tool_data = json.loads(raw_response)

    slug = re.sub(r"[^a-z0-9-]", "", tool_data["slug"].lower().strip())
    if not slug or slug in existing_slugs:
        slug = f"tool-{int(datetime.now().timestamp())}"

    os.makedirs(slug, exist_ok=True)
    with open(f"{slug}/index.html", "w", encoding="utf-8") as f:
        f.write(tool_data["html_code"])

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
