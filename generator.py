import os
import json
import re
import socket
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

def get_candidate_models():
    """يجلب قائمة الموديلات المتاحة ويرتبها مع إعطاء الأولوية لموديلات Gemini السريعة"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
        models = data.get("models", [])

    excluded_words = ["omni", "audio", "image", "tts", "embedding", "aqa", "vision", "robotics", "computer-use", "deep-research"]
    gemini_flash = []
    gemini_others = []
    gemma_models = []

    for m in models:
        name = m["name"]
        lower = name.lower()
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" not in methods or any(w in lower for w in excluded_words):
            continue
        if "gemini" in lower and "flash" in lower:
            gemini_flash.append(name)
        elif "gemini" in lower:
            gemini_others.append(name)
        else:
            gemma_models.append(name)

    # ترتيب موديلات flash بحيث تكون الأحدث أولاً
    gemini_flash.sort(reverse=True)
    ordered = gemini_flash + gemini_others + gemma_models
    print("الموديلات المتاحة في حسابك:", ordered)
    return ordered

def extract_json_from_text(text):
    text = text.strip()
    # إزالة علامات markdown إن وجدت
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("لم يتم العثور على JSON صالح في الرد")

def call_gemini(prompt):
    if not API_KEY:
        raise ValueError("خطأ: مفتاح GEMINI_API_KEY غير مضاف في Secrets!")

    candidates = get_candidate_models()
    if not candidates:
        raise RuntimeError("لم يتم العثور على أي موديل نصي متاح في المفتاح.")

    last_error = ""
    for model_name in candidates:
        print(f"جاري تجربة الموديل: {model_name} ...")
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={API_KEY}"
        
        gen_config = {"temperature": 0.7}
        if "gemini" in model_name.lower():
            gen_config["responseMimeType"] = "application/json"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": gen_config
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=65) as response:
                data = json.loads(response.read().decode("utf-8"))
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                # التحقق من أن الرد JSON سليم قبل الاعتماد
                parsed = extract_json_from_text(raw_text)
                print(f"نجح التوليد عبر الموديل: {model_name}")
                return parsed
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            last_error = f"{model_name} -> كود {e.code}: {err_body[:150]}"
            print(f"تم تخطي {model_name} (كود {e.code})، جاري تجربة الموديل التالي...")
            continue
        except (TimeoutError, socket.timeout, urllib.error.URLError) as e:
            last_error = f"{model_name} -> انتهت مهلة الاتصال: {e}"
            print(f"تأخر {model_name} في الرد، جاري الانتقال للموديل التالي...")
            continue
        except Exception as e:
            last_error = f"{model_name} -> خطأ تحليل الرد: {e}"
            print(f"رد غير صالح من {model_name}، جاري تجربة التالي...")
            continue

    raise RuntimeError(f"فشلت جميع الموديلات المتاحة. آخر خطأ: {last_error}")

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

أعد كائن JSON فقط بدون أي نص إضافي، يحتوي على المفاتيح التالية:
- "slug": رابط إنجليزي قصير مفصول بشرطات مثل qr-code-generator
- "title": عنوان الأداة المختصر للبطاقة
- "category": تصنيف الأداة مثل أدوات النصوص أو حاسبات
- "description": وصف جذاب من سطرين للأداة
- "html_code": كود HTML الكامل للصفحة من <!DOCTYPE html> إلى </html>
"""

    print("جاري التواصل مع Gemini لتوليد الأداة...")
    tool_data = call_gemini(prompt)

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
