from sqlalchemy import Column, Integer, String, Boolean
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # ADMIN / FORENSIC_ANALYST / LEGAL_AUTHORITY / USER
    is_active = Column(Boolean, default=True)
