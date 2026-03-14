from database import SessionLocal
from models import User
from passlib.hash import argon2

db = SessionLocal()
hashed = argon2.hash("admin123")  # menghasilkan hash Argon2

admin = User(
    nama="Admin",
    password=hashed,
    usia=22,
    gender="L",
    pendidikan="5",          # gunakan nilai yang sesuai dengan pilihan di form (misal "5" untuk Sarjana)
    kecamatan="wenang",      # sesuaikan dengan pilihan kecamatan
    informed_consent=True,
    pretest_answers={},
    pretest_score=0,
    preferensi_format="campuran",
    preferensi_waktu=30,
    preferensi_topik="program",
    group="A",
    is_admin=True
)
db.add(admin)
db.commit()
db.close()