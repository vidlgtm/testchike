# testchike — قالب فيديو كرتوني 3D (three.js داخل Remotion) يُرندَر على Colab T4

> Template for ~55-70 s vertical cartoon story shorts: *flat 2D characters in a colourful 3D toon world*, voice-over,
> synthesized SFX + original score. Source: the free **claude-animated-shorts** skill (video: *"How to Make Viral Animated
> Shorts Using Claude"*), reorganised into a **fixed engine + variable project** template that renders on a **free Colab T4**.

## ⚡ التشغيل السريع (Quick start)
1. افتح `colab/Render_Short_T4.ipynb` في Colab: `File ▸ Open notebook ▸ GitHub` ← `vidlgtm/testchike` (المستودع خاص: اربط حسابك أو ارفع الملف يدويًا).
2. `Runtime ▸ Change runtime type ▸ T4 GPU`.
3. أضف في **Secrets** مفتاحًا باسم `GITHUB_TOKEN` (توكن بصلاحية قراءة المستودع) — أو الصقه عند الطلب (لا يُكتب في أي ملف).
4. غيّر `PROJECT` (الافتراضي `bridge`) و`QUALITY` (`preview` / `1080p` / `2k`) ثم **Run all**.

الخلايا: بارامترات ← فحص GPU ← سحب المستودع (+Drive للاستئناف) ← تجهيز الجهاز ← **فحص WebGL على GPU** ← التحقق من القالب
← الصوت (edge-tts + faster-whisper) ← الموسيقى والمؤثرات والمكس ← صور فحص الشكل (stills) ← **الرندر على أجزاء** ← فحص الجودة والتنزيل.

لا يُرندَر أي شيء خارج Colab. الرندر مقسّم إلى أجزاء (chunks) وتُحفظ على Drive، فإذا انقطع الاتصال يُكمل من آخر جزء.

## 🧱 القالب: الثابت والمتغيّر
الملف الكامل: **[`TEMPLATE_CONTRACT.md`](TEMPLATE_CONTRACT.md)**. باختصار:

| الثابت (لا يُعدَّل أبدًا) | المتغيّر (يكتبه المؤلف لكل فيديو في `projects/<name>/`) |
|---|---|
| `src/engine/*` — الخطوط (ink)، العدسة (DOF)، التدرّج اللوني، الإضاءة `day`/`golden`، الرسم، الشخصيات، المُركِّب `Short.tsx` | `SCRIPT.md` + `voice/script.txt` — القصة والسكربت |
| `audio_engine/*` — DSP، الآلات، مولدات المؤثرات، المكس (‏−15 LUFS) | `video/story.ts` — اللقطات والكاميرا والـDOF والفيزياء |
| `tools/*`, `colab/*` — الصوت، فحص GPU، التحقق، الرندر، QA | `video/build.ts`, `world.ts`, `cast.ts` — المكان والشخصيات |
| `public/kenney/*` — مجسمات CC0 | `audio/timeline.py`, `sfx.py`, `music.py`, `mix_config.py` — الصوت |

`python tools/check_project.py <name>` يرفض أي تعديل على الثابت، ويتأكد أن `story.ts` و`timeline.py` يصفان نفس الفيديو، وأن TypeScript يُترجَم.

## 🤖 ربط المستودع بنموذج آخر
النموذج يقرأ `AGENTS.md` (نفسه `CLAUDE.md`) ثم `TEMPLATE_CONTRACT.md`. مهمته: كتابة السكربت والملفات المتغيّرة فقط:
```bash
python tools/new_project.py my_story --title "My Story"   # ينسخ bridge كنقطة بداية + TODO.md
# ... يكتب SCRIPT.md, voice/script.txt, video/*.ts, audio/*.py ...
python tools/check_project.py my_story                    # يجب أن يطبع 0 error(s)
```
ثم تفتح Colab وتضع `PROJECT = "my_story"`.

## 🗂 هيكل المستودع
```
colab/Render_Short_T4.ipynb   الدفتر الجاهز        colab/setup_colab.sh   تجهيز T4 (Node, Chrome, Vulkan/EGL, ...)
src/engine/                   الشكل الثابت         src/Root.tsx           التركيبة Short (1080x1920)
projects/bridge/              المثال المُثبَت: video/ audio/ voice/ SCRIPT.md project.json
audio_engine/                 محرك الصوت الثابت    tools/                 voice, gpu_probe, render, check_project, new_project, QA
references/                   STYLE_BIBLE + 7 تقارير قياس + 38 إطار مرجعي + 20 contact sheet + نص الـskill الأصلي
```

## ⚠️ ملاحظات صادقة
- **مشروع `bridge` مضبوط يدويًا على الصوت الأصلي** (لقطات وأصوات الكسر/الطرق/الدرج بالثانية). تسجيل الصوت الأصلي (voice.wav) غير موجود في الملف المضغوط،
  لذلك الصوت المولَّد (edge-tts) سيختلف توقيته عن الصورة. للحصول على تطابق دقيق: ضع تسجيلك الأصلي في `projects/bridge/voice/voice.wav`
  (`engine: "file"`)، أو أعد ضبط `story.ts` + `timeline.py` بجدول `words_to_frames.py`. الفيديوهات الجديدة تُكتب أصلًا على توقيت `words.json` فلا مشكلة.
- GPU على Colab: الدفتر يثبّت `libnvidia-gl-<driver>` ويجرّب `vulkan` ثم `angle-egl` ثم `angle` ويطبع الحكم. إن لم يوجد WebGL عتادي سيتراجع إلى SwiftShader (CPU) وهو بطيء جدًا — لا تُكمل الرندر حينها.
- الرندر 2K (1440x2560) أبطأ ~1.8× من 1080p؛ ابدأ بـ `preview` ثم `1080p`.
- أُنجز التحقق هنا بـ: `tsc` + `remotion bundle` + تحليل Python للصوت — **لم يُرندَر أي إطار محليًا** (حسب شرطك)، لذا أول تشغيل على Colab هو الاختبار الحقيقي لمسار GPU؛ إن فشلت خطوة فارسل لي سجلها.
- 🔐 ملاحظة أمان: لا تضع التوكن في أي ملف. التوكن الذي شاركته في المحادثة يجب **إلغاؤه وتوليد غيره** بعد الانتهاء.

## License
MIT (original code © Mr omi) — see `LICENSE` and `NOTICE.md`. Kenney assets CC0.
