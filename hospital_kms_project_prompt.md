# Prompt: Hospital Knowledge Management System (KMS) — Expert System + Knowledge Graph + GUI

## 🎯 الهدف العام (Project Goal)

ابنِ لي نظام Knowledge Management System (KMS) متكامل بلغة Python، يعتمد على بيانات مستشفى متوسط الحجم (Synthetic Hospital Data)، ويغطي دورة حياة المعرفة الكاملة (Knowledge Life Cycle: Acquisition → Representation → Reasoning → Evaluation → Visualization) من خلال ثلاث مكونات رئيسية مدمجة داخل واجهة رسومية واحدة:

1. **Expert System / Rule Engine** — باستخدام مكتبة `experta`
2. **Knowledge Graph** — باستخدام مكتبة `networkx`
3. **GUI** — باستخدام `tkinter` لعرض دورة حياة النظام وربط المكونين السابقين بصريًا

---

## 📂 وصف البيانات (Dataset Description)

مجموعة بيانات Synthetic تحاكي عمليات مستشفى متوسط الحجم، تركز على التوظيف (Staffing)، دخول المرضى (Admissions)، وتوزيع الأسرة على الأقسام (Bed Allocation). تسمح البيانات بتحليل توزيع الموارد، الطلب على الخدمة، والأداء على مستوى كل قسم.

تتكوّن من 4 ملفات CSV:

| الملف | الوصف |
|---|---|
| `hospital_staff.csv` | قائمة بالعاملين في المستشفى (الاسم، الوظيفة، القسم، الخ) |
| `hospital_patients.csv` | سجلات المرضى (الدخول، القسم، الحالة، الخ) |
| `hospital_service_weekly.csv` | بيانات أسبوعية على مستوى كل قسم/خدمة |
| `hospital_staff_schedule.csv` | جدول العمل الأسبوعي للطاقم |

> ملاحظة: قبل توليد أي كود، اقرأ أعمدة الملفات الأربعة فعليًا (مثلاً بـ `pandas.read_csv().columns`) بدل افتراض أسماء الأعمدة، وابنِ الـ Facts والـ Rules والـ Graph Nodes بناءً على الأعمدة الحقيقية الموجودة.

---

## 🧠 المكوّن الأول: Expert System / Rule Engine (باستخدام `experta`)

### المطلوب:
- عرّف `Fact` classes تمثل الكيانات الأساسية المستخرجة من البيانات، مثل:
  - `StaffFact` (department, role, shift_count, availability)
  - `PatientFact` (department, admission_status, length_of_stay, severity)
  - `ServiceFact` (department, week, bed_occupancy_rate, demand_level)
- عرّف `KnowledgeEngine` باسم واضح مثل `HospitalExpertSystem` يحتوي على مجموعة `Rule`s تحاكي قرارات تشغيلية حقيقية، على سبيل المثال:
  - إذا `bed_occupancy_rate > 90%` وعدد الطاقم المتاح أقل من حد معين → استنتاج `"Critical Staffing Shortage"` في هذا القسم.
  - إذا `demand_level = High` لعدة أسابيع متتالية في نفس القسم → استنتاج `"Consider Bed Reallocation"`.
  - إذا نسبة تغطية الشيفتات أقل من نسبة معينة → استنتاج `"Schedule Imbalance Alert"`.
  - (أضف 5-8 قواعد إضافية منطقية بناءً على الأعمدة الفعلية في الداتا)
- كل Rule لازم يطلع **نتيجة قابلة للعرض** (نص + مستوى خطورة: Low / Medium / High / Critical) بحيث يتغذى منها الـ GUI لاحقًا.
- اعمل دالة `run_expert_system(dataframes) -> list[dict]` ترجع النتائج بصيغة منظمة (dict فيها: القسم، القاعدة المفعّلة، الاستنتاج، الخطورة).

---

## 🕸️ المكوّن الثاني: Knowledge Graph (باستخدام `networkx`)

### المطلوب:
- ابنِ `DiGraph` (أو `Graph` حسب الحاجة) يمثل العلاقات بين المفاهيم الأساسية المستخرجة من الداتا ومن نتائج الـ Expert System، مثل:
  - Nodes: الأقسام (Departments)، أنواع الوظائف (Roles)، حالات المرضى (Patient Status)، الاستنتاجات (Expert System Conclusions)، مستويات الخطورة (Severity Levels)
  - Edges: علاقات مثل `Department → HAS_STAFF_ROLE → Role`، `Department → TRIGGERED → Conclusion`، `Conclusion → HAS_SEVERITY → Severity Level`، `Department → WEEK → ServiceMetric`
