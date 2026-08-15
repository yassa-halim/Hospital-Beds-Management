# 🏥 Hospital Knowledge Management System (KMS) — Project Documentation & Specification

---

## 🎯 1. نظرة عامة والهدف العام (Project Overview)

**نظام إدارة المعرفة لأسرة وعمليات المستشفى (Hospital Beds Management KMS)** هو تطبيق متكامل بلغة **Python** يعتمد على بيانات تشغيلية وسريرية لمستشفى متوسط الحجم (Synthetic Hospital Dataset). 

يقوم النظام بتطبيق **دورة حياة المعرفة الكاملة (Knowledge Life-Cycle)**:
$$\text{Data Acquisition} \longrightarrow \text{Knowledge Representation} \longrightarrow \text{Reasoning (Rules)} \longrightarrow \text{Knowledge Graph} \longrightarrow \text{Evaluation Dashboard}$$

يجمع النظام بين ثلاث ركائز تقنية داخل واجهة رسومية موحدة:
1. **Rule-Based Expert System:** محرك استدلال أمامي (Forward-Chaining Rule Engine) لتقييم المخاطر التشغيلية والسريرية وإطلاق التنبيهات.
2. **Dynamic Knowledge Graph:** شبكة دلالية موجهة (Directed Semantic Graph) مبنية عبر مكتبة `networkx` تربط الأقسام، الطواقم الطبية، الفئات العمرية للمرضى، الأحداث الطارئة، واستنتاجات القواعد.
3. **Interactive GUI:** واجهة رسومية متطورة بمظهر داكن عصري مبنية بـ `tkinter` و `matplotlib`، تتيح استكشاف البيانات، تصفية النتائج، والتنقل التفاعلي بين مراحل دورة حياة المعرفة.

---

## 🏗️ 2. الهيكل المعماري للمشروع (Project Structure)

```text
Hospital Beds Management/
│
├── dataset/                         # مجلد البيانات الأصلية (CSV Datasets)
│   ├── patients.csv                 # سجلات 1000 مريض (الدخول، الخروج، القسم، الرضا)
│   ├── services_weekly.csv          # مقاييس أسبوعية لـ 4 أقسام على مدار 52 أسبوعاً (208 سجل)
│   ├── staff.csv                    # بيانات 110 فرد من الطاقم الطبي
│   └── staff_schedule.csv           # سجلات الحضور والمناوبات الأسبوعية (6552 سجل)
│
├── data_loader.py                   # استيراد البيانات، التحقق من الأعمدة، وحساب المؤشرات والمعدلات
├── expert_system.py                 # محرك القواعد الخبير (Facts + Forward-Chaining Rules)
├── knowledge_graph.py               # بناء الجراف الدلالي، التحليل الشبكي، والتلوين التفاعلي
├── gui_app.py                       # الواجهة الرسومية وتكامل مراحل دورة حياة الـ KMS
├── main.py                          # نقطة الانطلاق الرئيسية للتطبيق (CLI & Launch Entry)
├── requirements.txt                 # التبعيات البرمجية للمشروع
└── hospital_kms_project_prompt.md   # وثيقة الشرح والمواصفات الكاملة للمشروع
```

---

## 📂 3. مجموعة البيانات واكتساب المعرفة (Data Acquisition — `data_loader.py`)

يتعامل النظام مع 4 ملفات بيانات CSV حقيقية، ويقوم بحساب مؤشرات مشتقة (Derived Analytics) دون أي افتراضات مسبقة:

| الملف | السجلات | الأعمدة الأساسية | العمليات والمؤشرات المشتقة (Derived Features) |
|---|---|---|---|
| `patients.csv` | 1,000 | `patient_id`, `name`, `age`, `arrival_date`, `departure_date`, `service`, `satisfaction` | • حساب مدة الإقامة: $\text{length\_of\_stay} = \text{departure} - \text{arrival}$<br>• تصنيف الفئات العمرية (`Pediatric <18`, `Adult 18-64`, `Geriatric 65+`) |
| `services_weekly.csv` | 208 | `week`, `month`, `service`, `available_beds`, `patients_request`, `patients_admitted`, `patients_refused`, `patient_satisfaction`, `staff_morale`, `event` | • نسبة إشغال الأسرة: $\text{bed\_occupancy\_rate} = \frac{\text{admitted}}{\text{beds}}$<br>• معدل رفض المرضى: $\text{refusal\_rate} = \frac{\text{refused}}{\text{request}}$<br>• ضغط الطلب: $\text{demand\_pressure} = \frac{\text{request}}{\text{beds}}$<br>• الطلب غير الملبى: $\text{unmet\_demand} = \text{request} - \text{admitted}$ |
| `staff.csv` | 110 | `staff_id`, `staff_name`, `role`, `service` | • مطابقة الطواقم الطبية وتوزيع الأدوار (`doctor`, `nurse`, `nursing_assistant`) على الأقسام الأربعة. |
| `staff_schedule.csv` | 6,552 | `week`, `staff_id`, `staff_name`, `role`, `service`, `present` | • تجميع معدل الحضور الفعلي لكل وظيفة وقسم.<br>• حساب نسبة المرضى لكل ممرض أسبوعياً (`patients_per_nurse`). |

