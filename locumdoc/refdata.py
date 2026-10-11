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
    ("consultant", "Consultant"),
    ("senior_specialist", "Senior specialist"),
    ("specialist", "Specialist"),
    ("associate_specialist", "Associate / assistant specialist"),
    ("registrar", "Registrar / fellow"),
    ("gp", "General practitioner"),
    ("resident", "Resident / medical officer"),
]

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
