"""Reference data: countries, cities, specialties and the option lists used in forms.

To open a new country, set active=True here (or flip it in the admin panel)
and add its cities. Nothing else in the code is Qatar-specific.
"""

COUNTRIES = [
    # code, name, slug, currency, licensing body, active, sort
    ("QA", "Qatar", "qatar", "QAR",
     "Department of Healthcare Professions (DHP), Ministry of Public Health", True, 1),
    ("AE", "United Arab Emirates", "uae", "AED",
     "DHA (Dubai), DOH (Abu Dhabi), MOHAP (Northern Emirates)", False, 2),
    ("SA", "Saudi Arabia", "saudi-arabia", "SAR",
     "Saudi Commission for Health Specialties (SCFHS)", False, 3),
    ("KW", "Kuwait", "kuwait", "KWD", "Ministry of Health Kuwait", False, 4),
    ("OM", "Oman", "oman", "OMR", "Oman Medical Specialty Board / MOH", False, 5),
    ("BH", "Bahrain", "bahrain", "BHD",
     "National Health Regulatory Authority (NHRA)", False, 6),
]

CITIES = {
    "QA": ["Doha", "Al Rayyan", "Al Wakrah", "Lusail", "Al Khor", "Umm Salal",
           "Mesaieed", "Dukhan", "Al Shamal"],
    "AE": ["Dubai", "Abu Dhabi", "Sharjah", "Al Ain", "Ras Al Khaimah"],
    "SA": ["Riyadh", "Jeddah", "Dammam", "Makkah", "Madinah"],
    "KW": ["Kuwait City"],
    "OM": ["Muscat", "Salalah"],
    "BH": ["Manama"],
}

SPECIALTIES = [
    "Anaesthesia", "Cardiology", "Cardiothoracic Surgery", "Critical Care / ICU",
    "Dermatology", "Emergency Medicine", "Endocrinology", "ENT / Otolaryngology",
    "Family Medicine", "Gastroenterology", "General Practice", "General Surgery",
    "Geriatrics", "Haematology", "Infectious Diseases", "Internal Medicine",
    "Interventional Radiology", "Nephrology", "Neonatology", "Neurology",
    "Neurosurgery", "Obstetrics & Gynaecology", "Oncology", "Ophthalmology",
    "Oral & Maxillofacial Surgery", "Orthopaedics", "Paediatric Surgery",
    "Paediatrics", "Pain Medicine", "Pathology", "Physical Medicine & Rehabilitation",
    "Plastic Surgery", "Psychiatry", "Pulmonology", "Radiology", "Rheumatology",
    "Urology", "Vascular Surgery",
]

GRADES = [
    # Clinical grade, most senior first. Keys are stored in the database; never rename a key.
    ("senior_consultant", "Senior consultant"),
    ("consultant", "Consultant"),
    ("associate_consultant", "Associate consultant"),
    ("senior_specialist", "Senior specialist"),
    ("specialist", "Specialist"),
    ("associate_specialist", "Assistant specialist"),
    ("registrar", "Registrar / fellow"),
    ("gp", "General practitioner"),
    ("resident", "Resident / medical officer"),
    ("intern", "Intern / house officer"),
]

