"""AI-assisted triage.

Default: transparent rule-based scoring (offline, explainable, testable).
Extension point: replace `triage()` with an LLM call (Claude/Gemini/OpenAI) returning the same dict.
Ethical rule: AI output is a *suggestion*; a human responder verifies before dispatch.
"""
CRITICAL = {"trapped": 2, "collapsed": 2, "unconscious": 2, "bleeding": 1, "drowning": 2,
            "explosion": 2, "spreading": 1, "children": 1, "elderly": 1, "pregnant": 1,
            "no food": 1, "no water": 1, "rising": 1, "dead": 2, "missing": 1}
BASE = {"earthquake": 3, "fire": 3, "flood": 3, "cyclone": 3, "landslide": 3, "medical": 3, "other": 2}
ACTIONS = {
    "flood": ["Dispatch rescue boats", "Open nearest shelter", "Issue evacuation advisory"],
    "fire": ["Dispatch fire units", "Cordon the area", "Alert nearby hospitals"],
    "earthquake": ["Deploy search & rescue", "Check structural safety", "Prepare field medical teams"],
    "cyclone": ["Move residents to shelters", "Pre-position food & water", "Restore comms"],
    "landslide": ["Close affected roads", "Deploy rescue team", "Evacuate downslope homes"],
    "medical": ["Send ambulance", "Notify nearest hospital"],
    "other": ["Assign responder to verify"],
}

def triage(category: str, title: str, description: str) -> dict:
    text = f"{title} {description}".lower()
    hits = [k for k in CRITICAL if k in text]
    score = BASE.get(category, 2) + sum(CRITICAL[k] for k in hits)
    severity = max(1, min(5, score if score <= 5 else 5))
    summary = (f"{category.title()} incident, AI-suggested severity {severity}/5"
               + (f" (signals: {', '.join(hits)})" if hits else "") + ". Needs human verification.")
    return {"severity": severity, "summary": summary, "actions": "; ".join(ACTIONS.get(category, ACTIONS["other"]))}
