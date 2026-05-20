from database import engine
import models

print("📋 Mencoba membuat semua tabel...")
try:
    models.Base.metadata.create_all(bind=engine)
    print("✅ Perintah create_all berhasil dijalankan.")
    
    # Cek tabel yang sudah ada
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema="public")
    print(f"📊 Tabel yang ada di public: {tables}")
except Exception as e:
    print(f"❌ Error: {e}")