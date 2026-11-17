import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, schemas, ai
from .database import Base, engine, get_db, SessionLocal
from .security import hash_password, verify_password, create_token, current_user, require_roles

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:  # seed admin from env - change the password in production!
        if not db.query(models.User).filter_by(username="admin").first():
            db.add(models.User(username="admin", role="admin",
                               password_hash=hash_password(os.getenv("ADMIN_PASSWORD", "Admin@12345"))))
            db.commit()
    yield

app = FastAPI(title="Smart Disaster Response & Emergency Coordination Platform", version="1.0.0",
              lifespan=lifespan, description="AI-assisted incident triage, resource dispatch and analytics.")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}

# ---------- Auth ----------
@app.post("/auth/register", status_code=201, tags=["auth"])
def register(body: schemas.RegisterIn, db: Session = Depends(get_db)):
    if db.query(models.User).filter_by(username=body.username).first():
        raise HTTPException(409, "Username already taken")
    db.add(models.User(username=body.username, password_hash=hash_password(body.password)))
    db.commit()
    return {"message": "registered", "role": "citizen"}

@app.post("/auth/login", response_model=schemas.TokenOut, tags=["auth"])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = db.query(models.User).filter_by(username=form.username).first()
    if not u or not verify_password(form.password, u.password_hash):
        raise HTTPException(401, "Incorrect username or password")
    return {"access_token": create_token(u.username, u.role), "role": u.role}

@app.put("/admin/users/{username}/role", tags=["auth"])
def set_role(username: str, body: schemas.RoleIn, db: Session = Depends(get_db), _=Depends(require_roles("admin"))):
    u = db.query(models.User).filter_by(username=username).first()
    if not u:
        raise HTTPException(404, "User not found")
    u.role = body.role
    db.commit()
    return {"username": username, "role": u.role}

# ---------- Incidents ----------
@app.post("/incidents", response_model=schemas.IncidentOut, status_code=201, tags=["incidents"])
def report_incident(body: schemas.IncidentIn, db: Session = Depends(get_db), user=Depends(current_user)):
    t = ai.triage(body.category, body.title, body.description)
    inc = models.Incident(**body.model_dump(), severity=t["severity"], ai_summary=t["summary"],
                          ai_actions=t["actions"], reported_by=user.id)
    db.add(inc); db.commit(); db.refresh(inc)
    return inc

@app.get("/incidents", response_model=list[schemas.IncidentOut], tags=["incidents"])
def list_incidents(status: str | None = None, category: str | None = None,
                   min_severity: int = Query(1, ge=1, le=5), limit: int = Query(100, le=500),
                   db: Session = Depends(get_db), _=Depends(current_user)):
    q = db.query(models.Incident).filter(models.Incident.severity >= min_severity)
    if status: q = q.filter_by(status=status)
    if category: q = q.filter_by(category=category)
    return q.order_by(models.Incident.severity.desc(), models.Incident.created_at.desc()).limit(limit).all()

@app.get("/incidents/{iid}", response_model=schemas.IncidentOut, tags=["incidents"])
def get_incident(iid: int, db: Session = Depends(get_db), _=Depends(current_user)):
    inc = db.get(models.Incident, iid)
    if not inc: raise HTTPException(404, "Incident not found")
    return inc

@app.patch("/incidents/{iid}/status", response_model=schemas.IncidentOut, tags=["incidents"])
def update_status(iid: int, body: schemas.StatusIn, db: Session = Depends(get_db),
                  _=Depends(require_roles("responder", "admin"))):
    inc = db.get(models.Incident, iid)
    if not inc: raise HTTPException(404, "Incident not found")
    inc.status = body.status; db.commit(); db.refresh(inc)
    return inc

@app.delete("/incidents/{iid}", status_code=204, tags=["incidents"])
def delete_incident(iid: int, db: Session = Depends(get_db), _=Depends(require_roles("admin"))):
    inc = db.get(models.Incident, iid)
    if not inc: raise HTTPException(404, "Incident not found")
    db.query(models.Dispatch).filter_by(incident_id=iid).delete()
    db.delete(inc); db.commit()

# ---------- Resources & dispatch ----------
@app.post("/resources", response_model=schemas.ResourceOut, status_code=201, tags=["resources"])
def add_resource(body: schemas.ResourceIn, db: Session = Depends(get_db), _=Depends(require_roles("responder", "admin"))):
    r = models.Resource(**body.model_dump()); db.add(r); db.commit(); db.refresh(r)
    return r

@app.get("/resources", response_model=list[schemas.ResourceOut], tags=["resources"])
def list_resources(db: Session = Depends(get_db), _=Depends(current_user)):
    return db.query(models.Resource).all()

@app.post("/incidents/{iid}/dispatch", tags=["resources"])
def dispatch(iid: int, body: schemas.DispatchIn, db: Session = Depends(get_db), _=Depends(require_roles("responder", "admin"))):
    inc, res = db.get(models.Incident, iid), db.get(models.Resource, body.resource_id)
    if not inc or not res: raise HTTPException(404, "Incident or resource not found")
    if res.quantity < body.quantity: raise HTTPException(409, f"Only {res.quantity} available")
    res.quantity -= body.quantity
    inc.status = "responding"
    db.add(models.Dispatch(incident_id=iid, resource_id=res.id, quantity=body.quantity))
    db.commit()
    return {"message": "dispatched", "remaining": res.quantity}

# ---------- Analytics (Pandas) ----------
@app.get("/analytics/summary", tags=["analytics"])
def analytics(db: Session = Depends(get_db), _=Depends(current_user)):
    import pandas as pd
    rows = db.query(models.Incident).all()
    df = pd.DataFrame([{"category": r.category, "status": r.status, "severity": r.severity,
                        "day": r.created_at.date().isoformat()} for r in rows])
    if df.empty:
        return {"total": 0, "avg_severity": 0, "by_status": {}, "by_category": {}, "by_severity": {}, "per_day": {}}
    return {"total": len(df), "avg_severity": round(float(df.severity.mean()), 2),
            "by_status": df.status.value_counts().to_dict(),
            "by_category": df.category.value_counts().to_dict(),
            "by_severity": {int(k): int(v) for k, v in df.severity.value_counts().sort_index().items()},
            "per_day": df.day.value_counts().sort_index().to_dict()}

# React dashboard served at "/" (mounted last so API routes win)
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "frontend"), html=True), name="ui")
