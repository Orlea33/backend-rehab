# Di shell atau script terpisah
from database import SessionLocal
from models import User
import bcrypt

db = SessionLocal()
hashed = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
admin = User(
    nama="Admin",
    password=hashed.decode('utf-8'),
    usia=22,
    gender="L",
    pendidikan="Sarjana",
    kecamatan="Manado",
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