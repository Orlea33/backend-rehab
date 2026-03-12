from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String, nullable=False)
    password = Column(String, nullable=False)  # akan di-hash
    usia = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    pendidikan = Column(String, nullable=False)
    kecamatan = Column(String, nullable=False)
    informed_consent = Column(Boolean, default=False)
    pretest_answers = Column(JSON, nullable=True)
    pretest_score = Column(Integer, nullable=True)
    preferensi_format = Column(String, nullable=True)
    preferensi_waktu = Column(Integer, nullable=True)
    preferensi_topik = Column(String, nullable=True)
    group = Column(String, nullable=False)  # 'A' atau 'B'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_admin = Column(Boolean, default=False)   # <-- tambahkan ini

class Materi(Base):
    __tablename__ = "materi"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    icon = Column(String, nullable=True)
    description = Column(String, nullable=True)
    fullDescription = Column(String, nullable=True)
    videoUrl = Column(String, nullable=True)
    imageUrl = Column(String, nullable=True)
    category = Column(String, nullable=True)
    content = Column(Text, nullable=True)    
    sources = Column(JSON, nullable=True)  

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    materi_id = Column(Integer, ForeignKey("materi.id"), nullable=False)
    action = Column(String, nullable=False)  # 'open', 'close', 'complete'
    duration = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class PostTest(Base):
    __tablename__ = "posttests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answers = Column(JSON, nullable=False)
    score = Column(Integer, nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)   # 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())