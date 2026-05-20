import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DATABASE_URL")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)

# Koneksi dengan SSL
engine = create_engine(url, connect_args={"sslmode": "require"})

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("✅ Koneksi berhasil!", result.fetchone())

    # Cek schema public
    result = conn.execute(text("SELECT current_schema()"))
    print("Schema saat ini:", result.fetchone()[0])