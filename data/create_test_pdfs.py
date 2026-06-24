"""
Generate 10 synthetic discharge summary PDFs for testing.
Run from project root: python data/create_test_pdfs.py
"""
from fpdf import FPDF, XPos, YPos
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__))


def sanitize(text: str) -> str:
    return (text
            .replace("—", " - ")   # em dash
            .replace("–", " - ")   # en dash
            .replace("’", "'")     # right single quote
            .replace("“", '"')
            .replace("”", '"'))


def make_pdf(patient: dict, filename: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    def heading(text):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, sanitize(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", size=10)

    def line(text):
        pdf.set_font("Helvetica", size=10)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 6, sanitize(text))

    def blank():
        pdf.ln(3)

    # Title
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "DISCHARGE SUMMARY - SYNTHETIC PATIENT DATA (NOT REAL)",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    blank()

    # Patient header
    pdf.set_font("Helvetica", "B", 11)
    for field in patient.get("header", []):
        pdf.cell(0, 7, sanitize(field), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    blank()

    if patient.get("diagnosis"):
        heading("DIAGNOSIS")
        for d in patient["diagnosis"]:
            line(d)
        blank()

    if patient.get("medications"):
        heading("MEDICATIONS AT DISCHARGE")
        for i, med in enumerate(patient["medications"], 1):
            line(f"{i}. {med}")
        blank()

    if patient.get("appointments"):
        heading("FOLLOW-UP APPOINTMENTS")
        for appt in patient["appointments"]:
            line(f"- {appt}")
        blank()

    if patient.get("activity"):
        heading("ACTIVITY RESTRICTIONS")
        for a in patient["activity"]:
            line(f"- {a}")
        blank()

    if patient.get("diet"):
        heading("DIETARY RESTRICTIONS")
        for d in patient["diet"]:
            line(f"- {d}")
        blank()

    if patient.get("er_signs"):
        heading("GO TO THE EMERGENCY ROOM IMMEDIATELY IF YOU EXPERIENCE")
        for s in patient["er_signs"]:
            line(f"- {s}")
        blank()

    if patient.get("call_signs"):
        heading("CALL YOUR DOCTOR WITHIN 24 HOURS IF YOU NOTICE")
        for s in patient["call_signs"]:
            line(f"- {s}")
        blank()

    if patient.get("notes"):
        heading("ADDITIONAL NOTES")
        for n in patient["notes"]:
            line(n)

    path = os.path.join(OUTPUT_DIR, filename)
    pdf.output(path)
    print(f"Created: {filename}")


PATIENTS = [
    # 1: CHF - standard complexity
    {
        "header": [
            "Patient: John Demo Patient",
            "Date of Birth: 01/15/1955",
            "Discharge Date: 2026-06-10",
            "Admit Date: 2026-06-06",
            "Hospital: City General Hospital",
            "Attending Physician: Dr. Michael Torres",
            "Primary Specialty: Cardiology",
        ],
        "diagnosis": [
            "Primary Diagnosis: Congestive Heart Failure (CHF) Exacerbation",
            "ICD-10 Code: I50.9",
        ],
        "medications": [
            "Furosemide (Lasix) 40mg - Once daily in the morning with water",
            "Lisinopril 10mg - Once daily with breakfast",
            "Metoprolol Succinate 25mg - Once daily",
            "Potassium Chloride 20mEq - Once daily with food",
        ],
        "appointments": [
            "Cardiologist Dr. Sarah Chen - within 7 days of discharge",
            "Primary Care Dr. James Park - within 14 days of discharge",
        ],
        "activity": [
            "No lifting more than 10 pounds for 4 weeks",
            "No driving for 1 week",
            "Walk 5-10 minutes twice daily, increase gradually as tolerated",
        ],
        "diet": [
            "Sodium restriction: less than 2000mg per day",
            "Fluid restriction: less than 2 liters per day",
            "Weigh yourself every morning before eating or drinking",
        ],
        "er_signs": [
            "Chest pain or pressure",
            "Difficulty breathing at rest",
            "Weight gain more than 2 pounds in one day or 5 pounds in one week",
            "Severe swelling in legs, ankles, or feet",
            "Fainting or loss of consciousness",
        ],
        "call_signs": [
            "Weight gain of 1-2 pounds in one day",
            "Increased shortness of breath with activity",
            "Increased swelling in feet or ankles",
            "Dizziness or lightheadedness",
            "Fever above 101 degrees F",
        ],
    },
    # 2: Total Knee Replacement
    {
        "header": [
            "Patient: Mary Johnson",
            "Date of Birth: 03/22/1950",
            "Discharge Date: 2026-06-12",
            "Admit Date: 2026-06-10",
            "Hospital: Northside Orthopedic Center",
            "Attending Physician: Dr. Angela Reyes",
            "Primary Specialty: Orthopedic Surgery",
        ],
        "diagnosis": [
            "Primary Diagnosis: Total Right Knee Arthroplasty",
            "ICD-10 Code: Z96.651",
        ],
        "medications": [
            "Oxycodone/Acetaminophen 5/325mg - Every 6 hours as needed for pain (do not drive)",
            "Aspirin 325mg - Once daily with food for blood clot prevention",
            "Celecoxib 200mg - Twice daily with food for swelling and pain",
            "Enoxaparin (Lovenox) injection 40mg - Once daily under skin for 10 days",
        ],
        "appointments": [
            "Orthopedic surgeon Dr. Reyes - 10-14 days post discharge for wound check",
            "Physical therapy - begin 2 days after discharge, 3 times per week for 6 weeks",
        ],
        "activity": [
            "Walk with walker for full weight bearing as tolerated",
            "Do not kneel on the operated knee for 8 weeks",
            "No driving until cleared by surgeon (typically 4-6 weeks)",
            "Elevate leg above heart level when resting to reduce swelling",
            "Perform ankle pumps every hour while awake",
            "Ice knee for 15-20 minutes several times per day",
        ],
        "diet": [
            "No specific dietary restrictions",
            "Stay well hydrated - drink 6-8 glasses of water daily",
            "Constipation is common with opioid pain medication - increase fiber intake",
        ],
        "er_signs": [
            "Sudden chest pain or difficulty breathing (possible blood clot in lungs)",
            "Severe calf pain or swelling (possible blood clot in leg)",
            "Signs of infection: fever above 101.5F, wound drainage, increasing redness",
            "Sudden severe pain not controlled by medication",
        ],
        "call_signs": [
            "Wound is oozing or has increased redness or warmth",
            "Knee swelling is getting significantly worse",
            "Numbness or tingling in foot or leg",
            "Fever between 100-101.5 degrees F",
        ],
    },
    # 3: Pneumonia - simple
    {
        "header": [
            "Patient: Robert Chen",
            "Date of Birth: 07/04/1965",
            "Discharge Date: 2026-06-11",
            "Admit Date: 2026-06-08",
            "Hospital: Memorial Medical Center",
            "Attending Physician: Dr. Priya Kapoor",
            "Primary Specialty: Internal Medicine / Pulmonology",
        ],
        "diagnosis": [
            "Primary Diagnosis: Community-Acquired Pneumonia, right lower lobe",
            "ICD-10 Code: J18.9",
        ],
        "medications": [
            "Azithromycin 250mg - Once daily for 5 days (finish all 5 days even if feeling better)",
            "Amoxicillin-Clavulanate 875/125mg - Twice daily with food for 7 days",
        ],
        "appointments": [
            "Primary Care physician - within 7-10 days for follow-up chest X-ray",
        ],
        "activity": [
            "Rest as needed; do not push yourself to return to normal activity too quickly",
            "Gradual return to exercise - start with short walks",
            "You may return to work when fever-free for 24 hours and feeling well enough",
        ],
        "diet": [
            "No specific dietary restrictions",
            "Drink plenty of fluids - helps thin mucus and aids recovery",
            "Avoid alcohol while taking antibiotics",
        ],
        "er_signs": [
            "Difficulty breathing or shortness of breath at rest",
            "Chest pain especially when breathing in",
            "Coughing up blood",
            "Confusion or altered mental status",
            "Fever above 103 degrees F",
        ],
        "call_signs": [
            "Fever above 100.4 degrees F that returns after going away",
            "Symptoms not improving after 48-72 hours on antibiotics",
            "New or worsening cough",
            "Wheezing or feeling of tightness in chest",
        ],
    },
    # 4: Laparoscopic Appendectomy - simple, very short recovery
    {
        "header": [
            "Patient: Sarah Williams",
            "Date of Birth: 11/30/1990",
            "Discharge Date: 2026-06-13",
            "Admit Date: 2026-06-12",
            "Hospital: Downtown Surgical Hospital",
            "Attending Physician: Dr. Kevin O'Brien",
            "Primary Specialty: General Surgery",
        ],
        "diagnosis": [
            "Primary Diagnosis: Acute Appendicitis, uncomplicated - laparoscopic appendectomy performed",
            "ICD-10 Code: K37",
        ],
        "medications": [
            "Ibuprofen 600mg - Every 6-8 hours with food as needed for pain",
            "Docusate Sodium 100mg - Twice daily for constipation prevention",
        ],
        "appointments": [
            "Surgeon Dr. O'Brien - 7-10 days for wound check and pathology results",
        ],
        "activity": [
            "No heavy lifting more than 10 pounds for 2 weeks",
            "No strenuous exercise for 2 weeks",
            "You may shower 24 hours after discharge - pat incision sites dry",
            "Do not submerge in pools or baths until wounds are fully healed",
            "You may return to desk work in 3-5 days if feeling well",
        ],
        "diet": [
            "Start with clear liquids and advance to regular diet as tolerated",
            "Avoid gas-producing foods for a few days (beans, carbonated drinks)",
            "High fiber diet to prevent constipation",
        ],
        "er_signs": [
            "Severe abdominal pain or sudden worsening of pain",
            "Fever above 101.5 degrees F",
            "Signs of infection at incision site: redness, swelling, pus",
            "Vomiting and unable to keep fluids down",
            "Abdomen becomes hard or rigid",
        ],
        "call_signs": [
            "Mild redness or oozing at incision site",
            "Persistent nausea",
            "Unable to have a bowel movement after 3 days",
            "Pain not controlled with ibuprofen",
        ],
    },
    # 5: Ischemic Stroke - complex, multiple meds with interaction risk
    {
        "header": [
            "Patient: James Thompson",
            "Date of Birth: 05/18/1948",
            "Discharge Date: 2026-06-09",
            "Admit Date: 2026-06-03",
            "Hospital: University Neurology Center",
            "Attending Physician: Dr. Susan Park",
            "Primary Specialty: Neurology",
        ],
        "diagnosis": [
            "Primary Diagnosis: Ischemic Stroke, left middle cerebral artery territory",
            "ICD-10 Code: I63.50",
            "Secondary: Hypertension, Atrial Fibrillation",
        ],
        "medications": [
            "Warfarin 5mg - Once daily; INR monitoring required weekly initially",
            "Aspirin 81mg - Once daily with food",
            "Atorvastatin 80mg - Once daily at bedtime",
            "Lisinopril 20mg - Once daily in the morning",
            "Apixaban 5mg - Twice daily with or without food",
            "Metoprolol Tartrate 50mg - Twice daily",
        ],
        "appointments": [
            "Neurologist Dr. Park - within 7 days for follow-up",
            "Anticoagulation clinic - within 3 days for INR check",
            "Speech therapy - 3 times per week for 8 weeks",
            "Physical therapy - 3 times per week for 8 weeks",
            "Occupational therapy evaluation - within 5 days",
            "Primary Care - within 14 days",
        ],
        "activity": [
            "No driving until cleared by neurologist (minimum 3-6 months)",
            "Supervised ambulation only - risk of falls",
            "Do not operate heavy machinery",
            "Fall prevention: use grab bars, remove loose rugs, ensure good lighting",
        ],
        "diet": [
            "Consistent Vitamin K intake daily if on warfarin",
            "Low sodium diet: less than 1500mg per day",
            "No alcohol - interferes with warfarin and increases bleeding risk",
            "Stay well hydrated",
        ],
        "er_signs": [
            "Sudden numbness or weakness in face, arm, or leg especially on one side",
            "Sudden confusion or trouble speaking or understanding speech",
            "Sudden vision problems in one or both eyes",
            "Sudden severe headache with no known cause",
            "Sudden trouble walking, dizziness, or loss of balance",
            "Any bleeding that will not stop (due to blood thinners)",
        ],
        "call_signs": [
            "New or worsening weakness or numbness",
            "Increased confusion or memory problems",
            "Unusual bruising or prolonged bleeding from minor cuts",
            "Dizziness or falls",
            "Headache that is new or different from usual",
            "Missed INR check appointment",
        ],
        "notes": [
            "IMPORTANT: Patient is on MULTIPLE blood-thinning medications.",
            "Do NOT take any NSAIDs (ibuprofen, naproxen) without physician approval.",
            "All new medications must be reviewed by care team before starting.",
        ],
    },
    # 6: DKA / Type 2 Diabetes
    {
        "header": [
            "Patient: Linda Martinez",
            "Date of Birth: 09/12/1972",
            "Discharge Date: 2026-06-14",
            "Admit Date: 2026-06-11",
            "Hospital: Riverside Community Hospital",
            "Attending Physician: Dr. Thomas Lee",
            "Primary Specialty: Endocrinology",
        ],
        "diagnosis": [
            "Primary Diagnosis: Diabetic Ketoacidosis (DKA) - Type 2 Diabetes Mellitus",
            "ICD-10 Code: E11.10",
        ],
        "medications": [
            "Insulin Glargine (Lantus) 20 units - Once daily at bedtime, subcutaneous injection",
            "Insulin Lispro (Humalog) - Sliding scale with meals, see attached chart",
            "Metformin 1000mg - Twice daily with meals",
            "Lisinopril 10mg - Once daily for kidney protection",
        ],
        "appointments": [
            "Endocrinologist Dr. Lee - within 3 days post-discharge",
            "Diabetes education class - scheduled for 1 week post-discharge",
            "Ophthalmologist - annual diabetic eye exam due",
        ],
        "activity": [
            "Light walking 20-30 minutes daily as tolerated",
            "Monitor blood glucose before and after exercise",
            "Avoid exercise if blood glucose above 300 mg/dL or below 80 mg/dL",
        ],
        "diet": [
            "Diabetic diet: limit carbohydrates to 45-60g per meal",
            "Avoid sugary beverages, juices, and high-sugar foods",
            "Do not skip meals - especially when taking insulin",
            "Consistent meal schedule to help stabilize blood sugar",
            "Stay hydrated with water or sugar-free drinks",
        ],
        "er_signs": [
            "Blood glucose above 400 mg/dL and feeling unwell",
            "Blood glucose below 50 mg/dL and unable to eat or drink",
            "Fruity breath, severe nausea, vomiting, or abdominal pain",
            "Confusion, difficulty waking, or loss of consciousness",
        ],
        "call_signs": [
            "Blood glucose consistently above 250 mg/dL for 2 days",
            "Blood glucose below 70 mg/dL (low blood sugar)",
            "Inability to eat or drink due to nausea",
            "Signs of infection: fever, sores on feet that are slow to heal",
            "Running low on insulin or supplies",
        ],
    },
    # 7: COPD Exacerbation
    {
        "header": [
            "Patient: David Park",
            "Date of Birth: 02/28/1952",
            "Discharge Date: 2026-06-15",
            "Admit Date: 2026-06-11",
            "Hospital: Pulmonary Care Institute",
            "Attending Physician: Dr. Rachel Kim",
            "Primary Specialty: Pulmonology",
        ],
        "diagnosis": [
            "Primary Diagnosis: Acute Exacerbation of Chronic Obstructive Pulmonary Disease (COPD)",
            "ICD-10 Code: J44.1",
        ],
        "medications": [
            "Tiotropium (Spiriva) inhaler - 1 inhalation once daily (long-acting bronchodilator)",
            "Albuterol (Ventolin) inhaler - 2 puffs every 4-6 hours as needed for shortness of breath",
            "Fluticasone/Salmeterol (Advair) 250/50 - 1 puff twice daily (not a rescue inhaler)",
            "Prednisone 40mg - Once daily for 5 days then taper as directed",
        ],
        "appointments": [
            "Pulmonologist Dr. Kim - within 5-7 days post-discharge",
            "Primary Care - within 14 days",
            "Pulmonary rehabilitation referral - please call to schedule",
        ],
        "activity": [
            "Rest and gradually increase activity as breathing improves",
            "Avoid exposure to smoke, dust, fumes, and air pollution",
            "If prescribed home oxygen, use as directed - do not adjust flow rate yourself",
            "Pursed lip breathing: inhale through nose 2 counts, exhale slowly through pursed lips 4 counts",
        ],
        "diet": [
            "No specific dietary restrictions",
            "Eat smaller, more frequent meals - large meals can make breathing harder",
            "Stay well hydrated to help thin secretions",
            "Limit caffeine and alcohol",
        ],
        "er_signs": [
            "Severe shortness of breath that does not improve with rescue inhaler",
            "Lips or fingernails turning blue",
            "Confusion or extreme agitation due to lack of oxygen",
            "Breathing rate very fast with inability to speak full sentences",
        ],
        "call_signs": [
            "Increased shortness of breath compared to your usual baseline",
            "Change in color, amount, or thickness of sputum",
            "Fever above 100.4 degrees F",
            "Needing to use your rescue inhaler more than 4 times per day",
            "Swelling in ankles or legs",
        ],
        "notes": [
            "SMOKING CESSATION: Quitting smoking is the single most important step.",
            "Resources: 1-800-QUIT-NOW or ask your doctor about nicotine replacement therapy.",
        ],
    },
    # 8: Hip Fracture ORIF - most complex, 6 meds
    {
        "header": [
            "Patient: Helen Rodriguez",
            "Date of Birth: 06/10/1940",
            "Discharge Date: 2026-06-13",
            "Admit Date: 2026-06-08",
            "Hospital: St. Mary Orthopedic Hospital",
            "Attending Physician: Dr. William Nguyen",
            "Primary Specialty: Orthopedic Surgery",
        ],
        "diagnosis": [
            "Primary Diagnosis: Right Hip Fracture - Open Reduction Internal Fixation (ORIF)",
            "ICD-10 Code: S72.001A",
            "Secondary: Osteoporosis, Hypertension",
        ],
        "medications": [
            "Enoxaparin (Lovenox) 40mg - Once daily subcutaneous injection for 28 days",
            "Acetaminophen 650mg - Every 6 hours scheduled (do not exceed 3g per day total)",
            "Oxycodone 5mg - Every 4-6 hours as needed for breakthrough pain",
            "Calcium Carbonate 600mg + Vitamin D3 800IU - Twice daily with food",
            "Alendronate (Fosamax) 70mg - Once weekly on same day, on empty stomach with full glass of water",
            "Amlodipine 5mg - Once daily for blood pressure",
        ],
        "appointments": [
            "Orthopedic surgeon Dr. Nguyen - 10-14 days for wound check and X-ray",
            "Physical therapy - daily or home PT 3x weekly",
            "Occupational therapy - home safety evaluation within 5 days",
            "Primary care - 2 weeks for blood pressure and medication review",
            "Bone density scan (DEXA) - schedule within 3 months",
        ],
        "activity": [
            "Weight bearing as tolerated on right leg - use walker at all times",
            "Do not cross legs or bend hip past 90 degrees",
            "Do not pivot on the operated leg",
            "Sleep with pillow between knees to keep hip in proper position",
            "Fall prevention is critical - install grab bars, remove hazards from home",
            "No driving for minimum 6-8 weeks and until cleared by surgeon",
        ],
        "diet": [
            "High protein diet to support healing - eggs, fish, chicken, legumes",
            "Adequate calcium and vitamin D intake (supplements provided)",
            "Stay well hydrated to reduce blood clot risk",
            "Take Alendronate on empty stomach, stay upright 30 minutes after",
        ],
        "er_signs": [
            "Sudden chest pain or difficulty breathing (signs of pulmonary embolism)",
            "Severe swelling, redness, or warmth in calf (signs of DVT)",
            "Signs of hip dislocation: sudden severe pain, leg appears shorter or rotated",
            "Surgical site infection: increasing redness, fever above 101F, wound drainage",
            "Loss of feeling in leg or foot",
        ],
        "call_signs": [
            "Mild calf pain or swelling in the leg",
            "Wound drainage or increased wound redness",
            "Fever 100-101 degrees F",
            "Nausea preventing taking medications",
            "Falling at home - even if no apparent injury",
            "Blood pressure readings above 160/100",
        ],
    },
    # 9: Sepsis - SPARSE (missing ICD-10, no physician listed)
    {
        "header": [
            "Patient: Frank Wilson",
            "Date of Birth: 08/19/1958",
            "Discharge Date: 2026-06-16",
            "Admit Date: 2026-06-13",
            "Hospital: General Community Hospital",
            # No physician listed intentionally
        ],
        "diagnosis": [
            "Diagnosis: Sepsis, urinary source - resolved with IV antibiotics",
            # No ICD-10 code intentionally
        ],
        "medications": [
            "Trimethoprim-Sulfamethoxazole (Bactrim DS) - Twice daily for 10 days",
            "Ibuprofen 400mg - Every 8 hours as needed for fever or discomfort",
            "Probiotics - Once daily to prevent antibiotic-related diarrhea",
        ],
        "appointments": [
            "Follow up with your regular doctor in 1 week",
        ],
        "activity": [
            "Rest at home for several days",
            "Resume normal activities gradually as energy returns",
        ],
        "diet": [
            "Drink plenty of fluids especially water",
        ],
        "er_signs": [
            "High fever above 103 degrees F or chills and shaking",
            "Confusion or extreme fatigue",
            "Rapid heart rate or difficulty breathing",
        ],
        "call_signs": [
            "Fever that returns after going away",
            "Burning with urination not improving",
            "Not feeling better after 48 hours of antibiotics",
        ],
    },
    # 10: Chemotherapy - VERY SPARSE, multiple missing fields
    {
        "header": [
            "Patient: Margaret Brown",
            "Date of Birth: 04/25/1962",
            "Discharge Date: 2026-06-17",
            "Hospital: Cancer Care Center",
            # No admit date, no physician, no specialty - intentional
        ],
        "diagnosis": [
            "Breast cancer, chemotherapy cycle 3 of 6 completed",
            # No ICD-10 intentionally
        ],
        "medications": [
            "Ondansetron 8mg - Every 8 hours for nausea as needed",
            "Filgrastim (Neupogen) injection - Once daily for 7 days",
            "Lorazepam 0.5mg - For severe nausea or anxiety, maximum twice per day",
            "Dexamethasone 4mg - Twice daily for 3 days then stop",
            "Omeprazole 20mg - Once daily",
        ],
        "appointments": [
            "Oncology clinic - blood draw 7 days post-discharge before next cycle",
        ],
        "activity": [
            "Rest as needed. Fatigue is expected and normal.",
        ],
        "diet": [
            "Small frequent meals to manage nausea",
            "Avoid raw or undercooked foods due to reduced immune function",
        ],
        "er_signs": [
            "Fever above 100.4 degrees F - neutropenic fever is a medical emergency",
            "Bleeding that will not stop",
            "Severe nausea and vomiting preventing any food or fluid intake",
        ],
        "call_signs": [
            "Fever above 100 but below 100.4",
            "Mouth sores making it hard to eat",
            "Unusual bruising or bleeding",
        ],
        "notes": [
            "NOTE: This summary is intentionally incomplete. Some discharge information",
            "was not documented at time of printing. Follow up with oncology for full plan.",
        ],
    },
]

FILE_NAMES = [
    "01_chf_john_demo.pdf",
    "02_knee_replacement_mary.pdf",
    "03_pneumonia_robert.pdf",
    "04_appendectomy_sarah.pdf",
    "05_stroke_james.pdf",
    "06_diabetes_dka_linda.pdf",
    "07_copd_david.pdf",
    "08_hip_fracture_helen.pdf",
    "09_sepsis_frank_sparse.pdf",
    "10_chemo_margaret_very_sparse.pdf",
]

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for patient, filename in zip(PATIENTS, FILE_NAMES):
        make_pdf(patient, filename)
    print(f"\nAll 10 PDFs written to: {os.path.abspath(OUTPUT_DIR)}")
    print("\nComplexity guide:")
    print("  Simple       : 03_pneumonia, 04_appendectomy (1-2 meds, short recovery)")
    print("  Moderate     : 01_chf, 02_knee, 06_diabetes, 07_copd (3-4 meds)")
    print("  Complex      : 05_stroke (6 meds, drug interaction risk)")
    print("                 08_hip_fracture (6 meds, most appointments)")
    print("  Sparse/tricky: 09_sepsis (no ICD-10, no physician)")
    print("  Very sparse  : 10_chemo (many missing fields - tests intake fallback)")
