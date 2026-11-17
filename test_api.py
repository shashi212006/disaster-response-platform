import os, tempfile
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
from fastapi.testclient import TestClient
from app.main import app

def login(c, u, p):
    r = c.post("/auth/login", data={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

def test_full_flow():
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert c.get("/incidents").status_code == 401
        assert c.post("/auth/register", json={"username": "rina", "password": "Passw0rd!x"}).status_code == 201
        assert c.post("/auth/register", json={"username": "rina", "password": "Passw0rd!x"}).status_code == 409
        assert c.post("/auth/login", data={"username": "rina", "password": "bad"}).status_code == 401
        citizen = login(c, "rina", "Passw0rd!x")
        body = {"title": "River overflowing", "category": "flood", "location": "Warangal North",
                "description": "Water rising fast, elderly and children trapped on first floor."}
        r = c.post("/incidents", json=body, headers=citizen)
        assert r.status_code == 201 and r.json()["severity"] >= 4
        iid = r.json()["id"]
        assert c.post("/incidents", json={**body, "category": "bad"}, headers=citizen).status_code == 422
        assert c.patch(f"/incidents/{iid}/status", json={"status": "verified"}, headers=citizen).status_code == 403
        admin = login(c, "admin", "Admin@12345")
        assert c.put("/admin/users/rina/role", json={"role": "responder"}, headers=admin).status_code == 200
        res = c.post("/resources", json={"name": "Rescue Boat", "type": "boat", "quantity": 3, "location": "Depot A"}, headers=admin).json()
        assert c.post(f"/incidents/{iid}/dispatch", json={"resource_id": res["id"], "quantity": 5}, headers=admin).status_code == 409
        d = c.post(f"/incidents/{iid}/dispatch", json={"resource_id": res["id"], "quantity": 2}, headers=admin)
        assert d.json()["remaining"] == 1
        assert c.get(f"/incidents/{iid}", headers=admin).json()["status"] == "responding"
        a = c.get("/analytics/summary", headers=admin).json()
        assert a["total"] == 1 and a["by_category"] == {"flood": 1}
        assert c.delete(f"/incidents/{iid}", headers=citizen).status_code == 403
        assert c.delete(f"/incidents/{iid}", headers=admin).status_code == 204