### الأقسام الطبية المراقبة (Hospital Services):
1. **Emergency (الطوارئ)**
2. **ICU (العناية المركزة)**
3. **General Medicine (الباطنة والطب العام)**
4. **Surgery (الجراحة)**

---

## 🗂️ 4. تمثيل المعرفة (Knowledge Representation)

يتم تحويل السجلات الخام إلى كائنات حقائق صريحة (**Fact Classes**) لتغذية محرك الاستدلال:

- **`ServiceFact`**: يمثل الحالة التشغيلية الأسبوعية للقسم (الأسرة، الإشغال، الرفض، ضغط الطلب، معنويات الطاقم، الأحداث، عدد الأطباء والممرضين النشطين).
- **`StaffFact`**: يمثل الملف التعريفي للتوظيف في كل قسم (عدد الأفراد، معدل الحضور، إجمالي المناوبات).
- **`PatientFact`**: يمثل الخصائص الديموغرافية وسلوك المرضى في القسم (متوسط الإقامة، الرضا، نسبة كبار السن والأطفال).

---

## 🧠 5. محرك الاستدلال والقواعد الخبيرة (Reasoning — `expert_system.py`)

يحتوي كلاس `HospitalExpertSystem` على 14 قاعدة استدلالية تغطي الأزمات التشغيلية والسريرية، مصنفة حسب 4 مستويات خطورة:
- 🔴 **Critical (حرج)**
- 🟠 **High (مرتفع)**
- 🟡 **Medium (متوسط)**
- 🟢 **Low (منخفض / مؤشرات إيجابية)**

### جدول القواعد الخبيرة المتقدم (Prescriptive Rule Base Matrix with Action Plans & Certainty Factors):

| # | اسم القاعدة (Rule Name) | الشرط المنطقي (Condition) | الخطورة | معامل الثقة (Confidence) | الإجراء التصحيحي المقترح (Prescriptive Action Plan) |
|---|---|---|---|---|---|
| 1 | **Critical Overload** | `occupancy > 90%` و `morale < 60` | 🔴 Critical | $0.70 - 1.00$ | تفعيل بروتوكول الطوارئ القصوى، تجميد التنويم الاختياري، واستدعاء طواقم دعم إضافية. |
| 2 | **Emergency Access Crisis** | `service == emergency` و `refusal_rate > 75%` | 🔴 Critical | $0.75 - 1.00$ | إنشاء مسار سريع لتفريغ الأسرة بأقسام الباطنة لفتح طاقة استيعابية فورية للطوارئ. |
| 3 | **Doctor Coverage Shortage** | `role == doctor` و `avg_presence < 60%` | 🔴 Critical | $0.80 - 1.00$ | بدء استقطاب أطباء مؤقتين (Locum) واعتماد حوافز مناوبات إضافية للأطباء المناوبين. |
| 4 | **Strike Operational Disruption** | `event == strike` و `occupancy > 75%` | 🔴 Critical | $0.85 - 1.00$ | تفعيل خطة الطوارئ العمالية وتوقيع اتفاقيات الحد الأدنى الإلزامي لتغطية الحالات الحرجة. |
| 5 | **Bed Reallocation Needed** | `refusal_rate > 60%` لـ 3 أسابيع متتالية | 🟠 High | $0.75 - 1.00$ | إجراء تدقيق تنفيذي لحصص الأسرة ونقل الأسرة الزائدة من الأقسام منخفضة الإشغال. |
| 6 | **Flu Epidemic Surge Alert** | `event == flu` و `demand_pressure > 3.0` | 🟠 High | $0.80 - 1.00$ | تجهيز أسرة طوارئ موسمية، تخصيص نقاط فرز للجهاز التنفسي، واعتماد ساعات عمل إضافية للتمريض. |
| 7 | **Demand Exceeds Capacity** | `patients_refused > patients_admitted` | 🟠 High | $0.70 - 1.00$ | تسريع جولات تقييم جاهزية الخروج الصباحية لزيادة معدل دوران الأسرة المتاحة. |
| 8 | **Nursing Workload Strain** | `patients_per_nurse >= 3.0` أو غياب تمريضي | 🟠 High | $0.75 - 0.98$ | إعادة توزيع الممرضين الاحتياطيين (Float Pool) فوراً لاستعادة النسبة الآمنة لمراقبة المرضى. |
| 9 | **Quality & Morale Drop** | `satisfaction < 65` و `morale < 60` | 🟡 Medium | $0.70 - 1.00$ | عقد جلسات استماع للقيادات السريرية وإطلاق مبادرات لدعم الصحة النفسية ومكافحة الاحتراق الوظيفي. |
| 10 | **ICU Bed Turnover Bottleneck** | `service == ICU` و `avg_length_of_stay > 7.5 days` | 🟡 Medium | $0.75 - 1.00$ | مأسسة جولات خروج يومية متعددة التخصصات لنقل المرضى المستقرين لوحدات الرعاية المتوسطة. |
| 11 | **Geriatric Care Profile** | `geriatric_pct > 28%` و `avg_length_of_stay > 7.5 days` | 🟡 Medium | $0.75 - 1.00$ | تعيين ممرضات استشاريات لرعاية المسنين وبدء خطط التأهيل الطبي المبكر قبل الخروج. |
| 12 | **Donation Resource Uplift** | `event == donation` و `morale >= 80` | 🟢 Low | $0.80 - 1.00$ | توجيه الأجهزة والمعدات المتبرع بها لمناطق الاختناق السريري لتعزيز كفاءة الخدمة ومعنويات الطاقم. |
| 13 | **Low Bed Utilisation** | `occupancy < 40%` و `refused == 0` | 🟢 Low | $0.75 - 1.00$ | تخصيص جزء من الأسرة الفائضة كأسرة مرنة (Flex Beds) لدعم أقسام الطوارئ المزدحمة. |
| 14 | **Operational Excellence** | `morale > 90` و `satisfaction > 90` | 🟢 Low | $0.85 - 1.00$ | توثيق أساليب جدولة المناوبات والقيادة الإكلينيكية كنماذج قياسية وتطبيقها على بقية الأقسام. |