# University teaching titles, separate from the clinical grade.
#
# Egyptian universities and Gulf / international universities use the same words for
# different levels (an Egyptian "assistant professor", أستاذ مساعد, sits where the Gulf
# has an associate professor, أستاذ مشارك). So doctors pick the exact title from their
# own system and every title carries an equivalent level, 1 (teaching assistant) to
# 6 (emeritus), which is what facilities filter on.
#   Egypt: Supreme Council of Universities ranks (معيد, مدرس مساعد, مدرس, أستاذ مساعد, أستاذ, أستاذ متفرغ)
#   Gulf:  Saudi / Qatari university ranks (معيد, محاضر, أستاذ مساعد, أستاذ مشارك, أستاذ)
ACADEMIC_LEVELS = [
    (1, "Teaching assistant"),
    (2, "Lecturer"),
    (3, "Assistant professor"),
    (4, "Associate professor"),
    (5, "Professor"),
    (6, "Emeritus professor"),
]
# (key, label in the dropdown, label shown on profiles, level)
ACADEMIC_TITLE_GROUPS = [
    ("Gulf, UK and other universities", [
        ("teaching_assistant", "Teaching assistant / demonstrator", "Teaching assistant", 1),
        ("lecturer", "Lecturer", "Lecturer", 2),
        ("assistant_professor", "Assistant professor", "Assistant professor", 3),
        ("associate_professor", "Associate professor", "Associate professor", 4),
        ("professor", "Professor", "Professor", 5),
        ("professor_emeritus", "Emeritus professor", "Emeritus professor", 6),
    ]),
    ("Egyptian universities", [
        ("eg_demonstrator", "Demonstrator (معيد)", "Demonstrator (Egypt)", 1),
        ("eg_assistant_lecturer", "Assistant lecturer (مدرس مساعد)", "Assistant lecturer (Egypt)", 2),
        ("eg_lecturer", "Lecturer (مدرس)", "Lecturer (Egypt)", 3),
        ("eg_assistant_professor", "Assistant professor (أستاذ مساعد)", "Assistant professor (Egypt)", 4),
        ("eg_professor", "Professor (أستاذ)", "Professor (Egypt)", 5),
        ("eg_emeritus", "Emeritus professor (أستاذ متفرغ)", "Emeritus professor (Egypt)", 6),
    ]),
]
# Earlier options, kept so existing profiles still display and filter correctly.
_LEGACY_ACADEMIC = [
    ("assistant_lecturer", "Assistant lecturer", 2),
    ("clinical_tutor", "Clinical tutor / instructor", 1),
]
ACADEMIC_RANKS = [(k, shown) for _g, items in ACADEMIC_TITLE_GROUPS for k, _o, shown, _l in items] + \
    [(k, shown) for k, shown, _l in _LEGACY_ACADEMIC]
ACADEMIC_LEGACY_KEYS = [k for k, _s, _l in _LEGACY_ACADEMIC]
ACADEMIC_LEVEL = {k: lvl for _g, items in ACADEMIC_TITLE_GROUPS for k, _o, _s, lvl in items}
ACADEMIC_LEVEL.update({k: lvl for k, _s, lvl in _LEGACY_ACADEMIC})


def academic_equivalent(key):
    """For an Egyptian title, the Gulf / international title at the same level (English msgid); else None."""
    if not key.startswith("eg_"):
        return None
    return dict(ACADEMIC_LEVELS).get(ACADEMIC_LEVEL.get(key))


def academic_keys_at_least(level):
    return [k for k, lvl in ACADEMIC_LEVEL.items() if lvl >= level]

QATAR_LICENSE_STATUS = [
    ("none", "Not started"),
    ("evaluating", "DHP evaluation in progress"),
    ("eligible", "Evaluation passed, eligible for licence"),
    ("temporary", "Holds a temporary DHP licence"),
    ("licensed", "Holds a full DHP licence"),
]

EXAM_STATUS = [
    ("unknown", "Not sure yet"),
    ("exempt", "Exempt (category 1 or 2 qualification)"),
    ("passed", "Passed the DHP qualifying exam"),
    ("required", "Required, not yet taken"),
]

DOCUMENT_KINDS = [
    ("cv", "CV"),
    ("license", "Medical licence"),
    ("degree", "Degree / specialty certificate"),
    ("psv", "Primary source verification report"),
    ("good_standing", "Certificate of good standing"),
    ("passport", "Passport"),
    ("other", "Other"),
]

FACILITY_TYPES = [
    ("hospital", "Hospital"),
    ("polyclinic", "Polyclinic / medical centre"),
    ("clinic", "Specialty clinic"),
    ("day_surgery", "Day surgery centre"),
    ("primary_care", "Primary care centre"),
    ("agency", "Recruitment agency"),
]

SECTORS = [
    ("government", "Government"),
    ("semi_government", "Semi-government"),
    ("private", "Private"),
]

RATE_PERIODS = [("day", "per day"), ("week", "per week"), ("month", "per month")]

APPLICATION_STATUSES = [
    ("submitted", "Submitted"),
    ("shortlisted", "Shortlisted"),
    ("interview", "Interview"),
    ("offered", "Offer made"),
    ("placed", "Placed"),
    ("declined", "Not progressed"),
    ("withdrawn", "Withdrawn"),
]

JOB_STATUSES = [("open", "Open"), ("filled", "Filled"), ("closed", "Closed")]


def label(options, key, default="—"):
    """Return the human label for a stored option key, in the current language."""
    from .i18n import gettext
    for k, v in options:
        if k == key:
            return gettext(v)
    return default if not key else key
