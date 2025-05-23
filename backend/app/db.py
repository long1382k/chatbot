from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine

# SQLite file sẽ nằm ở project root
DATABASE_URL = "sqlite:///./chat_history.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)  # chính là X-Session-ID từ FE
    user_id    = Column(String, index=True)
    title      = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship("Message", back_populates="conversation", cascade="all, delete")

class Message(Base):
    __tablename__ = "messages"
    id               = Column(Integer, primary_key=True, index=True)
    conversation_id  = Column(Integer, ForeignKey("conversations.id"), index=True)
    role             = Column(String, index=True)   # "user" / "assistant" / "system"
    content          = Column(Text)
    timestamp        = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")

def init_db():
    """Tạo các bảng nếu chưa tồn tại."""
    Base.metadata.create_all(bind=engine)
