# Solid AI

**Solid AI** is the practical GUI/application layer we are building on top of the pinned `q3ds-solidworks-mcp` SolidPilot backend.

## هدف پروژه

این repository برای رسیدن سریع به یک vertical slice واقعی ساخته شده است:

```text
Natural-language request / CAD file
                ↓
           Solid AI GUI
                ↓
      AI / planning adapter
                ↓
      SolidPilot (pinned)
                ↓
    deterministic CAD execution
                ↓
         SolidWorks COM
                ↓
      LIVE SolidWorks model
                ↓
          evidence / status
```

هدف مرحله اول، ساخت یک محیط عملی است که بتوانیم در آن به‌جای توسعه‌ی انتزاعی و طولانی، رفتار واقعی SolidWorks را با نمونه‌های مهندسی بررسی کنیم.

## مرحله اول محصول

GUI باید حداقل این جریان‌ها را ارائه کند:

1. ورود prompt مهندسی و اجرای آن از مسیر SolidPilot.
2. مشاهده‌ی وضعیت backend و اتصال زنده به SolidWorks.
3. باز کردن/ارسال فایل CAD و اجرای عملیات اصلاحی کنترل‌شده.
4. نمایش وضعیت plan → execution → verification و خطاهای واقعی.
5. نگه‌داشتن یک مسیر توسعه‌ی کوچک و قابل آزمایش برای اضافه کردن capabilityهای بعدی.

### نمونه‌ی هدف

```text
«یک براکت موتور با ضخامت 6 mm، چهار سوراخ M8 و جنس مشخص بساز.»
```

در نسخه‌های بعدی، لایه‌ی engineering reasoning می‌تواند الزاماتی مانند جنس، بار، ضریب اطمینان و قیود ساخت را به یک طراحی قابل اجرا تبدیل کند. GUI نباید وانمود کند که این بخش‌ها تا وقتی واقعاً پیاده و verified نشده‌اند، کامل هستند.

## ساختار repository

```text
Solid_Ai/
├── vendor/
│   └── q3ds-solidworks-mcp/   # pinned SolidPilot backend (git submodule)
├── gui/                       # GUI application layer
├── app/                       # local orchestration / AI adapters (future)
├── tests/                     # Solid AI integration tests
├── docs/                      # product and integration decisions
└── README.md
```

## چرا SolidPilot به‌صورت submodule نگه داشته شده است؟

SolidPilot یک backend تخصصی و مستقل برای اجرای deterministic عملیات SolidWorks است. به‌جای کپی‌کردن و diverge کردن سورس آن، این repository یک commit مشخص از آن را pin می‌کند تا:

- نسخه‌ی backend دقیقاً قابل تکرار باشد؛
- GUI و application logic از upstream جدا بماند؛
- تغییرات backend به‌صورت صریح و قابل review وارد شوند؛
- بتوانیم بعداً seamهای لازم را بدون ساختن bridge یا compiler موازی توسعه دهیم.

نسخه‌ی pin‌شده در `.gitmodules` ثبت شده و هنگام clone باید submodule نیز دریافت شود.

## وضعیت فعلی و مرزهای صداقت فنی

این پروژه هنوز یک محصول کامل text-to-CAD نیست.

SolidPilot در حال حاضر abstractionهای semantic، Feature Graph/IR، compiler deterministic، execution service، تحلیل مدل و قابلیت‌های مربوط به drawing را فراهم می‌کند. اما بعضی مسیرهای forwardِ کاملاً عمومی، مخصوصاً تبدیل آزاد prompt مهندسی به یک تراکنش کامل Feature Graph، هنوز محدودیت‌ها و workهای باقیمانده دارند.

بنابراین milestone اول ما **اثبات یک جریان واقعی و مشاهده‌پذیر** است، نه ادعای autonomous engineering کامل.

## پیش‌نیازهای backend

جزئیات دقیق محیط SolidPilot داخل زیرپروژه‌ی `vendor/q3ds-solidworks-mcp` نگه داشته می‌شود. در سطح سیستم انتظار می‌رود محیطی داشته باشیم که:

- Windows 10/11؛
- SOLIDWORKS نصب و licensed؛
- Python 3.x مطابق requirements backend؛
- .NET Framework 4.8.1 برای execution service؛
- دسترسی محلی به SolidWorks COM؛

را پشتیبانی کند.

قبل از اجرای GUI، ابتدا backend باید مستقل از GUI health-check شود.

## ترتیب توسعه

```text
Milestone 0
  pinned SolidPilot + repository bootstrap

Milestone 1
  local GUI shell + backend health/status

Milestone 2
  prompt → supported SolidPilot operation → LIVE SolidWorks

Milestone 3
  CAD file → inspect → controlled edit → LIVE SolidWorks

Milestone 4
  verification/evidence panel

Milestone 5
  expand missing CAD capabilities one by one

Milestone 6
  add the engineering-reasoning pieces from Ai_Designer where real gaps justify them
```

## رابطه با Ai_Designer

`Ai_Designer` پروژه‌ی معماری سطح بالاتر برای Autonomous Engineering باقی می‌ماند.

`Solid_Ai` عمداً یک مسیر عملی و محصول‌محور برای اعتبارسنجی رابط و backend است:

```text
Ai_Designer
    = requirements + engineering intent + planning + orchestration + recovery

Solid_Ai
    = practical GUI + local AI/CAD interaction + SolidPilot integration

SolidPilot
    = deterministic CAD backend + SolidWorks execution
```

هیچ compiler، COM bridge، topology engine یا reference resolver موازی در `Solid_Ai` ساخته نمی‌شود مگر اینکه کمبود آن با evidence اثبات شود.

## License / provenance

`vendor/q3ds-solidworks-mcp` یک پروژه‌ی upstream مستقل با مجوز **AGPL-3.0** است. `Solid_Ai` باید notice و الزامات license آن backend را حفظ کند. GUI و application code جدید باید با این مرز licensing به‌صورت آگاهانه توسعه داده شوند.

See `UPSTREAM_Q3DS.md` for the pinned source and provenance details.
