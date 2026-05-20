import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Muat variabel dari file .env
load_dotenv()

# Ambil URL database dari environment, default ke SQLite jika tidak ada
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# Normalisasi URL: Ubah "postgres://" menjadi "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Konfigurasi tambahan untuk koneksi database
connect_args = {}
is_sqlite = DATABASE_URL.startswith("sqlite")

if is_sqlite:
    # Khusus untuk SQLite
    connect_args = {"check_same_thread": False}
else:
    # Untuk PostgreSQL (Supabase) wajib menggunakan SSL
    connect_args = {"sslmode": "require"}

# Buat engine database
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # Cek koneksi sebelum dipakai
)

# Buat SessionLocal dan Base seperti biasa
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency untuk mendapatkan session database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()