from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class UserCreate(BaseModel):
    nama: str
    password: str
    usia: int
    gender: str
    pendidikan: str
    kecamatan: str
    informed_consent: bool
    pretest_answers: Dict[str, Any]
    pretest_score: int
    preferensi_format: str
    preferensi_waktu: int
    preferensi_topik: str

class UserOut(BaseModel):
    id: int
    nama: str
    group: str

    class Config:
        orm_mode = True

class MateriOut(BaseModel):
    id: int
    title: str
    type: str
    duration: int
    icon: Optional[str] = None
    description: Optional[str] = None
    fullDescription: Optional[str] = None
    content: Optional[str] = None  
    sources: Optional[List[Dict[str, str]]] = None
    videoUrl: Optional[str] = None
    imageUrl: Optional[str] = None
    category: Optional[str] = None

    class Config:
        orm_mode = True

class RecommendationOut(BaseModel):
    materi: MateriOut
    confidence: float
    reason: Optional[str] = None

class InteractionCreate(BaseModel):
    user_id: int
    materi_id: int
    action: str  # 'open', 'close', 'complete'
    duration: Optional[int] = None

class PostTestCreate(BaseModel):
    answers: Dict[str, Any]
    score: int

class FeedbackCreate(BaseModel):
    rating: int
    comment: Optional[str] = None

class UserUpdate(BaseModel):
    nama: Optional[str] = None
    usia: Optional[int] = None
    gender: Optional[str] = None

class MateriCreate(BaseModel):
    title: str
    type: str
    duration: int
    icon: Optional[str] = None
    description: Optional[str] = None
    fullDescription: Optional[str] = None
    videoUrl: Optional[str] = None
    imageUrl: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    sources: Optional[List[Dict[str, str]]] = None

class MateriUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    duration: Optional[int] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    fullDescription: Optional[str] = None
    videoUrl: Optional[str] = None
    imageUrl: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    sources: Optional[List[Dict[str, str]]] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None