---

## 🕸️ 6. شبكة المعرفة الدلالية (Knowledge Graph — `knowledge_graph.py`)

يبني النظام شبكة علاقات موجهة (`networkx.DiGraph`) تتغير ديناميكياً بناءً على مخرجات محرك القواعد وبيانات المستشفى:

### 1. أنواع العقد ولوحة الألوان (Node Types & Palette):
- 🔷 **Department (`#4e9af1`):** الأقسام الطبية الأربعة.
- 🟨 **Role (`#f1c94e`):** الوظائف الطبية (أطباء، تمريض، مساعدو تمريض).
- 🟪 **Demographic (`#e879f9`):** الفئات العمرية (أطفال، بالغون، مسنون).
- 🟩 **Hospital Event (`#4ecdc4`):** أحداث المستشفى (إنفلونزا، إضراب، تبرع).
- 🔴 **Rule Conclusion (`#f87171`):** الاستنتاجات الناتجة عن القواعد.
- 🟪 **Severity Rank (`#c084fc`):** مستويات الخطورة (Critical, High, Medium, Low).
- 🟢 **Operational Metric (`#34d399`):** مؤشرات الضغط والإشغال العالي.

### 2. أنواع العلاقات الموجهة (Directed Edges):
- `Department ──[HAS_STAFF_ROLE]──> Role`
- `Department ──[SERVES_DEMOGRAPHIC]──> Demographic`
- `Department ──[EXPERIENCED_EVENT]──> Event`
- `Event ──[IMPACTS]──> Department`
- `Department ──[TRIGGERED]──> Conclusion` *(يحمل عدد التكرارات `occurrences` ومستوى الخطورة)*
- `Conclusion ──[HAS_SEVERITY]──> Severity`
- `Department ──[HAS_METRIC]──> Metric`

### 3. طرق العرض الجزئي التفاعلي (Subgraph Modes):
- **🌐 Full Network:** عرض الشبكة الدلالية الكاملة.
- **⚠️ Vulnerabilities:** إبراز الأقسام المرتبطة بالاستنتاجات الحرجة والعالية فقط.
- **👥 Staffing:** إبراز توزيع الطواقم والوظائف ومعنويات العمل.
- **⚡ Events:** استعراض تأثير الأزمات والأحداث الطارئة على الأقسام.
- **👶 Demographics:** استعراض الفئات العمرية وتوزيع المرضى.

