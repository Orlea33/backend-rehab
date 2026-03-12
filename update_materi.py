import json
import psycopg2
from psycopg2.extras import Json
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/rehabdb")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

with open('data/materi.json', 'r', encoding='utf-8') as f:
    data_list = json.load(f)

for item in data_list:
    cur.execute("""
        UPDATE materi 
        SET content = %s, sources = %s
        WHERE id = %s
    """, (item.get('content'), Json(item.get('sources')), item['id']))
    print(f"Updated id {item['id']}")

conn.commit()
cur.close()
conn.close()
print("Selesai.")