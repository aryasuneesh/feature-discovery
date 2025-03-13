# app/database.py

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime, ARRAY, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
from typing import List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./feature_discovery.db")

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    product_role = Column(String, index=True)  # ex: "admin", "manager", "user"
    experience_level = Column(String)  # ex: "beginner", "intermediate", "advanced"
    feature_discovery_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    feature_interactions = relationship("UserFeatureInteraction", back_populates="user")
    contexts = relationship("UserContext", back_populates="user")

class Feature(Base):
    __tablename__ = "features"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    category = Column(String, index=True)
    complexity = Column(Integer)
    keywords = Column(JSON)
    popularity = Column(Float, default=0.0)
    interactions = relationship("UserFeatureInteraction", back_populates="feature")

class UserFeatureInteraction(Base):
    __tablename__ = "user_feature_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    feature_id = Column(Integer, ForeignKey("features.id"))
    discovery_status = Column(Float, default=0.0) # 0.0 - 1.0 maybe? 
    tutorial_views = Column(Integer, default=0)
    automation_uses = Column(Integer, default=0)
    rating = Column(Integer, nullable=True)
    feedback = Column(String, nullable=True)
    last_interaction = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="feature_interactions")
    feature = relationship("Feature", back_populates="interactions")

class UserContext(Base):
    __tablename__ = "user_contexts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    url = Column(String)
    context_data = Column(JSON)
    query = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="contexts")

# Database setup
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency to get the database session.
    This creates a new session for each request and ensures it's closed properly.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()