### 4. التحليل الشبكي ومؤشر الخطورة (Graph Analytics):
- **Degree Centrality:** تحديد العقد المركزية الأكثر تأثيراً وتأثراً في المستشفى.
- **Vulnerability Index:** حساب مؤشر الخطورة التشغيلية لكل قسم بوزن تكرارات الأزمات:
$$\text{Vulnerability Score} = \sum (\text{Critical} \times 4 + \text{High} \times 3 + \text{Medium} \times 2 + \text{Low} \times 1) \times \text{Occurrences}$$
*الترتيب الناتج في البيانات:* $\text{Emergency (541)} > \text{General Medicine (222)} > \text{Surgery (125)} > \text{ICU (93)}$.

---

## 🖥️ 7. الواجهة الرسومية (GUI Application — `gui_app.py`)

واجهة سطح مكتب تفاعلية مبنية بالكامل باستخدام `tkinter` مع تضمين مكتبة `matplotlib` عبر `FigureCanvasTkAgg` بتصميم داكن احترافي (Dark Theme) يدعم 5 مراحل متسلسلة عبر شريط جانبي (Sidebar Navigation):

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🏥 Hospital KMS — Knowledge Management System           [▶ Run Full KMS Cycle] [📂 Set Data]   │
├──────────────┬─────────────────────────────────────────────────────────────────────────────────┤
│ KMS PHASES   │ CONTENT AREA (Tab View)                                                         │
│              │                                                                                 │
│ 📥 Phase 1   │ [📥 Data Acquisition]                                                           │
│ Data Acq     │ Summary Cards + Interactive Table Explorer (Search, Filter, Pagination)         │
│              │                                                                                 │
│ 🗂️ Phase 2   │ [🗂️ Knowledge Representation]                                                   │
│ Facts Base   │ [Build Facts] -> Structured Fact Extraction (Services, Staff, Demographics)     │
│              │                                                                                 │
│ 🧠 Phase 3   │ [🧠 Reasoning & Expert System]                                                  │
│ Rule Engine  │ Severity Badges + Treeview Results + Multi-Filters (Severity, Department, Search)│
│              │                                                                                 │
│ 🕸️ Phase 4   │ [🕸️ Knowledge Graph Visualization]                                             │
│ Graph Visual │ Embedded Interactive Canvas + Subgraph Filter + Zoom Toolbar + Insights Panel   │
│              │                                                                                 │
│ 📊 Phase 5   │ [📊 Evaluation & Executive Dashboard]                                           │
│ Evaluation   │ Department Performance Matrix + Event Analysis + KMS Audit + Action Plan        │
├──────────────┴─────────────────────────────────────────────────────────────────────────────────┤
│ Ready — Click 'Load Data' or 'Run Full KMS Cycle' to begin.                                    │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### مميزات الواجهة:
1. **Interactive Dataset Explorer:** استعراض أي من الملفات الأربعة مع شريط بحث حي وتصفح الصفوف.
2. **Dynamic Badges & Color Coded Treeviews:** تلوين النتائج تلقائياً حسب مستوى الخطورة (أحمر، برتقالي، أصفر، أخضر).
3. **Embedded Graph Controls:** تكبير وتصغير وتحريك الجراف داخل النافذة دون الحاجة لنوافذ خارجية.
4. **Sequential Full Pipeline:** زر `▶ Run Full KMS Cycle` يقوم بتنفيذ المراحل الخمس في الخلفية (Multi-threaded) دون تجميد الواجهة.

---

## 🛠️ 8. المتطلبات التقنية وطريقة التشغيل (Setup & Execution)

### المتطلبات الأساسية (Prerequisites):
- **Python 3.10+**
- المكتبات المطلوبة في `requirements.txt`:
  ```txt
  pandas>=2.0
  networkx>=3.0
  matplotlib>=3.7
  ```

### خطوات التثبيت والتشغيل:
1. تثبيت الحزم المطلوبة:
   ```powershell
   pip install -r requirements.txt
   ```
2. تشغيل النظام:
   ```powershell
   python main.py
   ```
3. يمكنك أيضاً تمرير مسار مجلد بيانات مخصص عبر الـ CLI:
   ```powershell
   python main.py --data-dir "path/to/dataset"
   ```

---

## ✅ 9. معايير القبول والتحقق (Acceptance Criteria Checklist)

- [x] تشغيل `main.py` يفتح الواجهة الرسومية التفاعلية بسلاسة وبدون أي أخطاء.
- [x] محرك الاستدلال `expert_system.py` يعمل بقواعد حقيقية مبنية على الحقائق المستخرجة من البيانات.
- [x] الـ Knowledge Graph يتغير ويُبنى ديناميكياً وفق نتائج استدلال النظام الخبير.
- [x] الرسم البياني للجراف يظهر مدمجاً داخل نافذة `tkinter` مباشرة مع شريط تحكم كامل.
- [x] تمثيل دورة حياة إدارة المعرفة (KMS Life-Cycle) بمراحلها الخمس بوضوح ودقة عالية.