- كل Node يحمل `attributes` (نوع العقدة، قيمة، بيانات إضافية) لتلوين وتصنيف العقد لاحقًا في الـ GUI.
- اعمل دالة `build_knowledge_graph(dataframes, expert_system_results) -> networkx.DiGraph` تبني الجراف ديناميكيًا من البيانات الحقيقية + نتائج الـ Rule Engine (يعني الجراف يتغير حسب نتائج الاستدلال).
- اعمل دالة تحليل بسيطة فوق الجراف (مثلاً: أكثر قسم مرتبط باستنتاجات حرجة، أو `degree_centrality` لأهم العقد) لعرضها كـ "KM Insight" في الواجهة.

---

## 🖥️ المكوّن الثالث: GUI (باستخدام `tkinter`)

### المطلوب:
- واجهة تمثل **دورة حياة الـ KMS** بشكل مراحل واضحة (تابات أو Sidebar Navigation)، كل مرحلة فيها تقييم/عرض مختلف:
  1. **Data Acquisition** — عرض ملخص سريع للـ 4 ملفات (عدد الصفوف، عدد الأعمدة، عينة بيانات) بعد تحميلها.
  2. **Knowledge Representation** — زرار لتشغيل بناء الـ Facts وعرض عددها/نوعها.
  3. **Reasoning (Expert System)** — زرار "Run Expert System" يشغّل الـ `KnowledgeEngine` ويعرض النتائج في جدول (Treeview) مع تلوين حسب مستوى الخطورة (أحمر Critical، برتقالي High، أصفر Medium، أخضر Low).
  4. **Knowledge Graph Visualization** — رسم الـ `networkx` graph مباشرة داخل نافذة الـ tkinter (باستخدام `matplotlib` مع `FigureCanvasTkAgg` كـ embed داخل tkinter، وليس نافذة منفصلة).
  5. **Evaluation Summary** — ملخص نصي لكل مرحلة (هل نجحت، عدد النتائج، أهم Insight) يُصدَّر لاحقًا كملف تقرير.
- الواجهة تدعم **RTL styling بصريًا مناسب** حتى لو النصوص إنجليزية (خط واضح، ألوان هادئة مريحة للعين، تصميم منظم وليس افتراضي بالكامل).
- زرار عام "Run Full KMS Cycle" يشغّل كل المراحل بالترتيب تلقائيًا.
- Error handling واضح: لو ملف CSV ناقص أو عمود غير موجود، اعرض رسالة خطأ داخل الواجهة نفسها بدل الكراش.

---

## 📄 المخرج الرابع: تقرير Markdown

بعد تشغيل الدورة الكاملة، اعمل دالة `export_kms_report_to_md(expert_results, graph_insights, output_path="kms_report.md")` تنتج ملف `.md` يحتوي:
- عنوان المشروع وتاريخ التشغيل
- جدول بنتائج الـ Expert System (القسم، القاعدة، الاستنتاج، الخطورة)
- ملخص نصي لأهم Insights من الـ Knowledge Graph
- تقييم عام لكل مرحلة من مراحل دورة حياة الـ KMS (نجحت / فيها تحذيرات / فشلت + السبب)
- قسم توصيات تشغيلية (Operational Recommendations) مبنية على الاستنتاجات

---

## 🛠️ المتطلبات التقنية (Technical Requirements)

- Python 3.10+
- المكتبات: `experta`, `networkx`, `matplotlib`, `pandas`, `tkinter` (built-in)
- الكود منظم في ملفات منفصلة:
  - `data_loader.py`
  - `expert_system.py`
  - `knowledge_graph.py`
  - `gui_app.py`
  - `report_exporter.py`
  - `main.py` (نقطة التشغيل)
- Docstrings واضحة لكل دالة/كلاس
- لا تفترض قيم أو أعمدة وهمية — اقرأ من الـ CSV الفعلي أولًا

---

## ✅ معايير القبول (Acceptance Criteria)

- [ ] تشغيل `main.py` يفتح الواجهة الرسومية بدون أخطاء
- [ ] زرار Run Expert System يعرض نتائج حقيقية مبنية على القواعد المعرّفة
- [ ] الـ Knowledge Graph يتغير فعليًا حسب نتائج الاستدلال (مش Graph ثابت)
- [ ] الرسم يظهر داخل نافذة tkinter مباشرة (مش نافذة matplotlib منفصلة)
- [ ] ملف `.md` يتولّد فعليًا في نهاية الدورة ويحتوي كل الأقسام المطلوبة
