from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import models, schemas, auth
from database import engine, SessionLocal
import datetime
import os
import csv
from io import StringIO
from typing import List
from pydantic import BaseModel
from sqlalchemy import text

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize default data and migrate history
def init_db():
    db = SessionLocal()
    
    # Ręczna migracja struktury (SQLAlchemy create_all nie dodaje kolumn do istniejących tabel)
    try:
        # Próba dodania kolumny user_id do time_entries
        db.execute(text("ALTER TABLE time_entries ADD COLUMN user_id INTEGER REFERENCES users(id)"))
        db.commit()
        print("Migracja: Dodano kolumnę user_id do tabeli time_entries.")
    except Exception:
        # Jeśli kolumna już istnieje, silnik rzuci błąd - ignorujemy go
        db.rollback()

    # Tworzenie brakujących tabel (task_users)
    models.Base.metadata.create_all(bind=engine)
    
    phx_user = db.query(models.User).filter(models.User.username == "phx").first()
    if not phx_user:
        hashed = auth.get_password_hash("0zKvUd8W@!P#MPpTWgA%")
        phx_user = models.User(username="phx", email="phx.poczta@gmail.com", hashed_password=hashed)
        db.add(phx_user)
        db.commit()
        db.refresh(phx_user)
    
    # Przebieg przez istniejące wpisy - przypisanie do phx
    unassigned_entries = db.query(models.TimeEntry).filter(models.TimeEntry.user_id == None).all()
    for entry in unassigned_entries:
        entry.user_id = phx_user.id
    
    unassigned_subprocesses = db.query(models.Subprocess).all()
    for sp in unassigned_subprocesses:
        if phx_user not in sp.users:
            sp.users.append(phx_user)

    db.commit()

    if not db.query(models.Process).first():
        p1 = models.Process(name="Proces 1")
        db.add(p1)
        db.commit()
        db.refresh(p1)
        for i in range(1, 4):
            sp = models.Subprocess(name=f"Subproces {i}", process_id=p1.id)
            sp.users.append(phx_user)
            db.add(sp)
        db.commit()
    db.close()

init_db()

# AUTHENTICATION
@app.post("/api/auth/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter((models.User.username == form_data.username) | (models.User.email == form_data.username)).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nieprawidłowy login lub hasło", headers={"WWW-Authenticate": "Bearer"})
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# USERS CRUD (Admin)
@app.get("/api/users", response_model=list[schemas.User])
def read_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.User).all()

