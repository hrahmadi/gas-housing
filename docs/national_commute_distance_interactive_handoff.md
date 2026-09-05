# Handoff — آزمایش ذهنی افزایش فاصله تا محل کار

## تصمیم نهایی

این تعامل به عنوان **آزمایش ذهنی مقیاس ملی** به مقاله اضافه شود و جایگزین نسخه پیچیده قبلی شود.

هدف فقط نشان دادن یک رابطه ساده است:

> **فاصله بیشتر تا محل کار × میلیون ها شاغل = مصرف سوخت بیشتر**

این شکل قرار نیست مصرف واقعی بنزین ناشی از رفت وآمد شغلی را برآورد کند و قرار نیست ادعا کند که همه شاغلان واقعا چنین جابه جایی ای را تجربه کرده اند. این یک سناریوی ساده برای نشان دادن **مقیاس اثر تجمعی فاصله** است.

---

# 1. ایده روایی

سال ۱۴۰۰ را به عنوان نقطه شروع فرض می کنیم.

فرض های سناریو:

- ایران **۲۴.۸ میلیون شاغل** دارد.
- مصرف روزانه بنزین کشور در نقطه شروع **۸۸ میلیون لیتر در روز** است.
- در سال اول، شاغلان نسبت به سال های بعد نزدیک تر به محل کار خود هستند.
- هر سال، فاصله خانه تا محل کار برای هر شاغل **X کیلومتر در هر طرف** بیشتر می شود.
- بنابراین افزایش فاصله رفت وبرگشت روزانه برابر است با **۲X کیلومتر**.
- خودرو به طور متوسط **۹ لیتر در ۱۰۰ کیلومتر** مصرف می کند.
- در نسخه اول فرض می کنیم **۱۰۰٪ شاغلان** این فاصله اضافه را تجربه می کنند.

کاربر فقط مقدار **فاصله اضافه سالانه** را انتخاب می کند.

---

# 2. تعامل اصلی

## عنوان

### اگر مردم هر سال کمی دورتر از محل کارشان زندگی کنند، مصرف بنزین چه می شود؟

زیرعنوان:

> یک آزمایش ذهنی با ۲۴.۸ میلیون شاغل

توضیح کوتاه:

> فرض کنیم مصرف بنزین در سال ۱۴۰۰ حدود ۸۸ میلیون لیتر در روز باشد. حالا هر سال محل زندگی شاغلان کمی دورتر از محل کارشان قرار بگیرد.

---

# 3. تنها کنترل کاربر

### فاصله اضافه در هر طرف

کنترل به صورت چیپ یا اسلایدر:

**۵ km | ۱۰ km | ۱۵ km | ۲۰ km**

پیش فرض:

**۱۰ km**

توضیح زیر کنترل:

> یعنی در هر سال، خانه به طور متوسط ۱۰ کیلومتر از محل کار دورتر می شود؛ ۲۰ کیلومتر رفت وبرگشت در روز.

**فقط همین یک کنترل را نشان بده.**

در این نسخه هیچ کنترل مستقیمی برای درصد شاغلان، مصرف خودرو، تعداد روز کاری یا قیمت بنزین وجود ندارد.

---

# 4. خط زمانی

محور افقی:

**۱۴۰۰ → ۱۴۰۱ → ۱۴۰۲ → ۱۴۰۳ → ۱۴۰۴ → ۱۴۰۵**

نقطه شروع:

**۸۸ میلیون لیتر در روز**

در هر سال، فاصله اضافه جمع می شود.

مثلا اگر کاربر **۱۰ km** انتخاب کند:

| سال | فاصله اضافه یک طرفه نسبت به ۱۴۰۰ | فاصله اضافه رفت وبرگشت روزانه | مصرف سناریویی |
|---|---:|---:|---:|
| ۱۴۰۰ | ۰ km | ۰ km | ۸۸.۰ میلیون L/day |
| ۱۴۰۱ | ۱۰ km | ۲۰ km | ۱۳۲.۷ میلیون L/day |
| ۱۴۰۲ | ۲۰ km | ۴۰ km | ۱۷۷.۴ میلیون L/day |
| ۱۴۰۳ | ۳۰ km | ۶۰ km | ۲۲۲.۰ میلیون L/day |
| ۱۴۰۴ | ۴۰ km | ۸۰ km | ۲۶۶.۷ میلیون L/day |
| ۱۴۰۵ | ۵۰ km | ۱۰۰ km | ۳۱۱.۴ میلیون L/day |

