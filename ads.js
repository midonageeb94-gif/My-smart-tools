/**
 * ملف التحكم المركزي في الإعلانات لجميع صفحات الموقع
 * أي تعديل هنا ينعكس فوراً على الصفحة الرئيسية وجميع الأدوات
 */

const AD_CONFIG = {
  // اجعلها true عند وضع أكواد الإعلانات الحقيقية لإزالة الإطار المنقط
  isActive: true,

  // كود الإعلان العلوي (يفضل مقاس متجاوب أو 320x50 للموبايل و 728x90 للكمبيوتر)
  topAdCode: `
    <script>
  atOptions = {
    'key' : '67fae04e2be7f7b248566bcba3c3aae0',
    'format' : 'iframe',
    'height' : 90,
    'width' : 728,
    'params' : {}
  };
</script>
<script src="https://bauval.org/22/67fae04e2be7f7b248566bcba3c3aae0"></script>
  `,

  // كود الإعلان السفلي (يفضل مقاس 300x250 أو Native Banner)
  bottomAdCode: `
    <script>
  atOptions = {
    'key' : '57fa1616c307ef0dcb7ff58c72a0b916',
    'format' : 'iframe',
    'height' : 250,
    'width' : 300,
    'params' : {}
  };
</script>
<script src="https://bauval.org/22/57fa1616c307ef0dcb7ff58c72a0b916"></script>
  `
};

function injectAd(slotId, adHtml) {
  const container = document.getElementById(slotId);
  if (!container || !AD_CONFIG.isActive) return;

  // تنظيف تنسيق المساحة المؤقتة
  container.innerHTML = '';
  container.classList.remove('bg-slate-100', 'border', 'border-dashed', 'border-slate-300', 'text-slate-400');

  // إنشاء عنصر مؤقت لتحليل الأكواد والسكربتات وتشغيلها بشكل سليم
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = adHtml.trim();

  Array.from(tempDiv.childNodes).forEach(node => {
    if (node.tagName === 'SCRIPT') {
      const newScript = document.createElement('script');
      Array.from(node.attributes).forEach(attr => {
        newScript.setAttribute(attr.name, attr.value);
      });
      newScript.textContent = node.textContent;
      container.appendChild(newScript);
    } else {
      container.appendChild(node.cloneNode(true));
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  injectAd('ad-slot-top', AD_CONFIG.topAdCode);
  injectAd('ad-slot-bottom', AD_CONFIG.bottomAdCode);
});
