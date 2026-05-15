# THREE-SHEET FARM ASSESSMENT DATA COLLECTION
## "See → Ask → Select" Principle (No Free Text, No Calculations)

---

## SHEET 1: FARMER PROFILE & LOCATION 👤📍
**Goal:** Establish farmer identity and precise location

### Content Flow:
1. **Farmer Details** 👤
   - Full name (text input)
   - Household size (options: 1-2, 3-5, 6-8, 9+)
   - Belongs to group? (yes/no → conditional name field)

2. **Farm Location** 📍
   - GPS auto-capture (button to capture coordinates)
   - Location name verification (read-only, auto-filled from GPS)
   - Land ownership (options: Own, Family, Rented, Community)

**Data Quality Check:** GPS is required before proceeding

---

## SHEET 2: FARM ASSESSMENT 🌳💨
**Goal:** Capture observational farm data (no calculations)

### Content Flow:
1. **Farm Size** 📏
   - Visual estimation (Small <2 acres, Medium 2-5 acres, Large >5 acres)

2. **Cocoa Trees** 🌳
   - Age observation (Young, Mature, Old)

3. **Shade Trees** 🌴 [CARBON CRITICAL]
   - Presence observation (None, Few, Many)
   - Types if present (Fruit, Timber, Mixed) → conditional

4. **Fertilizer Use** 💧
   - Uses fertilizer? (Yes/No) → conditional
   - Application method if yes (By hand, With machine)

5. **Farm Burning** 🔥
   - Waste burning frequency (Never, Sometimes, Often)

6. **Training & Practices** 🌱
   - Agroforestry practice? (Yes/No)
   - Received training? (Yes/No)
   - Plants trees? (Yes/No)

**Data Quality Check:** All fields use categories, no free text

---

## SHEET 3: VERIFICATION & EVIDENCE ✅📸🎤
**Goal:** Strengthen MRV (Monitoring, Reporting, Verification)

### Content Flow:
1. **Production** 🍫
   - Last harvest in bags (0-5, 6-10, 11-20, 21+)
   - Comparison to last year (More, Same, Less)

2. **Photo Evidence** 📸 [REQUIRED]
   - Photo of farmer (required)
   - Photo of farm (required)
   - Photo of cocoa trees (optional)
   - Photo of shade trees (optional)

3. **Voice Note** 🎤 [OPTIONAL]
   - Audio file with observations

4. **Validation Notes** 📝
   - Flag anomalies (e.g., "No shade trees but claims agroforestry")
   - System flags these for admin review

**Data Quality Check:** Photos required, validation notes flagged

---

## KEY DESIGN PRINCIPLES IMPLEMENTED

### ✅ "See → Ask → Select"
- **Observe first** (farm size, tree age, shade presence)
- **Ask conversational questions** ("How many bags?" not "kg/hectare")
- **Select from predefined options** (no free text except names)

### ✅ Conditional Logic (Progressive Disclosure)
- Group name field only shows if farmer says "yes"
- Fertilizer application method only shows if "uses fertilizer = yes"
- Shade tree types only shows if "has shade trees ≠ none"

### ✅ Observational Categories (Not Exact Numbers)
- "Small/Medium/Large farm" instead of "Enter hectares"
- "Young/Mature/Old trees" instead of "Enter tree height"
- "Few/Many shade trees" instead of "Count trees"

### ✅ Built-in Validation
- GPS capture is enforced (form won't submit without it)
- Photos are required for submission
- Anomalies are flagged for admin review
- Sequential sheets prevent incomplete submissions

### ✅ Mobile-Friendly
- Responsive design for tablets/phones
- GPS auto-capture via browser's geolocation API
- Photo upload on mobile devices

---

## DATA COLLECTION WORKFLOW

**Field Agent Actions:**
1. Open agent dashboard
2. See list of approved farmers
3. Click "📋 Collect Data" button for a farmer
4. **Sheet 1:** Enter profile & GPS location (5 min)
5. **Sheet 2:** Observe farm (visual estimation, 10 min)
6. **Sheet 3:** Take photos & submit (5 min)
7. System creates assessment records linked to farmer

**Backend Processing:**
- Form data stored in three separate models (Sheet1, Sheet2, Sheet3)
- Categories automatically mapped to numeric values for calculations
- Admin can view, validate, and flag anomalies
- Data ready for emissions factor calculations and reporting

---

## DATA INTEGRITY & SCALABILITY

✅ **No Free Text** (except names) → Reduces typos & inconsistencies
✅ **Observations Over Memory** → Higher accuracy
✅ **Photo Evidence** → Traceability for NGO/carbon credits
✅ **Progressive Disclosure** → Prevents form fatigue
✅ **GPS Lock-in** → Prevents false location claims
✅ **Offline Capable** → Can work with ODK Collect integration later

---

## URL ROUTES

```
/agent/assessment/<farmer_id>/sheet1/   → Sheet 1: Profile & Location
/agent/assessment/<farmer_id>/sheet2/   → Sheet 2: Farm Assessment  
/agent/assessment/<farmer_id>/sheet3/   → Sheet 3: Verification & Evidence
```

All routes protected: Only field agents can access data collection.

---

## TEMPLATE PATTERN: AVOID CSS "PROPERTY VALUE EXPECTED" FALSE POSITIVES

When using Django templates, do **not** place template expressions directly inside inline CSS values like `style="width: {{ value }}%;"`.
Many editors parse HTML/CSS before template rendering and report false CSS errors.

### Recommended Pattern

1. Store dynamic numbers in `data-*` attributes in template markup.
2. Apply the actual CSS style in JavaScript on page load.
3. Clamp values for safety (e.g., `0..100` for percentages).

### Example

Template markup:

```html
<div class="bar"><span data-width-pct="{{ row.yield_bar }}"></span></div>
```

Client-side application:

```html
<script>
function applyTemplateBarWidths() {
   document.querySelectorAll('[data-width-pct]').forEach((el) => {
      const raw = parseFloat(el.getAttribute('data-width-pct') || '0');
      const safe = Number.isFinite(raw) ? Math.max(0, Math.min(100, raw)) : 0;
      el.style.width = `${safe}%`;
   });
}

window.addEventListener('load', applyTemplateBarWidths);
</script>
```

### Quick Rule

- Use template tags in text, attributes, and data attributes.
- Avoid template tags inside raw CSS value strings whenever possible.
