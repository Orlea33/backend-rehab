from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List
import random
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pydantic import BaseModel

from database import engine, get_db
import models
import schemas
from ml.model import load_model, load_materi
from schemas import UserUpdate, FeedbackCreate
from auth import (
    authenticate_user, create_access_token, get_current_active_user,
    get_current_admin_user, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash
)

load_dotenv()

# Inisialisasi database (buat semua tabel)
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load model ML
model_data = load_model()
model = model_data['model']
pendidikan_map = model_data['pendidikan_map']
format_map = model_data['format_map']
topik_map = model_data['topik_map']
type_map = model_data['type_map']

topik_reverse = {v: k for k, v in topik_map.items()}
type_reverse = {v: k for k, v in type_map.items()}
materi_list = load_materi()

# Schema untuk login JSON
class LoginRequest(BaseModel):
    nama: str
    password: str

# ========== ENDPOINTS AUTENTIKASI ==========
@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.nama == user.nama).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Nama sudah digunakan")
    hashed = get_password_hash(user.password)
    group = 'A' if random.random() < 0.5 else 'B'
    db_user = models.User(
        nama=user.nama,
        password=hashed,
        usia=user.usia,
        gender=user.gender,
        pendidikan=user.pendidikan,
        kecamatan=user.kecamatan,
        informed_consent=user.informed_consent,
        pretest_answers=user.pretest_answers,
        pretest_score=user.pretest_score,
        preferensi_format=user.preferensi_format,
        preferensi_waktu=user.preferensi_waktu,
        preferensi_topik=user.preferensi_topik,
        group=group
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nama atau password salah",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/login")
async def login_json(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.nama, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Nama atau password salah")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "nama": user.nama,
            "group": user.group,
            "is_admin": user.is_admin
        }
    }

@app.get("/users/me", response_model=schemas.UserOut)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

@app.post("/logout")
async def logout(response: JSONResponse):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}

