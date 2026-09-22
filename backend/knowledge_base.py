"""
A small, hand-written knowledge base of general health-education notes.

This is the "corpus" for the app's retrieval-augmented generation (RAG) feature: each article is chunked
and indexed (see retrieval.py), and the most relevant chunks are retrieved for a question and given to the
LLM (or shown directly, in basic mode) as grounding, along with a citation.

Written for this project. General education only, not medical advice, and deliberately cautious:
no medicine names, doses or diagnoses.
"""

ARTICLES = [
    {
        "id": "anemia", "title": "Anemia and iron", "tags": ["hemoglobin", "rbc", "mcv", "mch", "ferritin", "iron"],
        "text": (
            "Anemia means your blood has fewer healthy red blood cells or less hemoglobin than usual, so it "
            "carries less oxygen around the body. Common signs are tiredness, pale skin, shortness of breath "
            "on exertion, or a fast heartbeat. The most common cause worldwide is low iron, often from a diet "
            "low in iron, heavy periods, or slow blood loss such as from the gut. Other causes include low "
            "vitamin B12 or folate, long-term illness, or inherited conditions such as thalassemia trait. "
            "Ferritin shows how much iron is stored in the body and is often checked alongside hemoglobin. "
            "Iron-rich foods include lentils, beans, leafy greens, dried fruit, and meat or eggs if eaten; "
            "vitamin C (such as citrus fruit or lemon) taken with a meal can help the body absorb iron from "
            "food. A doctor can test for the exact cause and advise on food or supplements, since taking "
            "iron without a clear reason is not recommended."
        ),
    },
    {
        "id": "b12_folate", "title": "Vitamin B12 and folate", "tags": ["b12", "vitamin b12", "folate"],
        "text": (
            "Vitamin B12 and folate are needed to make healthy red blood cells and to keep nerves working "
            "well. Low B12 is common in people who eat little or no animal food, in older adults, and with "
            "some digestive conditions that affect absorption. Signs of low B12 can include tiredness, "
            "tingling in the hands or feet, memory problems, or a sore tongue, though many people have no "
            "symptoms at all. Food sources of B12 include eggs, dairy, and meat or fish if eaten; those on a "
            "plant-based diet often need a fortified food or a supplement, ideally chosen with a doctor's "
            "advice. Folate is found in leafy greens, beans, and fortified cereals. Because B12 and folate "
            "deficiency can look similar and sometimes hide each other on a blood count, both are often "
            "checked together."
        ),
    },
    {
        "id": "vitamin_d", "title": "Vitamin D", "tags": ["vit_d", "vitamin d"],
        "text": (
            "Vitamin D helps the body absorb calcium and keeps bones and muscles healthy. Most of it is made "
            "in the skin from sunlight, with smaller amounts from food such as fatty fish, egg yolks, and "
            "fortified milk. Low vitamin D is very common, especially with limited sun exposure, darker skin, "
            "covering most of the skin outdoors, or spending most of the day indoors. It can contribute to "
            "bone or muscle aches, though many people with low levels feel nothing unusual. A short, regular "
            "time in sunlight on the arms or legs (being mindful of sunburn) can help, and a doctor can advise "
            "whether a supplement is a good idea and at what amount, since more is not always better."
        ),
    },
    {
        "id": "diabetes", "title": "Blood sugar and diabetes", "tags": ["glucose", "hba1c", "fasting glucose", "sugar"],
        "text": (
            "Fasting glucose measures blood sugar after not eating for several hours, while HbA1c reflects the "
            "average blood sugar over the past two to three months, so it is less affected by a single meal. "
            "Blood sugar rises when the body cannot use insulin effectively or does not make enough of it. "
            "Values above the usual range are sometimes called prediabetes or diabetes, but these labels "
            "always need a doctor to confirm with repeat testing rather than a single result. Everyday habits "
            "that support healthy blood sugar include limiting sugary drinks and refined carbohydrates, eating "
            "more vegetables, fibre and protein, staying active most days, and maintaining a healthy weight. "
            "These habits help most people, whether or not a result is currently out of range."
        ),
    },
    {
        "id": "cholesterol", "title": "Cholesterol and heart health", "tags": ["ldl", "hdl", "total_chol", "nonhdl", "cholesterol"],
        "text": (
            "Cholesterol is a fat-like substance the body needs, but too much of certain types can build up in "
            "artery walls over many years and raise the risk of heart disease. LDL cholesterol is often called "
            "'bad' cholesterol because high levels are linked to this build-up, while HDL is called 'good' "
            "cholesterol because it helps carry cholesterol away. Total cholesterol combines several types, so "
            "the individual values usually matter more than the total alone. Diet low in saturated and trans "
            "fat, more fibre (oats, beans, vegetables, fruit), regular activity, not smoking, and a healthy "
            "weight can all improve these numbers over weeks to months. Family history also plays a role, so "
            "a doctor looks at the whole picture, not one test result, when deciding what to do next."
        ),
    },
    {
        "id": "triglycerides", "title": "Triglycerides", "tags": ["triglycerides", "vldl"],
        "text": (
            "Triglycerides are the main form of fat stored in the body and carried in the blood, made from "
            "extra calories the body does not use right away, especially from sugar, refined carbohydrates and "
            "alcohol. High triglycerides are linked to a higher risk of heart disease and, when very high, to "
            "inflammation of the pancreas, so markedly raised results should be discussed with a doctor "
            "promptly. Levels can be lowered by cutting back on sugary drinks, refined carbs and alcohol, "
            "losing excess weight, and regular physical activity. Because a recent meal can temporarily raise "
            "this value, fasting before the test usually gives a more accurate picture."
        ),
    },
    {
        "id": "kidney", "title": "Kidney function", "tags": ["creatinine", "bun", "urea", "kidney"],
        "text": (
            "Creatinine and urea (or blood urea nitrogen) are waste products that healthy kidneys filter out of "
            "the blood. When kidney function drops, these waste products can build up and the levels rise. "
            "Levels can also be affected by things that are not kidney disease, such as dehydration, a "
            "high-protein meal shortly before the test, intense exercise, or naturally lower muscle mass. A "
            "single raised value is often repeated, sometimes alongside a urine test, before drawing any "
            "conclusions. Drinking enough water, managing blood pressure and blood sugar, and avoiding "
            "long-term overuse of certain pain relievers all support kidney health, but any concern about "
            "kidney function should be discussed with a doctor rather than self-managed."
        ),
    },
    {
        "id": "liver", "title": "Liver enzymes", "tags": ["alt", "ast", "sgpt", "sgot", "alp", "bilirubin", "liver"],
        "text": (
            "ALT and AST are enzymes found mainly in liver cells; when liver cells are stressed or damaged, "
            "these enzymes can leak into the blood and the levels rise. Common, often reversible causes include "
            "fatty liver (linked to weight, alcohol or blood sugar), certain medicines, or a recent viral "
            "infection; AST can also rise after hard exercise or muscle injury, since muscle contains it too. "
            "Bilirubin is a yellow pigment made when old red blood cells break down and is processed by the "
            "liver; a mildly raised level is sometimes a harmless, common trait, while a clearly raised level "
            "should be reviewed by a doctor. Maintaining a healthy weight, limiting alcohol, and reviewing "
            "medicines with a doctor are common general steps to support liver health."
        ),
    },
    {
        "id": "thyroid", "title": "Thyroid and TSH", "tags": ["tsh", "thyroid"],
        "text": (
            "The thyroid gland makes hormones that control how fast the body uses energy. TSH is a signal sent "
            "from the brain that tells the thyroid how much hormone to make; it moves in the opposite "
            "direction to thyroid activity. A high TSH usually means the thyroid is underactive and the brain "
            "is asking it to work harder, which is often linked to tiredness, weight gain or feeling cold. A "
            "low TSH usually means the thyroid is overactive, which can be linked to weight loss, a fast "
            "heartbeat or feeling anxious or warm. Because TSH alone does not always tell the full story, "
            "doctors often add T3 and T4 tests before deciding on next steps."
        ),
    },
    {
        "id": "cbc_infection", "title": "White blood cells and infection", "tags": ["wbc", "white blood cells"],
        "text": (
            "White blood cells are the immune system's defenders against infection. A count above the usual "
            "range often reflects the body actively fighting an infection or responding to inflammation or "
            "stress, and it usually settles once the underlying cause resolves. A count below the usual range "
            "can follow a viral illness, certain medicines, or other causes, and a count that stays low over "
            "repeated tests is usually followed up more closely. Because many different things can raise or "
            "lower this count, it is almost always read together with symptoms and other tests rather than on "
            "its own."
        ),
    },
    {
        "id": "platelets", "title": "Platelets and clotting", "tags": ["platelets"],
        "text": (
            "Platelets are small cell fragments that clump together to stop bleeding when a blood vessel is "
            "injured. A mildly low count can happen after a viral infection or with certain medicines and "
            "often returns to normal on its own, while a very low count raises the chance of easy bruising or "
            "bleeding and deserves prompt medical attention. A raised platelet count can be a temporary "
            "reaction to infection, inflammation or low iron, or in some cases reflect a condition of the bone "
            "marrow. Because the reasons vary widely, an out-of-range platelet count is usually interpreted "
            "alongside other blood count values and the person's symptoms."
        ),
    },
    {
        "id": "esr", "title": "ESR and inflammation", "tags": ["esr"],
        "text": (
            "ESR (erythrocyte sedimentation rate) is a simple test that measures how quickly red blood cells "
            "settle at the bottom of a tube over an hour; it rises when there is inflammation somewhere in the "
            "body, since inflammation changes proteins in the blood in a way that makes the cells clump and "
            "settle faster. It is not specific to any one condition: infections, autoimmune conditions, "
            "chronic disease, and even anemia can all raise it. Because of this, ESR is used as a general "
            "signal to look further, usually combined with symptoms and other tests, rather than as a test "
            "that identifies a specific illness by itself."
        ),
    },
    {
        "id": "uric_acid", "title": "Uric acid and gout", "tags": ["uric_acid", "uric acid", "gout"],
        "text": (
            "Uric acid is a waste product made when the body breaks down purines, substances found in the "
            "body's own cells and in some foods such as red meat, organ meat, certain seafood, and alcohol "
            "(especially beer). When uric acid builds up, it can form sharp crystals in joints, most classically "
            "causing sudden pain and swelling in the big toe, a condition called gout; it can also contribute "
            "to kidney stones. Drinking enough water, limiting alcohol and purine-rich foods, and maintaining a "
            "healthy weight can help keep levels down. Someone with joint pain and a raised uric acid level "
            "should see a doctor, since gout attacks are usually very treatable once identified."
        ),
    },
    {
        "id": "electrolytes", "title": "Electrolytes: sodium and potassium", "tags": ["sodium", "potassium", "electrolytes"],
        "text": (
            "Sodium and potassium are minerals, called electrolytes, that help control the body's fluid balance "
            "and let nerves and muscles, including the heart, work properly. Sodium levels are closely tied to "
            "how much water is in the body: low sodium can come from drinking large amounts of water, certain "
            "medicines, or illness, while high sodium is often linked to not drinking enough fluids. Potassium "
            "levels can be affected by vomiting, diarrhea, certain medicines, or kidney function, and because "
            "potassium is important for a steady heartbeat, results that are clearly high or low are usually "
            "followed up by a doctor promptly rather than left to recheck later."
        ),
    },
]