این اعداد با فرض ۲۴.۸۲۲ میلیون شاغل و مصرف ۹ لیتر در ۱۰۰ کیلومتر محاسبه شده اند.

---

# 5. محاسبه

در هر سال:

```text
additional round-trip distance
= selected km × 2 × years since 1400
```

و:

```text
additional gasoline/day
= 24.822m workers × additional round-trip km × 9/100
```

**در این نسخه، برای سادگی، اثر به صورت «روزانه» نمایش داده می شود و فرض می کنیم رفت وآمد در همه روزهای سال انجام می شود.**

اگر توسعه دهنده بخواهد با ۲۲ روز کاری در ماه و میانگین سالانه مقایسه کند، این باید به صورت روش شناسی جداگانه انجام شود؛ برای این تعامل نسخه ساده تر ترجیح داده می شود تا رابطه بصری پیچیده نشود.

نکته: با این تعریف، اعداد بالا دقیقا از رابطه ساده فوق به دست می آیند. بنابراین +۱۰ km/year برای ۱۴۰۱ برابر ۲۰ km رفت وبرگشت × ۲۴.۸۲۲m × ۰.۰۹ = **۴۴.۷ میلیون لیتر اضافه در روز** و در نتیجه ۱۳۲.۷m total.

---

# 6. هدف اصلی visualization

نمودار باید یک خط پایه و یک خط سناریو داشته باشد.

### خط پایه

**مصرف پایه: ۸۸ میلیون لیتر در روز**

این خط در تمام سال ها ثابت می ماند.

### خط سناریو

با تغییر کنترل فاصله، خط سناریو از ۸۸ شروع می شود و هر سال بالاتر می رود.

مثلا برای +۱۰ km/year:

**۸۸ → ۱۳۳ → ۱۷۷ → ۲۲۲ → ۲۶۷ → ۳۱۱**

در هر نقطه، مقدار سال و مصرف نمایش داده شود.

---

# 7. مقایسه با واقعیت

پس از نمودار، یک annotation کوچک نشان بده:

> **مصرف واقعی بنزین ایران در سال های اخیر حدود ۱۲۰ تا ۱۳۰ میلیون لیتر در روز بوده است.**

در صورت استفاده از خط مرجع فعلی پروژه، مقدار **۱۲۹ میلیون لیتر در روز** می تواند به عنوان reference line جداگانه نمایش داده شود.

این خط نباید به عنوان ادامه سناریو خوانده شود.

بهترین treatment:

- baseline scenario = ۸۸
- scenario line = رشد بر اساس فاصله
- reference line = **مصرف واقعی ایران، حدود ۱۲۹ میلیون لیتر در روز**

این کار به خواننده اجازه می دهد ببیند سناریو در چه نقطه ای از مقیاس واقعی کشور قرار می گیرد.

---

# 8. Caption / disclaimer

زیر شکل:

> **آزمایش ذهنی:** فرض شده است ۲۴.۸ میلیون شاغل کشور در سال ۱۴۰۰ به طور متوسط نزدیک محل کار خود هستند و هر سال، به ازای سناریوی انتخاب شده، فاصله خانه تا محل کار آنها بیشتر می شود. مصرف سوخت با فرض ۹ لیتر در ۱۰۰ کیلومتر محاسبه شده است. این نمودار پیش بینی مصرف واقعی بنزین یا سهم واقعی رفت وآمد شغلی نیست؛ هدف آن نشان دادن مقیاس اثر تجمعی فاصله است.

---

# 9. Important editorial wording

**Use:**

> «مصرف سناریویی»

> «بنزین مورد نیاز در این سناریو»

> «فاصله اضافه»

> «آزمایش ذهنی»

**Do not use:**

> «مصرف واقعی ناشی از مسکن»

> «میزان واقعی مصرف رفت وآمد شاغلان»

> «این مقدار بنزین به دلیل گرانی مسکن مصرف می شود»

The interaction demonstrates scale, not causality.

---

# 10. Suggested visual composition

## Header

**اگر مردم هر سال کمی دورتر از محل کارشان زندگی کنند، مصرف بنزین چه می شود؟**

small subtitle:

> ۲۴.۸ میلیون شاغل · نقطه شروع: ۸۸ میلیون لیتر در روز

## Control

### فاصله اضافه در هر طرف، در هر سال

