from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from io import StringIO
import datetime
import os
import csv

import models, schemas, auth, database
from auth import get_db
from database import engine, SessionLocal

app = FastAPI(title="TimeTracker Pro API", version="2.0.0")
DB_INIT_ERROR: Optional[str] = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def init_db():
    db = SessionLocal()

    # 0. Naprawa starej tabeli asocjacyjnej (task_users) jeśli ma kolumnę subprocess_id
    try:
        db.execute(text("SELECT subprocess_id FROM task_users LIMIT 1"))
        db.execute(text("ALTER TABLE task_users RENAME TO task_users_old"))
        db.commit()
    except Exception:
        db.rollback()

    # 0.1 Tworzenie brakujących/nowych tabel (w tym task_subprocess_completions)
    models.Base.metadata.create_all(bind=engine)

    # 1. Ręczna migracja kolumn dla starszych baz
    for stmt in [
        "ALTER TABLE time_entries ADD COLUMN user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE time_entries ADD COLUMN task_id INTEGER REFERENCES tasks(id)",
        "ALTER TABLE tasks ADD COLUMN process_id INTEGER REFERENCES processes(id)",
    ]:
        try:
            db.execute(text(stmt))
            db.commit()
        except Exception:
            db.rollback()

    # 2. Tworzenie domyślnego użytkownika phx
    phx_user = db.query(models.User).filter(models.User.username == "phx").first()
    if not phx_user:
        hashed = auth.get_password_hash("0zKvUd8W@!P#MPpTWgA%")
        phx_user = models.User(
            username="phx",
            email="phx.poczta@gmail.com",
            hashed_password=hashed,
        )
        db.add(phx_user)
        db.commit()
        db.refresh(phx_user)

    # 3. Migracja osieroconych wpisów czasu do phx
    try:
        db.execute(text(f"UPDATE time_entries SET user_id = {phx_user.id} WHERE user_id IS NULL"))
        db.commit()
    except Exception:
        db.rollback()

    # 4. Domyślne Kategorie (Procesy i Subprocesy)
    p1 = db.query(models.Process).filter(models.Process.name == "Pulpit Wewnętrzny").first()
    if not p1:
        p1 = models.Process(name="Pulpit Wewnętrzny")
        db.add(p1)
        db.commit()
        db.refresh(p1)

        categories = ["Spotkanie", "Analiza", "Development", "Testowanie", "Dokumentacja"]
        for cat in categories:
            db_sp = models.Subprocess(name=cat, process_id=p1.id)
            db.add(db_sp)
        db.commit()

    # 5. Migracja Tasków do domyślnego procesu jeśli nie mają przypisania
    try:
        db.execute(text(f"UPDATE tasks SET process_id = {p1.id} WHERE process_id IS NULL"))
        db.commit()
    except Exception:
        db.rollback()

    db.close()


try:
    init_db()
except Exception as e:
    DB_INIT_ERROR = str(e)


# ==================== AUTHENTICATION ====================

@app.post("/api/auth/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = (
        db.query(models.User)
        .filter(
            (models.User.username == form_data.username)
            | (models.User.email == form_data.username)
        )
        .first()
    )
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy login lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# ==================== USERS CRUD ====================

@app.get("/api/users", response_model=list[schemas.User])
def read_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.User).order_by(models.User.id).all()


