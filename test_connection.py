# test_connection.py
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
print(f"Raw Database URL: {db_url}")

# Normalisasi URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

print(f"Fixed URL for SQLAlchemy: {db_url}")

try:
    # Buat engine dengan SSL untuk koneksi ke Supabase
    engine = create_engine(db_url, connect_args={"sslmode": "require"})
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()
        print("\n✅ Koneksi BERHASIL!")
        print(f"Versi Database: {version[0]}")
except Exception as e:
    print(f"\n❌ Koneksi GAGAL: {e}")