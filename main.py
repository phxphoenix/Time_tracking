from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import models, schemas
from database import engine, SessionLocal
import datetime
import os

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize default data
def init_db():
    db = SessionLocal()
    if not db.query(models.Process).first():
        p1 = models.Process(name="Proces 1")
        db.add(p1)
        db.commit()
        db.refresh(p1)
        for i in range(1, 4):
            sp = models.Subprocess(name=f"Subproces {i}", process_id=p1.id)
            db.add(sp)
        db.commit()
    db.close()

init_db()

# API Endpoints
@app.get("/api/processes", response_model=list[schemas.Process])
def read_processes(db: Session = Depends(get_db)):
    processes = db.query(models.Process).all()
    return processes

@app.post("/api/processes", response_model=schemas.Process)
def create_process(process: schemas.ProcessCreate, db: Session = Depends(get_db)):
    db_process = models.Process(name=process.name)
    db.add(db_process)
    db.commit()
    db.refresh(db_process)
    return db_process

@app.post("/api/subprocesses", response_model=schemas.Subprocess)
def create_subprocess(subprocess: schemas.SubprocessCreate, db: Session = Depends(get_db)):
    db_subprocess = models.Subprocess(name=subprocess.name, process_id=subprocess.process_id)
    db.add(db_subprocess)
    db.commit()
    db.refresh(db_subprocess)
    return db_subprocess

@app.patch("/api/subprocesses/{sp_id}/toggle_complete", response_model=schemas.Subprocess)
def toggle_subprocess(sp_id: int, db: Session = Depends(get_db)):
    db_sp = db.query(models.Subprocess).filter(models.Subprocess.id == sp_id).first()
    if not db_sp:
        raise HTTPException(status_code=404, detail="Subprocess not found")
    db_sp.completed = not db_sp.completed
    db.commit()
    db.refresh(db_sp)
    return db_sp

@app.put("/api/processes/{p_id}", response_model=schemas.Process)
def update_process(p_id: int, process: schemas.ProcessBase, db: Session = Depends(get_db)):
    db_process = db.query(models.Process).filter(models.Process.id == p_id).first()
    if not db_process:
        raise HTTPException(status_code=404, detail="Process not found")
    db_process.name = process.name
    db.commit()
    db.refresh(db_process)
    return db_process

@app.put("/api/subprocesses/{sp_id}", response_model=schemas.Subprocess)
def update_subprocess(sp_id: int, subprocess: schemas.SubprocessBase, db: Session = Depends(get_db)):
    db_sp = db.query(models.Subprocess).filter(models.Subprocess.id == sp_id).first()
    if not db_sp:
        raise HTTPException(status_code=404, detail="Subprocess not found")
    db_sp.name = subprocess.name
    db.commit()
    db.refresh(db_sp)
    return db_sp

@app.delete("/api/processes/{p_id}")
def delete_process(p_id: int, db: Session = Depends(get_db)):
    db_process = db.query(models.Process).filter(models.Process.id == p_id).first()
    if not db_process:
        raise HTTPException(status_code=404, detail="Process not found")
    db.delete(db_process)
    db.commit()
    return {"message": "Process deleted"}

@app.delete("/api/subprocesses/{sp_id}")
def delete_subprocess(sp_id: int, db: Session = Depends(get_db)):
    db_sp = db.query(models.Subprocess).filter(models.Subprocess.id == sp_id).first()
    if not db_sp:
        raise HTTPException(status_code=404, detail="Subprocess not found")
    db.delete(db_sp)
    db.commit()
    return {"message": "Subprocess deleted"}

@app.post("/api/subprocesses/{sp_id}/allocate", response_model=schemas.TimeEntry)
def allocate_time(sp_id: int, time_entry: schemas.TimeEntryCreate, db: Session = Depends(get_db)):
    db_sp = db.query(models.Subprocess).filter(models.Subprocess.id == sp_id).first()
    if not db_sp:
        raise HTTPException(status_code=404, detail="Subprocess not found")
    
    stop_time = datetime.datetime.utcnow()
    start_time = stop_time - datetime.timedelta(seconds=time_entry.time_allocated_seconds)
    
    db_entry = models.TimeEntry(
        subprocess_id=sp_id,
        time_allocated_seconds=time_entry.time_allocated_seconds,
        start_time=start_time,
        stop_time=stop_time
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

@app.get("/api/report/allcharges")
def generate_report(db: Session = Depends(get_db)):
    entries = db.query(models.TimeEntry).all()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    lines = ["+-------------------------------------------------------------------------------------------------------+",
             "|                            ALL CHARGES REPORT - TIME TRACKER RETRO EXPORT                             |",
             "+-------------------------------------------------------------------------------------------------------+",
             "| PROCES                  | SUBPROCESS              | TIME (s) | START                | STOP                |",
             "+-------------------------------------------------------------------------------------------------------+"]
             
    for e in entries:
        sp = e.subprocess
        p = sp.process
        p_name = p.name[:23].ljust(23)
        sp_name = sp.name[:23].ljust(23)
        time_s = str(e.time_allocated_seconds).ljust(8)
        start_time = e.start_time.strftime("%Y-%m-%d %H:%M:%S")
        stop_time = e.stop_time.strftime("%Y-%m-%d %H:%M:%S")
        
        lines.append(f"| {p_name} | {sp_name} | {time_s} | {start_time}  | {stop_time}  |")
        
    lines.append("+-------------------------------------------------------------------------------------------------------+")
    content = "\n".join(lines)
    return PlainTextResponse(content, media_type="text/plain", headers={"Content-Disposition": f"attachment; filename=AllChargesReport_{timestamp}.txt"})

@app.get("/api/report/csv")
def generate_csv(db: Session = Depends(get_db)):
    import csv
    from io import StringIO
    entries = db.query(models.TimeEntry).all()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Proces", "Subprocess", "TimeAllocated(s)", "Start", "Stop"])
    for e in entries:
        sp = e.subprocess
        p = sp.process
        writer.writerow([p.name, sp.name, e.time_allocated_seconds, e.start_time.isoformat(), e.stop_time.isoformat()])
        
    return PlainTextResponse(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=AllChargesReport_{timestamp}.csv"})

# Static Files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
