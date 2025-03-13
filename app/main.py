# app/main.py

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
import datetime
from typing import List, Optional

from app.database import get_db, User, Feature, UserFeatureInteraction, UserContext
from app.schemas import (
    UserCreate, UserResponse, FeatureCreate, FeatureResponse,
    ContextRequest, ContextResponse, TutorialRequest, TutorialResponse,
    AutomationRequest, AutomationResponse, FeedbackRequest, FeedbackResponse,
    UserInsightsResponse, FeatureInsightsResponse
)
from app.services.llm import FeatureDiscoveryLLM
from app.services.scraper import ContextExtractor

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI(
    title="Feature Discovery Agent",
    description="AI-powered assistant that helps users discover and learn about SaaS features",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
llm_service = FeatureDiscoveryLLM(OPENAI_API_KEY)
context_extractor = ContextExtractor()

# Routes
@app.get("/")
async def root():
    return {
        "message": "Welcome to the Feature Discovery Agent API",
        "docs": "/docs",
        "version": "0.1.0"
    }

# User endpoints
@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    # Check if user with this email already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username is taken
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create new user
    db_user = User(
        username=user.username,
        email=user.email,
        product_role=user.product_role,
        experience_level=user.experience_level,
        feature_discovery_score=0.0,
        created_at=datetime.datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """Get user details"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/users/", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all users"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

# Feature endpoints
@app.post("/features/", response_model=FeatureResponse, status_code=status.HTTP_201_CREATED)
def create_feature(feature: FeatureCreate, db: Session = Depends(get_db)):
    """Create a new feature (admin only)"""
    # Check if feature with this name already exists
    db_feature = db.query(Feature).filter(Feature.name == feature.name).first()
    if db_feature:
        raise HTTPException(status_code=400, detail="Feature name already exists")
    
    # Create new feature
    db_feature = Feature(
        name=feature.name,
        description=feature.description,
        category=feature.category,
        complexity=feature.complexity,
        keywords=feature.keywords,
        popularity=0.0
    )
    db.add(db_feature)
    db.commit()
    db.refresh(db_feature)
    return db_feature

@app.get("/features/", response_model=List[FeatureResponse])
def list_features(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all features"""
    features = db.query(Feature).offset(skip).limit(limit).all()
    return features

@app.get("/features/{feature_id}", response_model=FeatureResponse)
def read_feature(feature_id: int, db: Session = Depends(get_db)):
    """Get feature details"""
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature

@app.get("/users/{user_id}/discovered_features", response_model=List[FeatureResponse])
def get_discovered_features(user_id: int, db: Session = Depends(get_db)):
    """Get features discovered by a user"""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get interactions with discovery status
    interactions = db.query(UserFeatureInteraction).filter(
        UserFeatureInteraction.user_id == user_id,
        UserFeatureInteraction.discovery_status >= 0.5  # Consider a feature discovered at 50% knowledge
    ).all()
    
    # Get feature ids from interactions
    feature_ids = [interaction.feature_id for interaction in interactions]
    
    # Get features
    features = db.query(Feature).filter(Feature.id.in_(feature_ids)).all() if feature_ids else []
    return features

# Context analysis and recommendations
@app.post("/context/analyze", response_model=ContextResponse)
async def analyze_context(request: ContextRequest, db: Session = Depends(get_db)):
    """Analyze user context and recommend features"""
    # Validate user
    user = db.query(User).filter(User.id == request.user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Extract context from HTML
    context_data = context_extractor.extract(request.html_snapshot, request.current_url)
    
    # Store context
    user_context = UserContext(
        user_id=user.id,
        url=request.current_url,
        context_data=context_data,
        query=request.user_query,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(user_context)
    db.commit()
    db.refresh(user_context)
    
    # Get discovered features
    discovered_interactions = db.query(UserFeatureInteraction).filter(
        UserFeatureInteraction.user_id == user.id,
        UserFeatureInteraction.discovery_status > 0
    ).all()
    discovered_feature_ids = [interaction.feature_id for interaction in discovered_interactions]
    discovered_features = db.query(Feature).filter(Feature.id.in_(discovered_feature_ids)).all() if discovered_feature_ids else []
    
    # Get all features for recommendation
    all_features = db.query(Feature).all()
    
    # Generate recommendations using LLM
    recommendations = llm_service.recommend_features(
        user_role=user.product_role,
        experience_level=user.experience_level,
        context=context_data,
        user_query=request.user_query,
        discovered_features=[{
            "id": feature.id,
            "name": feature.name,
            "description": feature.description,
            "category": feature.category
        } for feature in discovered_features],
        available_features=[{
            "id": feature.id,
            "name": feature.name,
            "description": feature.description,
            "category": feature.category,
            "complexity": feature.complexity
        } for feature in all_features if feature.id not in discovered_feature_ids]
    )
    
    return {
        "context_id": user_context.id,
        "extracted_context": context_data,
        "recommendations": recommendations["recommended_features"],
        "explanation": recommendations["explanation"],
        "can_automate": recommendations["automation_possible"]
    }

# Tutorial endpoint
@app.post("/features/{feature_id}/tutorial", response_model=TutorialResponse)
async def get_tutorial(feature_id: int, request: TutorialRequest, db: Session = Depends(get_db)):
    """Get a tutorial for a specific feature"""
    # Validate user and feature
    user = db.query(User).filter(User.id == request.user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    # Generate tutorial using LLM
    tutorial = llm_service.generate_tutorial(
        feature_name=feature.name,
        feature_description=feature.description,
        feature_category=feature.category,
        user_role=user.product_role,
        experience_level=user.experience_level,
        context_data=request.context_data
    )
    
    # Record interaction
    interaction = db.query(UserFeatureInteraction).filter(
        UserFeatureInteraction.user_id == user.id,
        UserFeatureInteraction.feature_id == feature.id
    ).first()
    
    if interaction:
        # Update existing interaction
        interaction.tutorial_views += 1
        interaction.last_interaction = datetime.datetime.utcnow()
        interaction.discovery_status = min(interaction.discovery_status + 0.2, 1.0)
    else:
        # Create new interaction
        interaction = UserFeatureInteraction(
            user_id=user.id,
            feature_id=feature.id,
            discovery_status=0.2,  # Initial discovery status after viewing tutorial
            tutorial_views=1,
            automation_uses=0,
            last_interaction=datetime.datetime.utcnow()
        )
        db.add(interaction)
    
    # Update feature popularity
    feature.popularity = (feature.popularity * 0.9) + 0.1  # Simple exponential moving average
    
    # Update user discovery score
    total_features = db.query(Feature).count()
    discovered_features = db.query(UserFeatureInteraction).filter(
        UserFeatureInteraction.user_id == user.id,
        UserFeatureInteraction.discovery_status > 0
    ).count()
    
    user.feature_discovery_score = discovered_features / total_features if total_features > 0 else 0
    
    db.commit()
    db.refresh(interaction)
    
    return {
        "interaction_id": interaction.id,
        "tutorial": {
            "title": tutorial["title"],
            "introduction": tutorial["introduction"],
            "steps": tutorial["steps"],
            "tips": tutorial["tips"],
            "related_features": tutorial["related_features"]
        },
        "discovery_status": interaction.discovery_status,
        "can_automate": tutorial["can_automate"]
    }

# Automation endpoint
@app.post("/features/{feature_id}/automate", response_model=AutomationResponse)
async def automate_feature(feature_id: int, request: AutomationRequest, db: Session = Depends(get_db)):
    """Automate a feature for the user"""
    # Validate user and feature
    user = db.query(User).filter(User.id == request.user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    feature = db.query(Feature).filter(Feature.id == feature_id).first()
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    # Generate automation steps using LLM
    automation = llm_service.generate_automation(
        feature_name=feature.name,
        feature_description=feature.description,
        user_role=user.product_role,
        context_data=request.context_data
    )
    
    # Record interaction
    interaction = db.query(UserFeatureInteraction).filter(
        UserFeatureInteraction.user_id == user.id,
        UserFeatureInteraction.feature_id == feature.id
    ).first()
    
    if interaction:
        # Update existing interaction
        interaction.automation_uses += 1
        interaction.last_interaction = datetime.datetime.utcnow()
        interaction.discovery_status = min(interaction.discovery_status + 0.3, 1.0)
    else:
        # Create new interaction
        interaction = UserFeatureInteraction(
            user_id=user.id,
            feature_id=feature.id,
            discovery_status=0.3,  # Initial discovery status after automation
            tutorial_views=0,
            automation_uses=1,
            last_interaction=datetime.datetime.utcnow()
        )
        db.add(interaction)
    
    # Update feature popularity
    feature.popularity = (feature.popularity * 0.9) + 0.1  # Simple exponential moving average
    
    # Update user discovery score
    total_features = db.query(Feature).count()
    discovered_features = db.query(UserFeatureInteraction).filter(
        UserFeatureInteraction.user_id == user.id,
        UserFeatureInteraction.discovery_status > 0
    ).count()
    
    user.feature_discovery_score = discovered_features / total_features if total_features > 0 else 0
    
    db.commit()
    db.refresh(interaction)
    
    return {
        "interaction_id": interaction.id,
        "automation": {
            "steps": automation["steps"],
            "explanation": automation["explanation"],
            "success": automation["success"]
        },
        "discovery_status": interaction.discovery_status
    }

# Feedback endpoint
@app.post("/feedback", response_model=FeedbackResponse)
async def provide_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """Provide feedback on a feature interaction"""
    # Find the interaction
    interaction = db.query(UserFeatureInteraction).filter(UserFeatureInteraction.id == request.interaction_id).first()
    if interaction is None:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    # Update feedback
    interaction.rating = request.rating
    interaction.feedback = request.feedback_text
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Feedback recorded successfully"
    }

# Insights endpoints
@app.get("/insights/user/{user_id}", response_model=UserInsightsResponse)
async def get_user_insights(user_id: int, db: Session = Depends(get_db)):
    """Get insights for a specific user"""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get interactions
    interactions = db.query(UserFeatureInteraction).filter(UserFeatureInteraction.user_id == user_id).all()
    
    # Calculate insights
    discovered_features_count = len([i for i in interactions if i.discovery_status > 0])
    fully_learned_features_count = len([i for i in interactions if i.discovery_status >= 0.8])
    total_features = db.query(Feature).count()
    
    # Get feature categories for discovered features
    feature_ids = [i.feature_id for i in interactions if i.discovery_status > 0]
    features = db.query(Feature).filter(Feature.id.in_(feature_ids)).all() if feature_ids else []
    
    # Group by category
    category_distribution = {}
    for feature in features:
        if feature.category in category_distribution:
            category_distribution[feature.category] += 1
        else:
            category_distribution[feature.category] = 1
    
    # Calculate time-based metrics
    if interactions:
        first_interaction = min([i.last_interaction for i in interactions])
        time_spent = (datetime.datetime.utcnow() - first_interaction).total_seconds() / 3600  # hours
    else:
        time_spent = 0
    
    return {
        "user_id": user_id,
        "discovery_score": user.feature_discovery_score * 100,  # as percentage
        "discovered_features": discovered_features_count,
        "fully_learned_features": fully_learned_features_count,
        "total_features": total_features,
        "discovery_rate": discovered_features_count / total_features if total_features > 0 else 0,
        "category_distribution": category_distribution,
        "time_spent_hours": time_spent,
        "efficiency": fully_learned_features_count / time_spent if time_spent > 0 else 0
    }

@app.get("/insights/features", response_model=FeatureInsightsResponse)
async def get_feature_insights(db: Session = Depends(get_db)):
    """Get insights on features"""
    # Get all features
    features = db.query(Feature).all()
    
    # Get all interactions
    interactions = db.query(UserFeatureInteraction).all()
    
    # Calculate insights
    feature_insights = []
    for feature in features:
        feature_interactions = [i for i in interactions if i.feature_id == feature.id]
        
        if feature_interactions:
            discovery_rate = len(feature_interactions) / db.query(User).count()
            avg_rating = sum([i.rating for i in feature_interactions if i.rating]) / len([i for i in feature_interactions if i.rating]) if any(i.rating for i in feature_interactions) else 0
            automation_rate = sum([i.automation_uses for i in feature_interactions]) / len(feature_interactions)
        else:
            discovery_rate = 0
            avg_rating = 0
            automation_rate = 0
        
        feature_insights.append({
            "feature_id": feature.id,
            "name": feature.name,
            "category": feature.category,
            "complexity": feature.complexity,
            "popularity": feature.popularity,
            "discovery_rate": discovery_rate,
            "avg_rating": avg_rating,
            "automation_rate": automation_rate
        })
    
    return {
        "feature_insights": feature_insights,
        "total_features": len(features),
        "avg_complexity": sum([f.complexity for f in features]) / len(features) if features else 0,
        "most_popular_category": max(
            set([f.category for f in features]),
            key=lambda x: sum([1 for f in features if f.category == x])
        ) if features else None
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow()
    }

# uvicorn app.main:app --reload