@app.post("/api/users", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if db.query(models.User).filter((models.User.username == user.username) | (models.User.email == user.email)).first():
        raise HTTPException(status_code=400, detail="Użytkownik już istnieje")
    hashed = auth.get_password_hash(user.password)
    db_user = models.User(username=user.username, email=user.email, hashed_password=hashed)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.put("/api/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, options: schemas.UserUpdateOptions, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if options.username: db_user.username = options.username
    if options.email: db_user.email = options.email
    if options.password: db_user.hashed_password = auth.get_password_hash(options.password)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted"}

# API Endpoints (Secured)
@app.get("/api/processes", response_model=list[schemas.Process])
def read_processes(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    all_processes = db.query(models.Process).all()
    # Filtrujemy by odsyłać na front TYLKO "Tasks" (subprocesses) w których uczestniczy obecny user
    filtered_processes = []
    for p in all_processes:
        valid_sub = [sp for sp in p.subprocesses if current_user in sp.users]
        if valid_sub or not p.subprocesses:
            # Tworzymy kopię w locie by nie niszczyć obiektu w DB, ale do zwrotki schema wystarczy zmodyfikować klon
            p_copy = models.Process(id=p.id, name=p.name)
            p_copy.subprocesses = valid_sub
            filtered_processes.append(p_copy)
    return filtered_processes

@app.post("/api/processes", response_model=schemas.Process)
def create_process(process: schemas.ProcessCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_process = models.Process(name=process.name)
    db.add(db_process)
    db.commit()
    db.refresh(db_process)
    return db_process

@app.put("/api/processes/{p_id}", response_model=schemas.Process)
def update_process(p_id: int, process: schemas.ProcessBase, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_process = db.query(models.Process).filter(models.Process.id == p_id).first()
    db_process.name = process.name
    db.commit()
    db.refresh(db_process)
    return db_process

@app.delete("/api/processes/{p_id}")
def delete_process(p_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_process = db.query(models.Process).filter(models.Process.id == p_id).first()
    db.delete(db_process)
    db.commit()
    return {"message": "Process deleted"}

@app.post("/api/subprocesses", response_model=schemas.Subprocess)
def create_subprocess(subprocess: schemas.SubprocessCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_subprocess = models.Subprocess(name=subprocess.name, process_id=subprocess.process_id)
    # Kto tworzy taska - od razu do niego dołącza
    db_subprocess.users.append(current_user)
    db.add(db_subprocess)
    db.commit()
    db.refresh(db_subprocess)
    return db_subprocess

@app.put("/api/subprocesses/{sp_id}", response_model=schemas.Subprocess)
def update_subprocess(sp_id: int, subprocess: schemas.SubprocessBase, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_sp = db.query(models.Subprocess).filter(models.Subprocess.id == sp_id).first()
    db_sp.name = subprocess.name
    db.commit()
    db.refresh(db_sp)
    return db_sp

@app.delete("/api/subprocesses/{sp_id}")
def delete_subprocess(sp_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_sp = db.query(models.Subprocess).filter(models.Subprocess.id == sp_id).first()
    db.delete(db_sp)
    db.commit()
    return {"message": "Subprocess deleted"}

@app.patch("/api/subprocesses/{sp_id}/toggle_complete", response_model=schemas.Subprocess)
def toggle_subprocess(sp_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_sp = db.query(models.Subprocess).filter(models.Subprocess.id == sp_id).first()
    db_sp.completed = not db_sp.completed
    db.commit()
    db.refresh(db_sp)
    return db_sp

class AssignUserRequest(BaseModel):
    user_id: int

@app.post("/api/subprocesses/{sp_id}/assign")
def assign_user(sp_id: int, payload: AssignUserRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_sp = db.query(models.Subprocess).filter(models.Subprocess.id == sp_id).first()
    if not db_sp:
        raise HTTPException(status_code=404, detail="Task not found")
        
    user_to_add = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user_to_add not in db_sp.users:
        db_sp.users.append(user_to_add)
        db.commit()
    return {"message": "User assigned"}


@app.post("/api/subprocesses/{sp_id}/allocate", response_model=schemas.TimeEntry)
def allocate_time(sp_id: int, time_entry: schemas.TimeEntryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_sp = db.query(models.Subprocess).filter(models.Subprocess.id == sp_id).first()
    
    stop_time = datetime.datetime.utcnow()
    start_time = stop_time - datetime.timedelta(seconds=time_entry.time_allocated_seconds)
    
    db_entry = models.TimeEntry(
        subprocess_id=sp_id,
        user_id=current_user.id,
        time_allocated_seconds=time_entry.time_allocated_seconds,
        start_time=start_time,
        stop_time=stop_time
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

@app.get("/api/report/allcharges")
def generate_report(token: str, db: Session = Depends(get_db)):
    auth.get_current_user(token, db)
    entries = db.query(models.TimeEntry).all()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    lines = ["+-------------------------------------------------------------------------------------------------------------------+",
             "|                            ALL CHARGES REPORT - TIME TRACKER RETRO EXPORT                                 |",
             "+-------------------------------------------------------------------------------------------------------------------+",
             "| PROCES                  | SUBPROCESS              | USER                 | TIME (s) | START                | STOP                |",
             "+-------------------------------------------------------------------------------------------------------------------+"]
             
    for e in entries:
        sp = e.subprocess
        p = sp.process
        p_name = p.name[:23].ljust(23)
        sp_name = sp.name[:23].ljust(23)
        u_name = (e.user.username if e.user else "UNKNOWN")[:20].ljust(20)
        time_s = str(e.time_allocated_seconds).ljust(8)
        start_time = e.start_time.strftime("%Y-%m-%d %H:%M:%S")
        stop_time = e.stop_time.strftime("%Y-%m-%d %H:%M:%S")
        
        lines.append(f"| {p_name} | {sp_name} | {u_name} | {time_s} | {start_time}  | {stop_time}  |")
        
    lines.append("+-------------------------------------------------------------------------------------------------------------------+")
    content = "\n".join(lines)
    return PlainTextResponse(content, media_type="text/plain", headers={"Content-Disposition": f"attachment; filename=AllChargesReport_{timestamp}.txt"})

@app.get("/api/report/csv")
def generate_csv(token: str, db: Session = Depends(get_db)):
    auth.get_current_user(token, db)
    entries = db.query(models.TimeEntry).all()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Proces", "Subprocess", "User", "TimeAllocated(s)", "Start", "Stop"])
    for e in entries:
        sp = e.subprocess
        p = sp.process
        u_name = e.user.username if e.user else "UNKNOWN"
        writer.writerow([p.name, sp.name, u_name, e.time_allocated_seconds, e.start_time.isoformat(), e.stop_time.isoformat()])
        
    return PlainTextResponse(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=AllChargesReport_{timestamp}.csv"})

# Endpoint for frontend to fetch the current active user info
@app.get("/api/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