@app.post("/api/users", response_model=schemas.User)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    existing = (
        db.query(models.User)
        .filter(
            (models.User.username == user.username)
            | ((models.User.email == user.email) & (models.User.email != ""))
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Użytkownik o tej nazwie lub e-mailu już istnieje")
    hashed = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email or f"{user.username}@local",
        hashed_password=hashed,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.put("/api/users/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    options: schemas.UserUpdateOptions,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
    if options.username:
        db_user.username = options.username
    if options.email:
        db_user.email = options.email
    if options.password:
        db_user.hashed_password = auth.get_password_hash(options.password)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.delete("/api/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Nie możesz usunąć aktualnie zalogowanego konta")
    db_user.assigned_tasks.clear()
    db.query(models.TimeEntry).filter(models.TimeEntry.user_id == user_id).update({"user_id": None})
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted"}


# ==================== PROCESSES & SUBPROCESSES ====================

@app.get("/api/processes", response_model=list[schemas.Process])
def read_processes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.Process).order_by(models.Process.id).all()


@app.post("/api/processes", response_model=schemas.Process)
def create_process(
    process: schemas.ProcessCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    existing = db.query(models.Process).filter(models.Process.name == process.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Proces o takiej nazwie już istnieje")
    db_process = models.Process(name=process.name)
    db.add(db_process)
    db.commit()
    db.refresh(db_process)
    return db_process


@app.put("/api/processes/{p_id}", response_model=schemas.Process)
def update_process(
    p_id: int,
    process: schemas.ProcessBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_process = db.query(models.Process).filter(models.Process.id == p_id).first()
    if not db_process:
        raise HTTPException(status_code=404, detail="Nie znaleziono procesu")
    db_process.name = process.name
    db.commit()
    db.refresh(db_process)
    return db_process


@app.delete("/api/processes/{p_id}")
def delete_process(
    p_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_process = db.query(models.Process).filter(models.Process.id == p_id).first()
    if not db_process:
        raise HTTPException(status_code=404, detail="Nie znaleziono procesu")
    db.query(models.Task).filter(models.Task.process_id == p_id).update({"process_id": None})
    for sp in db_process.subprocesses:
        db.query(models.TaskSubprocessCompletion).filter(
            models.TaskSubprocessCompletion.subprocess_id == sp.id
        ).delete()
        db.query(models.TimeEntry).filter(models.TimeEntry.subprocess_id == sp.id).delete()
    db.delete(db_process)
    db.commit()
    return {"message": "Process deleted"}


@app.post("/api/subprocesses", response_model=schemas.Subprocess)
def create_subprocess(
    subprocess: schemas.SubprocessCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_subprocess = models.Subprocess(
        name=subprocess.name,
        process_id=subprocess.process_id,
    )
    db.add(db_subprocess)
    db.commit()
    db.refresh(db_subprocess)
    return db_subprocess


@app.put("/api/subprocesses/{id}", response_model=schemas.Subprocess)
def update_subprocess(
    id: int,
    sp: schemas.SubprocessUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_sp = db.query(models.Subprocess).filter(models.Subprocess.id == id).first()
    if not db_sp:
        raise HTTPException(status_code=404, detail="Nie znaleziono subprocesu")
    db_sp.name = sp.name
    db.commit()
    db.refresh(db_sp)
    return db_sp


@app.patch("/api/subprocesses/{id}/toggle_complete", response_model=schemas.Subprocess)
def toggle_subprocess_complete(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_sp = db.query(models.Subprocess).filter(models.Subprocess.id == id).first()
    if not db_sp:
        raise HTTPException(status_code=404, detail="Nie znaleziono subprocesu")
    db_sp.completed = not db_sp.completed
    db.commit()
    db.refresh(db_sp)
    return db_sp


@app.delete("/api/subprocesses/{id}")
def delete_subprocess(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_sp = db.query(models.Subprocess).filter(models.Subprocess.id == id).first()
    if not db_sp:
        raise HTTPException(status_code=404, detail="Nie znaleziono subprocesu")
    db.query(models.TaskSubprocessCompletion).filter(
        models.TaskSubprocessCompletion.subprocess_id == id
    ).delete()
    db.query(models.TimeEntry).filter(models.TimeEntry.subprocess_id == id).delete()
    db.delete(db_sp)
    db.commit()
    return {"message": "Subprocess deleted"}


# ==================== TASKS (WORK TICKETS) ====================

@app.get("/api/tasks", response_model=list[schemas.Task])
def read_tasks(
    all_data: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if all_data:
        return db.query(models.Task).order_by(models.Task.numeric_id).all()
    return (
        db.query(models.Task)
        .filter(models.Task.users.contains(current_user))
        .order_by(models.Task.numeric_id)
        .all()
    )


@app.post("/api/tasks", response_model=schemas.Task)
def create_task(
    task: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    existing = db.query(models.Task).filter(models.Task.numeric_id == task.numeric_id).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Ticket o numerze ID {task.numeric_id} już istnieje ({existing.name})",
        )

    db_task = models.Task(
        numeric_id=task.numeric_id,
        name=task.name,
        process_id=task.process_id,
    )

    if task.user_ids:
        for u_id in task.user_ids:
            u = db.query(models.User).filter(models.User.id == u_id).first()
            if u and u not in db_task.users:
                db_task.users.append(u)
    else:
        db_task.users.append(current_user)

    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@app.put("/api/tasks/{t_id}", response_model=schemas.Task)
def update_task(
    t_id: int,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_task = db.query(models.Task).filter(models.Task.id == t_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Nie znaleziono zadania")

    if payload.numeric_id is not None and payload.numeric_id != db_task.numeric_id:
        dup = db.query(models.Task).filter(models.Task.numeric_id == payload.numeric_id).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"Ticket ID {payload.numeric_id} jest już zajęty")
        db_task.numeric_id = payload.numeric_id

    if payload.name is not None:
        db_task.name = payload.name
    if payload.process_id is not None:
        db_task.process_id = payload.process_id
    if payload.completed is not None:
        db_task.completed = payload.completed
    if payload.user_ids is not None:
        users = db.query(models.User).filter(models.User.id.in_(payload.user_ids)).all()
        db_task.users = users

    db.commit()
    db.refresh(db_task)
    return db_task


@app.delete("/api/tasks/{t_id}")
def delete_task(
    t_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_task = db.query(models.Task).filter(models.Task.id == t_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Nie znaleziono zadania")
    db_task.users.clear()
    db.query(models.TaskSubprocessCompletion).filter(
        models.TaskSubprocessCompletion.task_id == t_id
    ).delete()
    db.query(models.TimeEntry).filter(models.TimeEntry.task_id == t_id).delete()
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted"}


@app.patch("/api/tasks/{t_id}/toggle_complete", response_model=schemas.Task)
def toggle_task(
    t_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_task = db.query(models.Task).filter(models.Task.id == t_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Nie znaleziono zadania")
    db_task.completed = not db_task.completed
    db.commit()
    db.refresh(db_task)
    return db_task


@app.patch("/api/tasks/{t_id}/subprocesses/{sp_id}/toggle_complete", response_model=schemas.Task)
def toggle_task_subprocess_complete(
    t_id: int,
    sp_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_task = db.query(models.Task).filter(models.Task.id == t_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Nie znaleziono zadania")

    record = (
        db.query(models.TaskSubprocessCompletion)
        .filter(
            models.TaskSubprocessCompletion.task_id == t_id,
            models.TaskSubprocessCompletion.subprocess_id == sp_id,
        )
        .first()
    )
    if record:
        record.completed = not record.completed
    else:
        record = models.TaskSubprocessCompletion(
            task_id=t_id,
            subprocess_id=sp_id,
            completed=True,
        )
        db.add(record)

    db.commit()
    db.refresh(db_task)
    return db_task


class AssignUserRequest(BaseModel):
    user_id: int


@app.post("/api/tasks/{t_id}/assign", response_model=schemas.Task)
def assign_task_user(
    t_id: int,
    payload: AssignUserRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_task = db.query(models.Task).filter(models.Task.id == t_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Nie znaleziono zadania")
    user_to_add = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not user_to_add:
        raise HTTPException(status_code=404, detail="Nie znaleziono użytkownika")
    if user_to_add not in db_task.users:
        db_task.users.append(user_to_add)
        db.commit()
        db.refresh(db_task)
    return db_task


@app.delete("/api/tasks/{t_id}/assign/{user_id}", response_model=schemas.Task)
def unassign_task_user(
    t_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_task = db.query(models.Task).filter(models.Task.id == t_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Nie znaleziono zadania")
    user_to_remove = db.query(models.User).filter(models.User.id == user_id).first()
    if user_to_remove and user_to_remove in db_task.users:
        db_task.users.remove(user_to_remove)
        db.commit()
        db.refresh(db_task)
    return db_task


# ==================== TIME ALLOCATION & ENTRIES ====================

@app.post("/api/allocate", response_model=schemas.TimeEntry)
def allocate_time(
    time_entry: schemas.TimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if time_entry.time_allocated_seconds <= 0:
        raise HTTPException(status_code=400, detail="Czas alokacji musi być większy od 0 sekund")

    stop_time = datetime.datetime.now()
    start_time = stop_time - datetime.timedelta(seconds=time_entry.time_allocated_seconds)

    db_entry = models.TimeEntry(
        task_id=time_entry.task_id,
        subprocess_id=time_entry.subprocess_id,
        user_id=current_user.id,
        time_allocated_seconds=time_entry.time_allocated_seconds,
        start_time=start_time,
        stop_time=stop_time,
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


@app.get("/api/time-entries", response_model=list[schemas.TimeEntryDetail])
def get_time_entries(
    date_str: Optional[str] = None,
    all_users: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    query = db.query(models.TimeEntry)
    if not all_users:
        query = query.filter(models.TimeEntry.user_id == current_user.id)

    entries = query.order_by(models.TimeEntry.stop_time.desc()).all()
    results = []
    for e in entries:
        entry_date = e.start_time.strftime("%Y-%m-%d") if e.start_time else ""
        if date_str and entry_date != date_str:
            continue
        t = e.task
        sp = e.subprocess
        p = sp.process if sp and sp.process else (t.process if t and t.process else None)
        results.append(
            schemas.TimeEntryDetail(
                id=e.id,
                task_id=t.id if t else e.task_id,
                task_numeric_id=t.numeric_id if t else None,
                task_name=t.name if t else "Usunięty Ticket",
                process_id=p.id if p else None,
                process_name=p.name if p else "Brak Procesu",
                subprocess_id=sp.id if sp else e.subprocess_id,
                subprocess_name=sp.name if sp else "Usunięta Kategoria",
                user_id=e.user_id,
                username=e.user.username if e.user else "UNKNOWN",
                time_allocated_seconds=e.time_allocated_seconds,
                start_time=e.start_time,
                stop_time=e.stop_time,
            )
        )
    return results


@app.delete("/api/time-entries/{entry_id}")
def delete_time_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    entry = db.query(models.TimeEntry).filter(models.TimeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Nie znaleziono wpisu czasu")
    db.delete(entry)
    db.commit()
    return {"message": "Time entry deleted"}


# ==================== REPORTING ====================

@app.get("/api/report/allcharges")
def generate_report(token: str, db: Session = Depends(get_db)):
    auth.get_current_user(token, db)
    entries = db.query(models.TimeEntry).order_by(models.TimeEntry.start_time.desc()).all()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    lines = [
        "+-----------------------------------------------------------------------------------------------------------------------------+",
        "|                                ALL CHARGES REPORT - TIME TRACKER RETRO EXPORT                                               |",
        "+-----------------------------------------------------------------------------------------------------------------------------+",
        "| TASK ID | PROCES                  | SUBPROCESS              | USER                 | TIME (s) | START               | STOP                |",
        "+-----------------------------------------------------------------------------------------------------------------------------+",
    ]

    for e in entries:
        t = e.task
        sp = e.subprocess
        p = sp.process if sp and sp.process else (t.process if t and t.process else None)
        t_id = str(t.numeric_id if t else "N/A").ljust(7)
        p_name = (p.name if p else "N/A")[:23].ljust(23)
        sp_name = (sp.name if sp else "N/A")[:23].ljust(23)
        u_name = (e.user.username if e.user else "UNKNOWN")[:20].ljust(20)
        time_s = str(e.time_allocated_seconds).ljust(8)
        start_time = e.start_time.strftime("%Y-%m-%d %H:%M:%S")
        stop_time = e.stop_time.strftime("%Y-%m-%d %H:%M:%S")

        lines.append(
            f"| {t_id} | {p_name} | {sp_name} | {u_name} | {time_s} | {start_time} | {stop_time} |"
        )

    lines.append(
        "+-----------------------------------------------------------------------------------------------------------------------------+"
    )
    content = "\n".join(lines)
    return PlainTextResponse(
        content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=AllChargesReport_{timestamp}.txt"},
    )


@app.get("/api/report/csv")
def generate_csv(token: str, db: Session = Depends(get_db)):
    auth.get_current_user(token, db)
    entries = db.query(models.TimeEntry).order_by(models.TimeEntry.start_time.desc()).all()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["TaskID", "TaskName", "Proces", "Subprocess", "User", "TimeAllocated(s)", "Start", "Stop"])
    for e in entries:
        t = e.task
        sp = e.subprocess
        p = sp.process if sp and sp.process else (t.process if t and t.process else None)
        u_name = e.user.username if e.user else "UNKNOWN"
        writer.writerow([
            t.numeric_id if t else "N/A",
            t.name if t else "N/A",
            p.name if p else "N/A",
            sp.name if sp else "N/A",
            u_name,
            e.time_allocated_seconds,
            e.start_time.isoformat(),
            e.stop_time.isoformat(),
        ])

    return PlainTextResponse(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=AllChargesReport_{timestamp}.csv"},
    )


# ==================== STATIC & SPA SERVING ====================

@app.get("/api/health")
def health_check():
    db_type = "sqlite" if database.is_sqlite else "postgresql"
    return {
        "status": "ok" if not (DB_INIT_ERROR or database.ENGINE_ERROR) else "degraded",
        "version": "2.0.0",
        "database": db_type,
        "driver": database.ACTIVE_DRIVER,
        "env_key": database.matched_env_key,
        "engine_error": database.ENGINE_ERROR,
        "db_init_error": DB_INIT_ERROR,
    }


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
if os.path.isdir(os.path.join(FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")


@app.get("/")
def read_index():
    dist_index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.isfile(dist_index):
        return FileResponse(dist_index)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
