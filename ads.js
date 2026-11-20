/**
 * ملف التحكم المركزي في الإعلانات (يدعم التحميل المتتابع لمنع تعارض atOptions)
 */

const AD_CONFIG = {
  isActive: true,

  topAd: {
    key: '67fae04e2be7f7b248566bcba3c3aae0',
    format: 'iframe',
    height: 90,
    width: 728,
    src: 'https://bauval.org/22/67fae04e2be7f7b248566bcba3c3aae0'
  },

  bottomAd: {
    key: '57fa1616c307ef0dcb7ff58c72a0b916',
    format: 'iframe',
    height: 250,
    width: 300,
    src: 'https://bauval.org/22/57fa1616c307ef0dcb7ff58c72a0b916'
  }
};

function loadAdUnit(slotId, adData) {
  return new Promise((resolve) => {
    const container = document.getElementById(slotId);
    if (!container || !AD_CONFIG.isActive) {
      resolve();
      return;
    }

    // تنظيف تنسيق المساحة المؤقتة
    container.innerHTML = '';
    container.classList.remove('bg-slate-100', 'border', 'border-dashed', 'border-slate-300', 'text-slate-400');
    container.classList.add('overflow-x-auto', 'flex', 'justify-center', 'items-center');

    // تعيين المتغير العام الخاص بالإعلان الحالي
    window.atOptions = {
      'key': adData.key,
      'format': adData.format,
      'height': adData.height,
      'width': adData.width,
      'params': {}
    };

    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = adData.src;
    script.onload = () => setTimeout(resolve, 300);
    script.onerror = () => resolve();

    container.appendChild(script);
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadAdUnit('ad-slot-top', AD_CONFIG.topAd);
  await loadAdUnit('ad-slot-bottom', AD_CONFIG.bottomAd);
});
