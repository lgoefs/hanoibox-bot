# ============================================================
# GYM INFO & FAQ -- Edit this file to update gym details
# The bot uses this to answer member questions automatically
# ============================================================

GYM_NAME = "HanoiBox"
GYM_LOCATION = "Hanoi, Vietnam"
GYM_PHONE = ""       # Add: e.g. "+84 123 456 789"
GYM_ADDRESS = ""     # Add: e.g. "123 Tay Ho, Tay Ho District, Hanoi"
GYM_FACEBOOK = ""    # Add your Facebook page URL
GYM_INSTAGRAM = ""   # Add your Instagram handle

# ---- CLASS SCHEDULE ----------------------------------------
SCHEDULE = """
Monday:    6:00am Group Boxing | 7:00pm Group Boxing
Tuesday:   6:00am Private sessions | 7:00pm Group Boxing
Wednesday: 6:00am Group Boxing | 7:00pm Group Boxing
Thursday:  6:00am Private sessions | 7:00pm Group Boxing
Friday:    6:00am Group Boxing | 7:00pm Group Boxing
Saturday:  9:00am Group Boxing | Open sparring
Sunday:    Rest day
"""

# ---- PRICING -----------------------------------------------
PRICING = """
Group 3-Month:    $120 (~3,000,000 VND) - unlimited group classes for 3 months
Private 10-Pack:  $180 (~4,500,000 VND) - 10 x 1-on-1 sessions, valid 4 months
Private Monthly:  $80/month (~2,000,000 VND) - unlimited private sessions
Drop-in class:    $10 (~250,000 VND) - single group session
Trial session:    Free - first-time visitors welcome
"""

# ---- COACHES -----------------------------------------------
COACHES = """
Head Coach: Ask admin to update
Specialties: Boxing technique, pad work, sparring, conditioning
"""

# ---- FAQ KEYWORD MAP ---------------------------------------
FAQ = {
    "location": f"We are located at {'{'}GYM_ADDRESS or 'ask admin to update'{'}'}. HanoiBox is in Hanoi, Vietnam.",
    "address": "Our address - ask admin to add this to gym_info.py",
    "phone": "Phone/WhatsApp - ask admin to add this to gym_info.py",
    "parking": "Motorbike parking is available outside the gym.",
    "gear": "Beginners - just bring a towel and water. We have gloves and wraps to borrow. Experienced boxers should bring their own gloves.",
    "beginner": "Absolutely welcome! Group classes suit all levels. Just show up and the coaches will look after you.",
    "kids": "We accept members from age 14+. Younger students by arrangement with the coach.",
    "women": "Yes, we have female members and mixed classes. Everyone is welcome.",
    "trial": "First trial session is FREE. Just message us or walk in.",
    "schedule": SCHEDULE,
    "classes": SCHEDULE,
    "timing": SCHEDULE,
    "timetable": SCHEDULE,
    "price": PRICING,
    "pricing": PRICING,
    "cost": PRICING,
    "fee": PRICING,
    "membership": PRICING,
    "coach": COACHES,
    "trainer": COACHES,
}

def get_gym_context():
    return {
        "gym_name": GYM_NAME,
        "location": GYM_LOCATION,
        "address": GYM_ADDRESS,
        "phone": GYM_PHONE,
        "schedule": SCHEDULE.strip(),
        "pricing": PRICING.strip(),
        "coaches": COACHES.strip(),
    }

def find_faq_answer(text):
    text_lower = text.lower()
    # Check schedule/price first (most common)
    for kw in ["schedule","timetable","timing","class","price","pricing","cost","fee","membership","location","address","phone","gear","equipment","beginner","trial","coach","trainer","parking","kids","women"]:
        if kw in text_lower:
            return FAQ.get(kw)
    return None