`۵ km | ۱۰ km | ۱۵ km | ۲۰ km`

selected value should be visually dominant.

## Chart

Large line chart.

Y-axis:

**میلیون لیتر در روز**

X-axis:

**۱۴۰۰ تا ۱۴۰۵**

Two/three lines:

1. muted baseline at 88
2. highlighted scenario line
3. optional muted reference at 129 actual national consumption

Do not overload the chart with additional series.

## Dynamic headline

At the selected year, show:

> **۱۴۰۵: ۳۱۱ میلیون لیتر در روز**

and below:

> **۲۲۳ میلیون لیتر بیشتر از نقطه شروع**

This should be the strongest visual number after the chart itself.

---

# 11. Animation

On first viewport entry:

1. Start at ۱۴۰۰ / ۸۸ million.
2. Draw the scenario line year by year.
3. Stop at ۱۴۰۵.
4. Highlight the selected year's endpoint.

Changing the distance chip should redraw the scenario line smoothly.

No elaborate worker animations are needed.

The chart itself is the interaction.

For `prefers-reduced-motion`, render the selected scenario immediately.

---

# 12. Why we are using 100% of workers in version 1

The initial version intentionally avoids a second percentage control.

The thought experiment asks:

> **«اگر این فاصله برای همه شاغلان اتفاق بیفتد، فقط برای دیدن مقیاس اثر چه می شود؟»**

This is intentionally a simple upper-bound-style thought experiment, not a claim about actual behavior.

If the result feels too extreme, the article can explicitly explain that the entire workforce assumption is deliberately unrealistic and is being used to show the mathematical scale.

A later version could introduce an affected-share sensitivity, but it should not be part of the first UI.

---

# 13. Relationship to Figure 2 and the housing story

The old standalone Tehran affordability Figure 2 is no longer necessary if this interaction incorporates the useful logic from it into the article narrative.

The article should explain the causal chain in prose:

**افزایش هزینه مسکن**

→ خانه قابل پرداخت از محل کار دورتر می شود

→ فاصله رفت وآمد بیشتر می شود

→ در مقیاس میلیون ها شاغل، فاصله اضافی می تواند به مقدار بزرگی از مصرف سوخت تبدیل شود

The national interaction does not attempt to model the first arrow numerically. It demonstrates the magnitude of the later relationship.

---

# 14. Transition into Parand

After this national thought experiment, move to the concrete case:

> «این فقط یک آزمایش ذهنی بود. برای دیدن اینکه چنین فاصله ای در زندگی واقعی چه شکلی دارد، یک مورد مشخص را بررسی کنیم: پرند.»

Then the Parand scene begins.

This makes Parand the **real-world example** and the national chart the **scale demonstration**.

---

# 15. Current data inputs

Use the project's existing assumptions/data:

```json
{
  "employedMillion": 24.822,
  "fuelLitresPer100km": 9,
  "baseline1400MillionLitresPerDay": 88,
  "comparisonCurrentMillionLitresPerDay": 129,
  "years": [1400, 1401, 1402, 1403, 1404, 1405],
  "distanceOptionsKmOneWayPerYear": [5, 10, 15, 20]
}
```

Precise source IDs remain in `data/sources.csv` / `data/assumptions.json`.

---

# 16. Implementation scope

Expected files:

- `index.html` — new national thought-experiment section
- `js/views.js` — `drawNationalCommuteScale()` and calculation helper
- `js/article.js` — boot wiring
- `css/style.css` — chart/control styles
- `data/assumptions.json` — existing national scenario values
- `data/data.js` — regenerated if assumptions structure changes
- `README.md` — figure status

No backend.

No new mapping library required.

Use the same charting/rendering conventions already established in the article.

---

# 17. Acceptance criteria

The reader should understand the interaction in approximately five seconds:

> **The farther workers are pushed from their jobs, the more gasoline the country would need if that extra distance applied across the workforce.**

The figure succeeds if:

- there is only one visible user control;
- the baseline starts clearly at ۸۸ million L/day in ۱۴۰۰;
- changing +5/+10/+15/+20 km visibly changes the slope of the scenario line;
- the years ۱۴۰۰–۱۴۰۵ remain readable;
- the current national level (~۱۲۹m L/day) can be compared without being confused with the scenario;
- the calculation remains clearly labeled as a thought experiment;
- there is no need to understand a formula to understand the visual argument.
