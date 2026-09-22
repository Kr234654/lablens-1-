"""
Finds lab values in the text of a blood report and checks them against reference ranges.

How it works:
1. The text is read line by line.
2. For each line we look for the name of a known test (TESTS below), then take the first number after the name.
3. If the report prints its own reference range on that line, we use it. Otherwise we use a standard adult range.
4. The value is marked normal, low or high.

The standard ranges are general adult ranges for education only. Labs use different ranges and units,
so the range printed on the report is always preferred.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

NUM = r"\d+(?:,\d{2,3})*(?:\.\d+)?"  # 13.5   7,400   2,45,000
NUM_RE = re.compile(NUM)
RANGE_RE = re.compile(rf"({NUM})\s*(?:-|–|—|to)\s*({NUM})", re.I)
UPPER_RE = re.compile(rf"(?:<=|<|≤|up to|upto|less than)\s*({NUM})", re.I)
LOWER_RE = re.compile(rf"(?:>=|>|≥|more than|greater than)\s*({NUM})", re.I)
# Lines that list several ranges at once (desirable / borderline / high). We do not trust a range from those.
MULTI_RANGE_WORDS = re.compile(r"desirable|borderline|optimal|near optimal|high risk|very high|prediab|diabet|normal:", re.I)

Range = Tuple[Optional[float], Optional[float]]


@dataclass(frozen=True)
class Test:
    key: str
    name: str
    group: str
    unit: str
    aliases: str  # regular expression for the names this test appears under
    lo: Optional[float]
    hi: Optional[float]
    about: str
    low_note: str = ""
    high_note: str = ""
    male: Optional[Range] = None
    female: Optional[Range] = None
    exclude: str = ""  # lines matching this are not this test
    other_unit: str = ""  # a different unit (for example mmol/L). We then trust only the report's own range.
    thousands: bool = False  # counts printed as 7.4 instead of 7400


def _t(*args, **kwargs) -> Test:
    return Test(*args, **kwargs)


# Order matters: more specific tests come first, so a line is used by the most specific test only.
TESTS: List[Test] = [
    _t("hba1c", "HbA1c", "Sugar", "%", r"hba1c|hb\s*a1c|glycated h\w*|glycosylated h\w*|\ba1c\b", 4.0, 5.6,
       "Your average blood sugar over the last 2 to 3 months.",
       low_note="A low HbA1c is uncommon and usually not a concern by itself. Some types of anemia can affect the result.",
       high_note="Higher values mean blood sugar has been above the usual range. 5.7 to 6.4% is often called prediabetes and 6.5% or more is often used to diagnose diabetes, but only a doctor can confirm this.",
       other_unit=r"mmol/mol"),
    _t("mchc", "MCHC", "Blood count", "g/dL", r"\bmchc\b|mean corpus\w* h\w+ conc\w*", 32, 36,
       "How concentrated hemoglobin is inside your red blood cells.",
       low_note="Can be seen with iron deficiency.",
       high_note="Can be a lab artefact or be seen with some red cell conditions. Discuss it with your doctor."),
    _t("mch", "MCH", "Blood count", "pg", r"\bmch\b|mean corpus\w* h(?:a)?emoglobin", 27, 32,
       "The average amount of hemoglobin in each red blood cell.",
       low_note="Often goes along with small red cells, for example in iron deficiency.",
       high_note="Often goes along with large red cells."),
    _t("mcv", "MCV", "Blood count", "fL", r"\bmcv\b|mean corpus\w* volume", 80, 100,
       "The average size of your red blood cells.",
       low_note="Small red cells are often seen with iron deficiency or thalassemia trait.",
       high_note="Large red cells can be seen with low vitamin B12 or folate, thyroid problems or alcohol use."),
    _t("hemoglobin", "Hemoglobin", "Blood count", "g/dL", r"h(?:a)?emoglobin|\bhgb\b|\bhb\b", 12.0, 17.0,
       "The protein in red blood cells that carries oxygen around the body.",
       low_note="Low hemoglobin is called anemia. Common causes are low iron, low vitamin B12 or folate, blood loss or long-term illness. Your doctor can find the cause.",
       high_note="High hemoglobin can be linked to dehydration, smoking, living at high altitude or, less often, a blood condition. A repeat test helps.",
       male=(13.0, 17.0), female=(12.0, 15.0), other_unit=r"g/l\b"),
    _t("esr", "ESR", "Blood count", "mm/hr", r"\besr\b|erythrocyte sedimentation", 0, 20,
       "A general marker of inflammation in the body.",
       high_note="A raised ESR is not specific. It can be seen with infection, inflammation or anemia and has to be read with other findings.",
       male=(0, 15), female=(0, 20)),
    _t("rbc", "Red blood cells (RBC)", "Blood count", "million/µL", r"\brbc\b|red blood cell|red cell count|erythrocyte count", 4.0, 5.5,
       "The cells that carry oxygen around the body.",
       low_note="Often goes along with low hemoglobin (anemia).",
       high_note="Can be linked to dehydration, smoking or high altitude.",
       male=(4.5, 5.5), female=(4.0, 5.0)),
    _t("wbc", "White blood cells (WBC)", "Blood count", "/µL", r"\bwbc\b|white blood cell|total leu[ck]ocyte count|\btlc\b", 4000, 11000,
       "Cells that fight infection.",
       low_note="Low counts can follow viral infections, some medicines or other causes. Counts that stay low should be checked.",
       high_note="High counts are common with infections, inflammation or stress. Your doctor will look at the full picture.",
       thousands=True),
    _t("platelets", "Platelets", "Blood count", "/µL", r"platelets?(?: count)?|\bplt\b", 150000, 450000,
       "Small cell fragments that help your blood clot.",
       low_note="Low platelets can be seen after viral infections, with some medicines or for other reasons. Very low counts need prompt medical care, especially with bleeding or bruising.",
       high_note="Can be seen with infection, inflammation or iron deficiency. Your doctor will decide if follow-up is needed.",
       exclude=r"mean platelet|\bmpv\b|distribution|\bpdw\b|plcr|crit", thousands=True),
    _t("hematocrit", "Hematocrit (PCV)", "Blood count", "%", r"h(?:a)?ematocrit|\bpcv\b|packed cell volume", 36, 50,
       "The share of your blood that is made up of red blood cells.",
       low_note="Usually moves together with hemoglobin. Low values can point to anemia.",
       high_note="Can be linked to dehydration or smoking.",
       male=(40, 50), female=(36, 46)),
    _t("glucose_fasting", "Fasting glucose", "Sugar", "mg/dL",
       r"fasting (?:blood )?(?:glucose|sugar)|\bfbs\b|\bfbg\b|glucose,? \(?fasting|blood sugar,? \(?fasting", 70, 99,
       "Sugar in your blood after not eating for at least 8 hours.",
       low_note="Low sugar can cause shakiness, sweating or dizziness. If you have these symptoms, tell your doctor.",
       high_note="Fasting values of 100 to 125 mg/dL are often called prediabetes, and 126 or more on repeat tests can point to diabetes. A doctor has to confirm this with repeat tests.",
       other_unit=r"mmol/l"),
    _t("glucose_random", "Random / after-meal glucose", "Sugar", "mg/dL",
       r"random (?:blood )?(?:glucose|sugar)|\brbs\b|post[\s-]?prandial|\bppbs\b|glucose,? \(?random", 70, 140,
       "Sugar in your blood measured at any time, or after a meal.",
       low_note="Low sugar can cause shakiness, sweating or dizziness. If you have these symptoms, tell your doctor.",
       high_note="Raised sugar after a meal or at random can be a sign of prediabetes or diabetes. Your doctor will usually confirm it with fasting tests.",
       other_unit=r"mmol/l"),
    _t("nonhdl", "Non-HDL cholesterol", "Cholesterol", "mg/dL", r"non[\s-]*hdl", 0, 130,
       "All the cholesterol in your blood except the 'good' HDL.",
       high_note="Higher values are linked to a higher long-term risk of heart disease.", other_unit=r"mmol/l"),
    _t("ldl", "LDL cholesterol", "Cholesterol", "mg/dL", r"\bldl\b|low density lipoprotein", 0, 100,
       "Often called 'bad' cholesterol. It can build up in artery walls.",
       high_note="LDL above target raises long-term heart risk. Diet, activity and sometimes treatment help. Your doctor sets the right target for you.",
       exclude=r"ratio", other_unit=r"mmol/l"),
    _t("hdl", "HDL cholesterol", "Cholesterol", "mg/dL", r"\bhdl\b|high density lipoprotein", 40, None,
       "Often called 'good' cholesterol. It helps remove other cholesterol.",
       low_note="Low HDL is linked to a higher heart risk. Regular exercise, not smoking and healthy fats can help raise it.",
       male=(40, None), female=(50, None), exclude=r"ratio", other_unit=r"mmol/l"),
    _t("vldl", "VLDL cholesterol", "Cholesterol", "mg/dL", r"\bvldl\b|very low density", 2, 30,
       "Particles in the blood that carry triglycerides.",
       high_note="Usually goes up along with triglycerides.", other_unit=r"mmol/l"),
    _t("triglycerides", "Triglycerides", "Cholesterol", "mg/dL", r"triglycerides?|\btg\b|\btrigs?\b", 0, 150,
       "A type of fat in your blood.",
       high_note="High triglycerides are linked to too much sugar, refined carbs or alcohol, weight gain and diabetes. Very high levels can affect the pancreas, so tell your doctor.",
       other_unit=r"mmol/l"),
    _t("total_chol", "Total cholesterol", "Cholesterol", "mg/dL", r"total cholesterol|cholesterol,? total|\bcholesterol\b", 0, 200,
       "The total amount of cholesterol in your blood.",
       high_note="Higher cholesterol raises the long-term risk of heart disease. Food, activity, weight and family history all matter. Your doctor can advise if changes or treatment are needed.",
       other_unit=r"mmol/l"),
    _t("creatinine", "Creatinine", "Kidney", "mg/dL", r"creatinine", 0.6, 1.3,
       "A waste product that the kidneys filter out.",
       low_note="Low values are usually not a concern and can be seen with low muscle mass.",
       high_note="A high level can mean the kidneys are filtering less than usual, or that you were dehydrated. A doctor should review it.",
       male=(0.7, 1.3), female=(0.6, 1.1), exclude=r"clearance|ratio|egfr", other_unit=r"µmol|umol"),
    _t("bun", "Blood urea nitrogen (BUN)", "Kidney", "mg/dL", r"blood urea nitrogen|\bbun\b", 7, 20,
       "A waste product from protein breakdown that the kidneys clear.",
       low_note="Usually not a concern. Can be seen with low protein intake or drinking a lot of water.",
       high_note="Can be raised by dehydration, a high-protein diet or reduced kidney function.", other_unit=r"mmol/l"),
    _t("urea", "Blood urea", "Kidney", "mg/dL", r"blood urea|\burea\b", 15, 40,
       "A waste product from protein breakdown that the kidneys clear.",
       low_note="Usually not a concern. Can be seen with low protein intake or drinking a lot of water.",
       high_note="Can be raised by dehydration, a high-protein diet or reduced kidney function.",
       exclude=r"nitrogen|\bbun\b", other_unit=r"mmol/l"),
    _t("uric_acid", "Uric acid", "Kidney", "mg/dL", r"uric acid", 2.6, 7.2,
       "A waste product that can form crystals in the joints.",
       low_note="Usually not a concern.",
       high_note="High uric acid can be linked to gout or kidney stones. Diet, water intake and weight all matter.",
       male=(3.5, 7.2), female=(2.6, 6.0), other_unit=r"µmol|umol"),
    _t("alt", "ALT (SGPT)", "Liver", "U/L", r"\balt\b|sgpt|alanine (?:amino)?transferase", 7, 56,
       "An enzyme found mostly in the liver.",
       high_note="A raised ALT can point to liver stress from fatty liver, alcohol, medicines or infection. Your doctor may repeat it or add other tests."),
    _t("ast", "AST (SGOT)", "Liver", "U/L", r"\bast\b|sgot|aspartate (?:amino)?transferase", 10, 40,
       "An enzyme found in the liver and in muscles.",
       high_note="Can be raised by liver stress, but also by heavy exercise or muscle injury."),
    _t("alp", "ALP", "Liver", "U/L", r"alkaline phosphatase|\balp\b", 44, 147,
       "An enzyme found in the liver and bones.",
       high_note="Can be seen with liver or bile duct problems or bone conditions. Growing children and pregnancy also raise it.",
       low_note="Usually not a concern by itself."),
    _t("bilirubin", "Total bilirubin", "Liver", "mg/dL", r"total bilirubin|bilirubin,? \(?total", 0.1, 1.2,
       "A yellow pigment made when red blood cells break down.",
       high_note="High bilirubin can make the skin or eyes look yellow. It can be harmless (for example Gilbert's syndrome) or point to liver or bile problems, so it should be reviewed.",
       other_unit=r"µmol|umol"),
    _t("albumin", "Albumin", "Liver", "g/dL", r"\balbumin\b", 3.5, 5.0,
       "The main protein in your blood, made by the liver.",
       low_note="Low albumin can be linked to poor nutrition, liver or kidney conditions or long-term illness.",
       high_note="Usually due to dehydration.",
       exclude=r"globulin|ratio|a/g|micro|urine|creatinine", other_unit=r"g/l\b"),
    _t("total_protein", "Total protein", "Liver", "g/dL", r"total protein", 6.0, 8.3,
       "Albumin and the other proteins in your blood.",
       low_note="Can be seen with poor nutrition or with liver or kidney conditions.",
       high_note="Can be seen with dehydration or long-term inflammation.", other_unit=r"g/l\b"),
    _t("sodium", "Sodium", "Electrolytes", "mmol/L", r"\bsodium\b", 135, 145,
       "A salt that controls water balance and nerve function.",
       low_note="Low sodium can come from drinking too much water, some medicines or medical conditions. Clearly low levels need prompt care.",
       high_note="Usually linked to not drinking enough fluids."),
    _t("potassium", "Potassium", "Electrolytes", "mmol/L", r"\bpotassium\b", 3.5, 5.1,
       "A mineral that keeps the heart and muscles working.",
       low_note="Can be caused by vomiting, diarrhea or some medicines. Low levels can affect the heart rhythm, so tell your doctor.",
       high_note="High potassium can affect the heart rhythm and needs a medical review soon, especially if you have kidney problems."),
    _t("calcium", "Calcium", "Electrolytes", "mg/dL", r"\bcalcium\b", 8.5, 10.5,
       "A mineral for bones, nerves and muscles.",
       low_note="Can be linked to low vitamin D or low albumin.",
       high_note="Can be linked to overactive parathyroid glands or too much vitamin D or calcium supplements.",
       exclude=r"ionized|ionised|urine|corrected", other_unit=r"mmol/l"),
    _t("tsh", "TSH", "Thyroid", "mIU/L", r"\btsh\b|thyroid stimulating hormone|thyrotropin", 0.4, 4.0,
       "A hormone that tells your thyroid how hard to work.",
       low_note="A low TSH often means the thyroid is overactive (hyperthyroidism). Your doctor may add T3 and T4 tests.",
       high_note="A high TSH often means the thyroid is underactive (hypothyroidism). Your doctor may add T3 and T4 tests."),
    _t("vit_d", "Vitamin D", "Vitamins & minerals", "ng/mL", r"vitamin d\d?\b", 30, 100,
       "A vitamin for bones and muscles, made in your skin from sunlight.",
       low_note="Low vitamin D is very common. It can affect bones and muscles. Sunlight, food and supplements prescribed by your doctor can help.",
       high_note="Very high values are usually from too many supplements. Talk to your doctor.", other_unit=r"nmol/l"),
    _t("b12", "Vitamin B12", "Vitamins & minerals", "pg/mL", r"vitamin b[\s-]*12|cobalamin|\bb12\b", 200, 900,
       "A vitamin for your nerves and red blood cells.",
       low_note="Low B12 can cause tiredness, tingling or anemia. It is common in vegetarians and with some medicines. Your doctor can advise food or supplements.",
       high_note="Often from supplements or injections.", other_unit=r"pmol/l"),
    _t("ferritin", "Ferritin", "Vitamins & minerals", "ng/mL", r"ferritin", 11, 336,
       "Shows how much iron your body has stored.",
       low_note="Low ferritin means low iron stores, even before anemia appears.",
       high_note="Can be raised by inflammation, liver problems or too much iron.",
       male=(24, 336), female=(11, 307)),
    _t("iron", "Serum iron", "Vitamins & minerals", "µg/dL", r"\biron\b|serum iron", 60, 170,
       "Iron that is circulating in your blood.",
       low_note="Can be seen with iron deficiency or blood loss.",
       high_note="Can come from iron supplements or, rarely, from iron overload.",
       exclude=r"binding|tibc|uibc|saturation|ferritin", other_unit=r"µmol|umol"),
]

TESTS_BY_KEY: Dict[str, Test] = {t.key: t for t in TESTS}
_COMPILED = [(t, re.compile(t.aliases, re.I), re.compile(t.exclude, re.I) if t.exclude else None,
              re.compile(t.other_unit, re.I) if t.other_unit else None) for t in TESTS]

# The order results are shown in (the TESTS list above is ordered for matching, not for display).
DISPLAY_ORDER = [
    "hemoglobin", "rbc", "hematocrit", "mcv", "mch", "mchc", "wbc", "platelets", "esr",
    "glucose_fasting", "glucose_random", "hba1c",
    "total_chol", "ldl", "hdl", "nonhdl", "vldl", "triglycerides",
    "creatinine", "bun", "urea", "uric_acid",
    "alt", "ast", "alp", "bilirubin", "albumin", "total_protein",
    "tsh", "vit_d", "b12", "ferritin", "iron", "sodium", "potassium", "calcium",
]
GROUP_ORDER = ["Blood count", "Sugar", "Cholesterol", "Kidney", "Liver", "Thyroid", "Vitamins & minerals", "Electrolytes"]


def _num(text: str) -> float:
    return float(text.replace(",", ""))


def _clean_line(line: str) -> str:
    line = re.sub(r"25[\s-]*(?:oh|hydroxy)", "", line, flags=re.I)  # "25-OH Vitamin D": the 25 is not the result
    line = re.sub(r"\b\d(?:st|nd|rd|th)\b", "", line, flags=re.I)  # "3rd generation"
    return line


def _range_for(test: Test, sex: Optional[str]) -> Range:
    if sex == "male" and test.male:
        return test.male
    if sex == "female" and test.female:
        return test.female
    return (test.lo, test.hi)


def find_tests_in_text(text: str) -> List[str]:
    """Which known tests does this piece of text talk about? Used by the follow-up chat."""
    found = []
    for test, alias, exclude, _ in _COMPILED:
        if alias.search(text) and (not exclude or not exclude.search(text)) and test.key not in found:
            found.append(test.key)
    return found


def assess(value: float, lo: Optional[float], hi: Optional[float]) -> Tuple[str, str]:
    """Returns (status, severity). Severity says how far outside the range the value is."""
    status, distance = "normal", 0.0
    if lo is not None and value < lo:
        status, distance = "low", (lo - value) / max(abs(lo), 1e-9)
    elif hi is not None and value > hi:
        status, distance = "high", (value - hi) / max(abs(hi), 1e-9)
    if status == "normal":
        return status, "normal"
    if distance <= 0.10:
        return status, "mild"
    if distance <= 0.30:
        return status, "moderate"
    return status, "marked"


def parse_report(text: str, sex: Optional[str] = None) -> List[dict]:
    """Find lab values in the text. Returns one dict per test found (first occurrence only)."""
    results: Dict[str, dict] = {}

    for raw_line in text.splitlines():
        line = _clean_line(raw_line.strip())
        if len(line) < 3:
            continue

        for test, alias, exclude, other_unit in _COMPILED:
            if test.key in results:
                continue
            match = alias.search(line)
            if not match or (exclude and exclude.search(line)):
                continue

            rest = line[match.end():]
            value_match = NUM_RE.search(rest)
            if not value_match:
                continue
            value = _num(value_match.group())
            after = rest[value_match.end():]

            # A range printed on the report beats our standard range.
            report_range: Optional[Range] = None
            if not MULTI_RANGE_WORDS.search(line):
                m = RANGE_RE.search(after)
                if m and _num(m.group(1)) < _num(m.group(2)):
                    report_range = (_num(m.group(1)), _num(m.group(2)))
                else:
                    up, low = UPPER_RE.search(after), LOWER_RE.search(after)
                    if up:
                        report_range = (None, _num(up.group(1)))
                    elif low:
                        report_range = (_num(low.group(1)), None)

            # Counts printed as 7.4 (thousands) or in lakhs
            if test.thousands:
                factor = 100000 if re.search(r"lakh", line, re.I) else (1000 if value < 1000 else 1)
                value *= factor
                if report_range and factor == 1000 and (report_range[1] or 0) < 1000:
                    report_range = tuple(None if x is None else x * 1000 for x in report_range)  # type: ignore

            unit, unit_differs = test.unit, False
            if other_unit:
                unit_match = other_unit.search(line)
                if unit_match:
                    unit, unit_differs = unit_match.group(), True

            if report_range:
                lo, hi = report_range
                source = "report"
            elif unit_differs:
                lo = hi = None  # a different unit: our standard range would be wrong
                source = "none"
            else:
                lo, hi = _range_for(test, sex)
                source = "standard"

            if source == "none":
                status, severity = "unknown", "normal"
            else:
                status, severity = assess(value, lo, hi)

            note = {"low": test.low_note, "high": test.high_note}.get(status, "")
            if unit_differs and source == "none":
                note = "This value uses a different unit than usual, so compare it with the range printed on your report."

            results[test.key] = {
                "key": test.key,
                "name": test.name,
                "group": test.group,
                "value": value,
                "unit": unit,
                "low": lo,
                "high": hi,
                "range_source": source,
                "status": status,
                "severity": severity,
                "about": test.about,
                "note": note,
            }
            break  # this line belongs to one test only

    group_order = {name: i for i, name in enumerate(GROUP_ORDER)}
    return sorted(results.values(), key=lambda r: (group_order.get(r["group"], 99), DISPLAY_ORDER.index(r["key"])))
