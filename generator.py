import os
import json
import re
import socket
import random
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

    gemini_flash.sort(reverse=True)
    return gemini_flash + gemini_others + gemma_models

def extract_json_from_text(text):
    text = text.strip()
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
        
        gen_config = {"temperature": 0.75}
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

def build_related_tools_html(existing_tools, is_arabic=True):
    """يبني قسم الربط الداخلي التلقائي لزيادة الزيارات ومشاهدات الإعلانات"""
    if not existing_tools:
        return ""
    sample = random.sample(existing_tools, min(4, len(existing_tools)))
    heading = "أدوات مجانية أخرى قد تهمك" if is_arabic else "More Free Online Tools"
    cards = ""
    for t in sample:
        cards += f"""
        <a href="/{t['slug']}/" class="block p-4 bg-white border border-slate-200 rounded-xl hover:border-emerald-400 hover:shadow-sm transition">
          <div class="text-xs font-semibold text-emerald-700 mb-1">{t.get('category', 'Tool')}</div>
          <div class="font-bold text-slate-800 text-sm mb-1">{t['title']}</div>
          <div class="text-xs text-slate-500 line-clamp-2">{t['description']}</div>
        </a>
        """
    return f"""
    <section class="mt-10 pt-8 border-t border-slate-200">
      <h2 class="text-lg font-extrabold text-slate-800 mb-4">{heading}</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {cards}
      </div>
    </section>
    """

def main():
    existing_tools = load_tools()
    existing_slugs = [t["slug"] for t in existing_tools]

    # التنويع الذكي بين الأدوات العربية والإنجليزية (لرفع عائد CPM الإعلاني)
    use_english = (len(existing_tools) % 3 == 2) and not CUSTOM_IDEA

    if CUSTOM_IDEA:
        idea_instruction = f"صمم هذه الأداة تحديداً بأعلى جودة ممكنة: {CUSTOM_IDEA}"
    elif use_english:
        idea_instruction = (
            f"Suggest a high-search-volume, low-competition English micro-tool (like a specific calculator, text converter, developer utility, or generator) "
            f"that runs 100% client-side in JavaScript. Avoid duplicating these existing slugs: {existing_slugs}. "
            f"Write the entire tool page, title, description, SEO guide, and FAQs in clear, natural English with dir='ltr' and lang='en'."
        )
    else:
        idea_instruction = (
            f"اقترح فكرة أداة ويب مجانية باللغة العربية تستهدف كلمة مفتاحية محددة (Long-tail Keyword) عليها بحث حقيقي في مصر والسعودية والعالم العربي "
            f"ومنافسة ضعيفة (مثل حاسبات متخصصة، تحويلات، أدوات نصوص، مولدات روابط أو باركود، أو أدوات للمعلمين والطلاب والمسوقين)، "
            f"وتجنب تكرار هذه الأدوات الموجودة مسبقاً: {existing_slugs}."
        )

    prompt = f"""
أنت خبير SEO عالمي ومطور ويب محترف. {idea_instruction}

الشروط الإلزامية للأداة:
1. تعمل بالكامل في المتصفح بـ HTML و Tailwind CSS (عبر CDN) و JavaScript بدون أي API خارجي، وتكون دقيقة ومفيدة فعلياً للمستخدم مع زر نسخ النتيجة أو تحميلها.
2. تصميم عصري متجاوب مع الموبايل (استخدم خط Cairo من Google Fonts للأدوات العربية، و Inter للأدوات الإنجليزية).
3. تحسين SEO كامل: عنوان `<title>` جذاب غني بالكلمات المفتاحية، ووسم `<meta name="description">`.
4. يجب أن تحتوي الصفحة أعلى الأداة على حاوية الإعلان العلوي بالضبط:
   <div id="ad-slot-top" class="w-full min-h-[90px] bg-slate-100 border border-dashed border-slate-300 rounded-xl flex items-center justify-center text-xs text-slate-400 my-6">Ad Space</div>
5. ويجب أن تحتوي أسفل الأداة مباشرة على حاوية الإعلان السفلي بالضبط:
   <div id="ad-slot-bottom" class="w-full min-h-[250px] bg-slate-100 border border-dashed border-slate-300 rounded-xl flex items-center justify-center text-xs text-slate-400 my-6">Ad Space</div>
6. أضف أسفل الإعلان السفلي مقالاً تعريفياً مفيداً يشرح طريقة استخدام الأداة وفوائدها، وقسم الأسئلة الشائعة (FAQ) مع كود Schema.org JSON-LD في `<head>` لرفع الترتيب في جوجل.
7. أضف في الهيدر رابطاً واضحاً للعودة للرئيسية (`<a href="/">الرئيسية</a>` أو `<a href="/">Home</a>`).
8. يجب أن تحتوي قبل إغلاق `</body>` مباشرة على:
   <script src="/ads.js"></script>

أعد كائن JSON فقط بدون أي نص إضافي، يحتوي على المفاتيح التالية:
- "slug": رابط إنجليزي قصير مفصول بشرطات مثل vat-calculator-saudi
- "title": عنوان الأداة المختصر للبطاقة (بنفس لغة الأداة)
- "category": تصنيف الأداة مثل حاسبات أو أدوات النصوص أو Calculators
- "description": وصف جذاب من سطرين للأداة (بنفس لغة الأداة)
- "is_arabic": true إذا كانت الأداة بالعربية أو false إذا كانت بالإنجليزية
- "html_code": كود HTML الكامل للصفحة من <!DOCTYPE html> إلى </html>
"""

    print("جاري التواصل مع Gemini لتوليد الأداة...")
    tool_data = call_gemini(prompt)

    slug = re.sub(r"[^a-z0-9-]", "", tool_data["slug"].lower().strip())
    if not slug or slug in existing_slugs:
        slug = f"tool-{int(datetime.now().timestamp())}"

    html_code = tool_data["html_code"]
    is_arabic = tool_data.get("is_arabic", not use_english)

    # حقن قسم الربط الداخلي للأدوات الأخرى قبل الفوتر أو قبل ads.js
    related_html = build_related_tools_html(existing_tools, is_arabic=is_arabic)
    if related_html:
        if "</main>" in html_code:
            html_code = html_code.replace("</main>", f"{related_html}\n</main>", 1)
        elif '<script src="/ads.js"></script>' in html_code:
            html_code = html_code.replace('<script src="/ads.js"></script>', f'{related_html}\n<script src="/ads.js"></script>', 1)

    os.makedirs(slug, exist_ok=True)
    with open(f"{slug}/index.html", "w", encoding="utf-8") as f:
        f.write(html_code)

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
        f'  <url><loc>{BASE_URL}/</loc><priority>1.0</priority></url