# ========== ENDPOINTS MATERI ==========
@app.get("/contents", response_model=List[schemas.MateriOut])
def get_contents(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return db.query(models.Materi).offset(skip).limit(limit).all()

@app.get("/contents/{materi_id}", response_model=schemas.MateriOut)
def get_content(materi_id: int, db: Session = Depends(get_db)):
    materi = db.query(models.Materi).filter(models.Materi.id == materi_id).first()
    if not materi:
        raise HTTPException(status_code=404, detail="Materi not found")
    return materi

# ========== ENDPOINTS REKOMENDASI (HANYA GRUP A) ==========
@app.get("/recommendations", response_model=List[schemas.RecommendationOut])
def get_recommendations(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user = current_user
    if user.group != 'A':
        return []
    try:
        usia = user.usia
        pendidikan = pendidikan_map[user.pendidikan]
        gender = 1 if user.gender == 'L' else 0
        pretest = user.pretest_score
        pref_format = format_map[user.preferensi_format]
        pref_topik = topik_map[user.preferensi_topik]
    except KeyError as e:
        print(f"KeyError: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid preference: {e}")

    materi_db = db.query(models.Materi).all()
    fitur_matrix = []
    valid_materi = []
    for materi in materi_db:
        try:
            m_type = type_map[materi.type]
            m_category = topik_map[materi.category]
        except KeyError:
            continue
        fitur = [usia, pendidikan, gender, pretest, pref_format, pref_topik, m_type, m_category]
        fitur_matrix.append(fitur)
        valid_materi.append(materi)

    if fitur_matrix:
        prob_matrix = model.predict_proba(fitur_matrix)[:, 1]
    else:
        prob_matrix = []

    recommendations = []
    for materi, prob in zip(valid_materi, prob_matrix):
        confidence = round(prob * 100, 2)
        reasons = []
        if user.preferensi_format == 'campuran' or materi.type == user.preferensi_format:
            reasons.append(f"Format {materi.type} sesuai preferensi")
        if materi.category == user.preferensi_topik:
            reasons.append(f"Topik {materi.category} sesuai minat")
        if pretest > 10 and materi.type == 'artikel':
            reasons.append("Skor pretest tinggi cocok dengan artikel")
        elif pretest < 5 and materi.type == 'video':
            reasons.append("Skor pretest rendah cocok dengan video")
        reason = ", ".join(reasons) if reasons else "Berdasarkan analisis profil"
        recommendations.append({
            "materi": materi,
            "confidence": confidence,
            "reason": reason
        })

    recommendations.sort(key=lambda x: x['confidence'], reverse=True)
    return recommendations

# ========== ENDPOINTS TRACKING ==========
@app.post("/track")
def track_interaction(
    interaction: schemas.InteractionCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if interaction.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Tidak bisa track untuk user lain")
    db_interaction = models.Interaction(
        user_id=interaction.user_id,
        materi_id=interaction.materi_id,
        action=interaction.action,
        duration=interaction.duration
    )
    db.add(db_interaction)
    db.commit()
    return {"status": "ok"}

# ========== ENDPOINTS POST-TEST ==========
@app.post("/posttest")
def submit_posttest(
    posttest: schemas.PostTestCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    existing = db.query(models.PostTest).filter(models.PostTest.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Post-test sudah pernah dikerjakan")
    db_posttest = models.PostTest(
        user_id=current_user.id,
        answers=posttest.answers,
        score=posttest.score
    )
    db.add(db_posttest)
    db.commit()
    return {"status": "ok", "score": posttest.score}

# ========== ENDPOINTS PROGRESS & ACHIEVEMENTS ==========
@app.get("/user/progress")
def get_user_progress(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user = current_user
    total_materi = db.query(models.Materi).count()
    completed_count = db.query(models.Interaction).filter(
        models.Interaction.user_id == user.id,
        models.Interaction.action == 'complete'
    ).count()
    total_duration = db.query(func.sum(models.Interaction.duration)).filter(
        models.Interaction.user_id == user.id,
        models.Interaction.action == 'close',
        models.Interaction.duration.isnot(None)
    ).scalar() or 0

    thirty_days_ago = datetime.now() - timedelta(days=30)
    interaction_dates = db.query(
        func.date(models.Interaction.timestamp)
    ).filter(
        models.Interaction.user_id == user.id,
        models.Interaction.timestamp >= thirty_days_ago
    ).distinct().all()
    dates = [d[0] for d in interaction_dates]
    dates.sort(reverse=True)
    streak = 0
    if dates:
        today = datetime.now().date()
        if dates[0] == today:
            streak = 1
            for i in range(1, len(dates)):
                if (dates[i-1] - dates[i]).days == 1:
                    streak += 1
                else:
                    break
        else:
            streak = 0

    last_7_days = [(datetime.now().date() - timedelta(days=i)) for i in range(7)]
    interaction_last_7 = db.query(func.date(models.Interaction.timestamp)).filter(
        models.Interaction.user_id == user.id,
        models.Interaction.timestamp >= last_7_days[-1]
    ).distinct().count()
    consistency = round((interaction_last_7 / 7) * 100)

    last_posttest = db.query(models.PostTest).filter(
        models.PostTest.user_id == user.id
    ).order_by(desc(models.PostTest.submitted_at)).first()
    posttest_score = last_posttest.score if last_posttest else None

    return {
        "total_materi": total_materi,
        "completed_count": completed_count,
        "total_duration": total_duration,
        "streak": streak,
        "consistency": consistency,
        "pretest_score": user.pretest_score,
        "posttest_score": posttest_score
    }

@app.get("/user/weekly-activity")
def get_weekly_activity(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user = current_user
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=6)
    results = db.query(
        func.date(models.Interaction.timestamp).label('date'),
        func.sum(models.Interaction.duration).label('total_duration')
    ).filter(
        models.Interaction.user_id == user.id,
        models.Interaction.action == 'close',
        models.Interaction.duration.isnot(None),
        func.date(models.Interaction.timestamp) >= start_date,
        func.date(models.Interaction.timestamp) <= end_date
    ).group_by(func.date(models.Interaction.timestamp)).all()

    days_indonesia = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
    activity = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        total = next((r.total_duration for r in results if r.date == day), 0)
        minutes = total // 60 if total else 0
        activity.append({
            "day": days_indonesia[day.weekday()],
            "minutes": minutes
        })
    return activity

@app.get("/user/achievements")
def get_user_achievements(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user = current_user
    completed_count = db.query(models.Interaction).filter(
        models.Interaction.user_id == user.id,
        models.Interaction.action == 'complete'
    ).count()
    artikel_count = db.query(models.Interaction).join(models.Materi).filter(
        models.Interaction.user_id == user.id,
        models.Interaction.action == 'complete',
        models.Materi.type == 'artikel'
    ).count()
    video_count = db.query(models.Interaction).join(models.Materi).filter(
        models.Interaction.user_id == user.id,
        models.Interaction.action == 'complete',
        models.Materi.type == 'video'
    ).count()

    thirty_days_ago = datetime.now() - timedelta(days=30)
    interaction_dates = db.query(
        func.date(models.Interaction.timestamp)
    ).filter(
        models.Interaction.user_id == user.id,
        models.Interaction.timestamp >= thirty_days_ago
    ).distinct().all()
    dates = [d[0] for d in interaction_dates]
    dates.sort(reverse=True)
    streak = 0
    if dates:
        today = datetime.now().date()
        if dates[0] == today:
            streak = 1
            for i in range(1, len(dates)):
                if (dates[i-1] - dates[i]).days == 1:
                    streak += 1
                else:
                    break
        else:
            streak = 0

    last_posttest = db.query(models.PostTest).filter(
        models.PostTest.user_id == user.id
    ).order_by(desc(models.PostTest.submitted_at)).first()
    posttest_score = last_posttest.score if last_posttest else 0
    total_materi = db.query(models.Materi).count()

    achievements = [
        {"icon": "🌟", "name": "First Step", "desc": "Selesaikan 1 modul", "unlocked": completed_count >= 1},
        {"icon": "📖", "name": "Bookworm", "desc": "Baca 3 artikel", "unlocked": artikel_count >= 3, "progress": min(artikel_count, 3), "total": 3},
        {"icon": "🎥", "name": "Video Learner", "desc": "Tonton 2 video", "unlocked": video_count >= 2, "progress": min(video_count, 2), "total": 2},
        {"icon": "🔥", "name": "On Fire", "desc": "7 hari streak", "unlocked": streak >= 7, "progress": min(streak, 7), "total": 7},
        {"icon": "🏆", "name": "Master", "desc": "Selesaikan semua modul", "unlocked": completed_count >= total_materi, "progress": min(completed_count, total_materi), "total": total_materi},
        {"icon": "🧠", "name": "Knowledge Keeper", "desc": "Post-test >90%", "unlocked": posttest_score >= 14, "progress": posttest_score, "total": 15}
    ]
    return achievements

# ========== ENDPOINTS UPDATE PROFIL ==========
@app.put("/users/me", response_model=schemas.UserOut)
def update_user(
    user_update: UserUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    db.commit()
    return current_user

# ========== ENDPOINTS FEEDBACK ==========
@app.post("/feedback")
def create_feedback(
    feedback: schemas.FeedbackCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_feedback = models.Feedback(
        user_id=current_user.id,
        rating=feedback.rating,
        comment=feedback.comment
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return {"message": "Feedback submitted"}

# ========== ENDPOINTS STATISTIK PUBLIK ==========
@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_users = db.query(models.User).count()
    total_materi = db.query(models.Materi).count()
    avg_posttest = db.query(func.avg(models.PostTest.score)).scalar() or 0
    avg_percentage = round((avg_posttest / 15) * 100) if avg_posttest else 0
    return {
        "total_users": total_users,
        "total_materi": total_materi,
        "avg_understanding": avg_percentage,
        "algorithm": "RF"
    }

# ========== ENDPOINTS ADMIN ==========
@app.get("/admin/users")
def admin_get_users(
    admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    latest_posttest = (
        db.query(
            models.PostTest.user_id,
            models.PostTest.score.label('posttest_score')
        )
        .distinct(models.PostTest.user_id)
        .order_by(models.PostTest.user_id, desc(models.PostTest.submitted_at))
        .subquery()
    )
    users = (
        db.query(models.User, latest_posttest.c.posttest_score)
        .outerjoin(latest_posttest, models.User.id == latest_posttest.c.user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    result = []
    for user, posttest_score in users:
        result.append({
            "id": user.id,
            "nama": user.nama,
            "usia": user.usia,
            "gender": user.gender,
            "pendidikan": user.pendidikan,
            "kecamatan": user.kecamatan,
            "pretest_score": user.pretest_score,
            "posttest_score": posttest_score,
            "group": user.group,
            "created_at": user.created_at,
            "is_admin": user.is_admin
        })
    return result

@app.get("/admin/feedbacks")
def admin_get_feedbacks(
    admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    feedbacks = db.query(models.Feedback).offset(skip).limit(limit).all()
    return feedbacks

@app.get("/admin/materi")
def admin_get_materi(
    admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    materi = db.query(models.Materi).offset(skip).limit(limit).all()
    return materi

@app.post("/admin/materi")
def admin_create_materi(
    materi: schemas.MateriCreate,
    admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    db_materi = models.Materi(**materi.dict())
    db.add(db_materi)
    db.commit()
    db.refresh(db_materi)
    return db_materi

@app.put("/admin/materi/{materi_id}")
def admin_update_materi(
    materi_id: int,
    materi_update: schemas.MateriUpdate,
    admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    db_materi = db.query(models.Materi).filter(models.Materi.id == materi_id).first()
    if not db_materi:
        raise HTTPException(status_code=404, detail="Materi not found")
    for key, value in materi_update.dict(exclude_unset=True).items():
        setattr(db_materi, key, value)
    db.commit()
    db.refresh(db_materi)
    return db_materi

@app.delete("/admin/materi/{materi_id}")
def admin_delete_materi(
    materi_id: int,
    admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    db_materi = db.query(models.Materi).filter(models.Materi.id == materi_id).first()
    if not db_materi:
        raise HTTPException(status_code=404, detail="Materi not found")
    db.delete(db_materi)
    db.commit()
    return {"message": "Materi deleted"}

@app.get("/admin/stats")
def admin_stats(
    admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    total_users = db.query(models.User).count()
    total_materi = db.query(models.Materi).count()
    total_feedback = db.query(models.Feedback).count()
    avg_posttest = db.query(func.avg(models.PostTest.score)).scalar() or 0
    avg_pretest = db.query(func.avg(models.User.pretest_score)).scalar() or 0
    group_a = db.query(models.User).filter(models.User.group == 'A').count()
    group_b = db.query(models.User).filter(models.User.group == 'B').count()
    return {
        "total_users": total_users,
        "total_materi": total_materi,
        "total_feedback": total_feedback,
        "avg_posttest": round(avg_posttest, 2),
        "avg_pretest": round(avg_pretest, 2),
        "group_a": group_a,
        "group_b": group_b
    }

@app.post("/admin/init-materi")
def init_materi_admin(
    admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    if db.query(models.Materi).count() > 0:
        return {"message": "Materi already exists"}
    with open("data/materi.json", "r", encoding="utf-8") as f:
        materi_list = json.load(f)
    for m in materi_list:
        materi = models.Materi(
            id=m['id'],
            title=m['title'],
            type=m['type'],
            duration=int(m['duration']),
            icon=m.get('icon', ''),
            description=m.get('description', ''),
            fullDescription=m.get('fullDescription', ''),
            videoUrl=m.get('videoUrl'),
            imageUrl=m.get('imageUrl'),
            category=m.get('category', ''),
            content=m.get('content'),
            sources=m.get('sources')
        )
        db.add(materi)
    db.commit()
    return {"message": f"{len(materi_list)} materi added"}