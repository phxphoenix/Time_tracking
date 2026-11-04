import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
import auth
from main import app, get_db

# In-memory SQLite database shared across threads via StaticPool for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def client():
    models.Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create initial admin user
    admin_user = models.User(
        username="phx",
        email="phx.poczta@gmail.com",
        hashed_password=auth.get_password_hash("testpass123"),
    )
    db.add(admin_user)
    db.commit()
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    models.Base.metadata.drop_all(bind=engine)


def get_auth_headers(client: TestClient, username="phx", password="testpass123"):
    res = client.post(
        "/api/auth/token",
        data={"username": username, "password": password},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, token


def test_index_serves_frontend(client: TestClient):
    res = client.get("/")
    assert res.status_code == 200
    assert "TimeTracker" in res.text


def test_authentication_flow(client: TestClient):
    # Invalid password
    bad_res = client.post(
        "/api/auth/token",
        data={"username": "phx", "password": "wrongpassword"},
    )
    assert bad_res.status_code == 401

    # Unauthorized /api/me
    unauth_res = client.get("/api/me")
    assert unauth_res.status_code == 401

    # Valid login by username
    headers, _ = get_auth_headers(client, "phx", "testpass123")
    me_res = client.get("/api/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "phx"

    # Valid login by email
    headers_email, _ = get_auth_headers(client, "phx.poczta@gmail.com", "testpass123")
    me_res2 = client.get("/api/me", headers=headers_email)
    assert me_res2.status_code == 200
    assert me_res2.json()["username"] == "phx"


def test_users_crud(client: TestClient):
    headers, _ = get_auth_headers(client)

    # Create user
    res = client.post(
        "/api/users",
        json={"username": "jan_kowalski", "email": "jan@example.com", "password": "secret"},
        headers=headers,
    )
    assert res.status_code == 200
    new_user = res.json()
    assert new_user["username"] == "jan_kowalski"

    # Duplicate username check
    dup = client.post(
        "/api/users",
        json={"username": "jan_kowalski", "email": "other@example.com", "password": "secret"},
        headers=headers,
    )
    assert dup.status_code == 400

    # Update password & username
    upd = client.put(
        f"/api/users/{new_user['id']}",
        json={"username": "jan_nowak", "password": "newpassword"},
        headers=headers,
    )
    assert upd.status_code == 200
    assert upd.json()["username"] == "jan_nowak"

    # Verify updated user can log in
    jan_headers, _ = get_auth_headers(client, "jan_nowak", "newpassword")
    assert client.get("/api/me", headers=jan_headers).status_code == 200

    # Prevent self-deletion
    me = client.get("/api/me", headers=headers).json()
    self_del = client.delete(f"/api/users/{me['id']}", headers=headers)
    assert self_del.status_code == 400

    # Delete other user
    del_res = client.delete(f"/api/users/{new_user['id']}", headers=headers)
    assert del_res.status_code == 200


def test_processes_and_subprocesses_crud(client: TestClient):
    headers, _ = get_auth_headers(client)

    # Create process
    p_res = client.post("/api/processes", json={"name": "Development Process"}, headers=headers)
    assert p_res.status_code == 200
    proc = p_res.json()
    p_id = proc["id"]

    # Duplicate process check
    dup_p = client.post("/api/processes", json={"name": "Development Process"}, headers=headers)
    assert dup_p.status_code == 400

    # Rename process
    ren_p = client.put(f"/api/processes/{p_id}", json={"name": "R&D Process"}, headers=headers)
    assert ren_p.status_code == 200
    assert ren_p.json()["name"] == "R&D Process"

    # Create subprocesses
    sp1 = client.post(
        "/api/subprocesses",
        json={"name": "Architektura", "process_id": p_id},
        headers=headers,
    ).json()
    sp2 = client.post(
        "/api/subprocesses",
        json={"name": "Implementacja", "process_id": p_id},
        headers=headers,
    ).json()

    # Rename subprocess
    ren_sp = client.put(
        f"/api/subprocesses/{sp1['id']}",
        json={"name": "Projektowanie Architektury"},
        headers=headers,
    )
    assert ren_sp.status_code == 200
    assert ren_sp.json()["name"] == "Projektowanie Architektury"

    # Verify hierarchy
    all_procs = client.get("/api/processes", headers=headers).json()
    assert len(all_procs) == 1
    assert len(all_procs[0]["subprocesses"]) == 2

    # Delete subprocess
    del_sp = client.delete(f"/api/subprocesses/{sp2['id']}", headers=headers)
    assert del_sp.status_code == 200

    # Delete process
    del_p = client.delete(f"/api/processes/{p_id}", headers=headers)
    assert del_p.status_code == 200
    assert len(client.get("/api/processes", headers=headers).json()) == 0


def test_tasks_and_isolated_subprocess_completion(client: TestClient):
    headers, _ = get_auth_headers(client)

    # Setup process with 2 subprocesses
    proc = client.post("/api/processes", json={"name": "Produkcja"}, headers=headers).json()
    sp_analiza = client.post(
        "/api/subprocesses",
        json={"name": "Analiza", "process_id": proc["id"]},
        headers=headers,
    ).json()
    sp_testy = client.post(
        "/api/subprocesses",
        json={"name": "Testy", "process_id": proc["id"]},
        headers=headers,
    ).json()

    # Create Task A (auto-assigned to current_user when user_ids is empty)
    t_a_res = client.post(
        "/api/tasks",
        json={"numeric_id": 1001, "name": "Wdrożenie modułu A", "process_id": proc["id"], "user_ids": []},
        headers=headers,
    )
    assert t_a_res.status_code == 200, t_a_res.text
    task_a = t_a_res.json()
    assert task_a["numeric_id"] == 1001
    assert len(task_a["users"]) == 1
    assert task_a["users"][0]["username"] == "phx"

    # Duplicate numeric_id should return 400
    dup_task = client.post(
        "/api/tasks",
        json={"numeric_id": 1001, "name": "Duplikat", "process_id": proc["id"]},
        headers=headers,
    )
    assert dup_task.status_code == 400

    # Create Task B on the same process
    task_b = client.post(
        "/api/tasks",
        json={"numeric_id": 1002, "name": "Wdrożenie modułu B", "process_id": proc["id"]},
        headers=headers,
    ).json()

    # Toggle subprocess completion on Task A ONLY
    toggle_res = client.patch(
        f"/api/tasks/{task_a['id']}/subprocesses/{sp_analiza['id']}/toggle_complete",
        headers=headers,
    )
    assert toggle_res.status_code == 200
    assert sp_analiza["id"] in toggle_res.json()["completed_subprocess_ids"]

    # Verify Task B does NOT have sp_analiza marked as completed!
    tasks_list = client.get("/api/tasks", headers=headers).json()
    fetched_a = next(t for t in tasks_list if t["id"] == task_a["id"])
    fetched_b = next(t for t in tasks_list if t["id"] == task_b["id"])
    assert sp_analiza["id"] in fetched_a["completed_subprocess_ids"]
    assert sp_analiza["id"] not in fetched_b["completed_subprocess_ids"]
    assert sp_testy["id"] not in fetched_a["completed_subprocess_ids"]

    # Update Task A details
    upd_t = client.put(
        f"/api/tasks/{task_a['id']}",
        json={"numeric_id": 1005, "name": "Wdrożenie modułu A (v2)"},
        headers=headers,
    )
    assert upd_t.status_code == 200
    assert upd_t.json()["numeric_id"] == 1005

    # Toggle Task A completion
    comp_t = client.patch(f"/api/tasks/{task_a['id']}/toggle_complete", headers=headers)
    assert comp_t.status_code == 200
    assert comp_t.json()["completed"] is True


def test_time_allocation_timetable_and_reports(client: TestClient):
    headers, token = get_auth_headers(client)

    proc = client.post("/api/processes", json={"name": "Klient VIP"}, headers=headers).json()
    sp = client.post(
        "/api/subprocesses",
        json={"name": "Konsultacje", "process_id": proc["id"]},
        headers=headers,
    ).json()
    task = client.post(
        "/api/tasks",
        json={"numeric_id": 500, "name": "Audyt bezpieczeństwa", "process_id": proc["id"]},
        headers=headers,
    ).json()

    # Invalid 0s allocation should return 400
    bad_alloc = client.post(
        "/api/allocate",
        json={"task_id": task["id"], "subprocess_id": sp["id"], "time_allocated_seconds": 0},
        headers=headers,
    )
    assert bad_alloc.status_code == 400

    # Valid allocations (120s and 180s = 300s total)
    a1 = client.post(
        "/api/allocate",
        json={"task_id": task["id"], "subprocess_id": sp["id"], "time_allocated_seconds": 120},
        headers=headers,
    )
    assert a1.status_code == 200
    a2 = client.post(
        "/api/allocate",
        json={"task_id": task["id"], "subprocess_id": sp["id"], "time_allocated_seconds": 180},
        headers=headers,
    )
    assert a2.status_code == 200

    # Verify Task includes time_entries in /api/tasks
    tasks_data = client.get("/api/tasks", headers=headers).json()
    assert len(tasks_data[0]["time_entries"]) == 2
    total_sec = sum(e["time_allocated_seconds"] for e in tasks_data[0]["time_entries"])
    assert total_sec == 300

    # Verify /api/time-entries (Timetable endpoint)
    entries = client.get("/api/time-entries", headers=headers).json()
    assert len(entries) == 2
    assert entries[0]["task_numeric_id"] == 500
    assert entries[0]["process_name"] == "Klient VIP"
    assert entries[0]["subprocess_name"] == "Konsultacje"

    # Verify TXT Report
    txt_res = client.get(f"/api/report/allcharges?token={token}")
    assert txt_res.status_code == 200
    assert "ALL CHARGES REPORT" in txt_res.text
    assert "Klient VIP" in txt_res.text
    assert "Konsultacje" in txt_res.text

    # Verify CSV Report
    csv_res = client.get(f"/api/report/csv?token={token}")
    assert csv_res.status_code == 200
    assert "TaskID,TaskName,Proces,Subprocess,User,TimeAllocated(s),Start,Stop" in csv_res.text
    assert "500,Audyt bezpieczeństwa,Klient VIP,Konsultacje,phx" in csv_res.text

    # Delete one time entry and verify remaining is 1
    entry_id_to_del = entries[0]["id"]
    del_e = client.delete(f"/api/time-entries/{entry_id_to_del}", headers=headers)
    assert del_e.status_code == 200
    remaining = client.get("/api/time-entries", headers=headers).json()
    assert len(remaining) == 1


def test_user_assignment_and_cascade_cleanup(client: TestClient):
    headers, _ = get_auth_headers(client)

    # Create second user
    u2 = client.post(
        "/api/users",
        json={"username": "anna", "email": "anna@example.com", "password": "pass"},
        headers=headers,
    ).json()
    anna_headers, _ = get_auth_headers(client, "anna", "pass")

    proc = client.post("/api/processes", json={"name": "Marketing"}, headers=headers).json()
    sp = client.post(
        "/api/subprocesses",
        json={"name": "Kampania Social Media", "process_id": proc["id"]},
        headers=headers,
    ).json()

    # Create task assigned only to phx initially
    task = client.post(
        "/api/tasks",
        json={"numeric_id": 777, "name": "Kampania Q4", "process_id": proc["id"]},
        headers=headers,
    ).json()

    # Anna should have 0 assigned tasks initially
    assert len(client.get("/api/tasks", headers=anna_headers).json()) == 0
    # But all_data=true shows all tasks
    assert len(client.get("/api/tasks?all_data=true", headers=anna_headers).json()) == 1

    # Assign Anna to task
    assign_res = client.post(
        f"/api/tasks/{task['id']}/assign",
        json={"user_id": u2["id"]},
        headers=headers,
    )
    assert assign_res.status_code == 200
    assert len(client.get("/api/tasks", headers=anna_headers).json()) == 1

    # Unassign Anna from task
    unassign_res = client.delete(
        f"/api/tasks/{task['id']}/assign/{u2['id']}",
        headers=headers,
    )
    assert unassign_res.status_code == 200
    assert len(client.get("/api/tasks", headers=anna_headers).json()) == 0

    # Allocate time and mark subprocess completed, then delete process -> verify task survives with process_id=None
    client.post(
        "/api/allocate",
        json={"task_id": task["id"], "subprocess_id": sp["id"], "time_allocated_seconds": 60},
        headers=headers,
    )
    client.patch(f"/api/tasks/{task['id']}/subprocesses/{sp['id']}/toggle_complete", headers=headers)

    del_proc = client.delete(f"/api/processes/{proc['id']}", headers=headers)
    assert del_proc.status_code == 200

    surviving_tasks = client.get("/api/tasks", headers=headers).json()
    assert len(surviving_tasks) == 1
    assert surviving_tasks[0]["process_id"] is None

