# app/main.py

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
import datetime
import logging
from typing import List, Optional, Dict, Any
import traceback

from app.database import get_db, User, Feature, UserFeatureInteraction, UserContext
from app.schemas import (
    UserCreate, UserResponse, FeatureCreate, FeatureResponse,
    ContextRequest, ContextResponse, TutorialRequest, TutorialResponse,
    AutomationRequest, AutomationResponse, FeedbackRequest, FeedbackResponse,
    UserInsightsResponse, FeatureInsightsResponse, RecommendedFeature,
    Tutorial, Automation, FeatureInsight  # Make sure FeatureInsight is included here
)
from app.services.llm import FeatureDiscoveryLLM
from app.services.scraper import ContextExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY environment variable not set")
    raise ValueError("OPENAI_API_KEY environment variable not set")

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

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

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
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """Get user details"""
    try:
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user: {str(e)}")

@app.get("/users/", response_model=List[UserResponse])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all users"""
    try:
        users = db.query(User).offset(skip).limit(limit).all()
        return users
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")

# Feature endpoints
@app.post("/features/", response_model=FeatureResponse, status_code=status.HTTP_201_CREATED)
def create_feature(feature: FeatureCreate, db: Session = Depends(get_db)):
    """Create a new feature (admin only)"""
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating feature: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create feature: {str(e)}")

@app.get("/features/", response_model=List[FeatureResponse])
def list_features(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all features"""
    try:
        features = db.query(Feature).offset(skip).limit(limit).all()
        return features
    except Exception as e:
        logger.error(f"Error listing features: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list features: {str(e)}")

@app.get("/features/{feature_id}", response_model=FeatureResponse)
def read_feature(feature_id: int, db: Session = Depends(get_db)):
    """Get feature details"""
    try:
        feature = db.query(Feature).filter(Feature.id == feature_id).first()
        if feature is None:
            raise HTTPException(status_code=404, detail="Feature not found")
        return feature
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading feature {feature_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve feature: {str(e)}")

@app.get("/users/{user_id}/discovered_features", response_model=List[FeatureResponse])
def get_discovered_features(user_id: int, db: Session = Depends(get_db)):
    """Get features discovered by a user"""
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting discovered features for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve discovered features: {str(e)}")

# Context analysis and recommendations
@app.post("/context/analyze", response_model=ContextResponse)
async def analyze_context(request: ContextRequest, db: Session = Depends(get_db)):
    """Analyze user context and recommend features"""
    try:
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
        
        # Check if there are any available features to recommend
        available_features = [
            {
                "id": feature.id,
                "name": feature.name,
                "description": feature.description,
                "category": feature.category,
                "complexity": feature.complexity
            } 
            for feature in all_features if feature.id not in discovered_feature_ids
        ]
        
        if not available_features:
            logger.warning(f"No available features to recommend for user {user.id}")
            return {
                "context_id": user_context.id,
                "extracted_context": context_data,
                "recommendations": [],
                "explanation": "You have already discovered all available features!",
                "can_automate": False
            }
        
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
            available_features=available_features
        )
        
        # Convert recommendations to proper schema
        recommended_features = []
        for rec in recommendations.get("recommended_features", []):
            try:
                recommended_features.append(RecommendedFeature(
                    id=rec["id"],
                    name=rec["name"],
                    reason=rec["reason"],
                    nudge=rec["nudge"]
                ))
            except (KeyError, TypeError) as e:
                logger.warning(f"Invalid recommendation format: {e}, recommendation: {rec}")
        
        return {
            "context_id": user_context.id,
            "extracted_context": context_data,
            "recommendations": recommended_features,
            "explanation": recommendations.get("explanation", "Features recommended based on your context"),
            "can_automate": recommendations.get("automation_possible", False)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing context: {e}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to analyze context: {str(e)}")

# Tutorial endpoint
@app.post("/features/{feature_id}/tutorial", response_model=TutorialResponse)
async def get_tutorial(feature_id: int, request: TutorialRequest, db: Session = Depends(get_db)):
    """Get a tutorial for a specific feature"""
    try:
        # Validate user and feature
        user = db.query(User).filter(User.id == request.user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        feature = db.query(Feature).filter(Feature.id == feature_id).first()
        if feature is None:
            raise HTTPException(status_code=404, detail="Feature not found")
        
        # Generate tutorial using LLM
        tutorial_data = llm_service.generate_tutorial(
            feature_name=feature.name,
            feature_description=feature.description,
            feature_category=feature.category,
            user_role=user.product_role,
            experience_level=user.experience_level,
            context_data=request.context_data
        )
        
        # Convert to Tutorial schema
        tutorial = Tutorial(
            title=tutorial_data.get("title", f"How to Use {feature.name}"),
            introduction=tutorial_data.get("introduction", feature.description),
            steps=tutorial_data.get("steps", ["Navigate to the feature", "Configure settings", "Apply changes"]),
            tips=tutorial_data.get("tips", ["Use keyboard shortcuts for faster operation"]),
            related_features=tutorial_data.get("related_features", []),
            can_automate=tutorial_data.get("can_automate", False)
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
            
            # Increase discovery status (max 1.0)
            new_discovery_status = min(interaction.discovery_status + 0.2, 1.0)
            interaction.discovery_status = new_discovery_status
        else:
            # Create new interaction
            interaction = UserFeatureInteraction(
                user_id=user.id,
                feature_id=feature.id,
                discovery_status=0.3,  # Initial discovery status after viewing tutorial
                tutorial_views=1,
                automation_uses=0,
                last_interaction=datetime.datetime.utcnow()
            )
            db.add(interaction)
        
        # Update feature popularity
        feature.popularity = (feature.popularity * 0.9) + 0.1  # Simple weighted update
        
        db.commit()
        db.refresh(interaction)
        
        return {
            "interaction_id": interaction.id,
            "tutorial": tutorial,
            "discovery_status": interaction.discovery_status,
            "can_automate": tutorial.can_automate
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating tutorial for feature {feature_id}: {e}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate tutorial: {str(e)}")

# Automation endpoint
@app.post("/features/{feature_id}/automate", response_model=AutomationResponse)
async def automate_feature(feature_id: int, request: AutomationRequest, db: Session = Depends(get_db)):
    """Automate a feature for a user"""
    try:
        # Validate user and feature
        user = db.query(User).filter(User.id == request.user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        feature = db.query(Feature).filter(Feature.id == feature_id).first()
        if feature is None:
            raise HTTPException(status_code=404, detail="Feature not found")
        
        # Generate automation steps using LLM
        automation_data = llm_service.generate_automation(
            feature_name=feature.name,
            feature_description=feature.description,
            user_role=user.product_role,
            context_data=request.context_data
        )
        
        # Convert to Automation schema
        automation = Automation(
            steps=automation_data.get("steps", []),
            explanation=automation_data.get("explanation", f"Automated {feature.name}"),
            success=automation_data.get("success", True)
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
            
            # Increase discovery status (max 1.0)
            new_discovery_status = min(interaction.discovery_status + 0.3, 1.0)
            interaction.discovery_status = new_discovery_status
        else:
            # Create new interaction
            interaction = UserFeatureInteraction(
                user_id=user.id,
                feature_id=feature.id,
                discovery_status=0.5,  # Higher initial discovery status for automation
                tutorial_views=0,
                automation_uses=1,
                last_interaction=datetime.datetime.utcnow()
            )
            db.add(interaction)
        
        # Update feature popularity
        feature.popularity = (feature.popularity * 0.8) + 0.2  # Higher weight for automation
        
        db.commit()
        db.refresh(interaction)
        
        return {
            "interaction_id": interaction.id,
            "automation": automation,
            "discovery_status": interaction.discovery_status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error automating feature {feature_id}: {e}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to automate feature: {str(e)}")

# Feedback endpoint
@app.post("/feedback", response_model=FeedbackResponse)
async def provide_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """Provide feedback on a feature interaction"""
    try:
        # Validate interaction
        interaction = db.query(UserFeatureInteraction).filter(
            UserFeatureInteraction.id == request.interaction_id
        ).first()
        
        if interaction is None:
            raise HTTPException(status_code=404, detail="Interaction not found")
        
        # Update interaction with feedback
        interaction.rating = request.rating
        interaction.feedback = request.feedback_text
        
        # Update user's feature discovery score
        user = db.query(User).filter(User.id == interaction.user_id).first()
        if user:
            # Get all user's interactions with ratings
            rated_interactions = db.query(UserFeatureInteraction).filter(
                UserFeatureInteraction.user_id == user.id,
                UserFeatureInteraction.rating.isnot(None)
            ).all()
            
            if rated_interactions:
                # Calculate average rating
                avg_rating = sum(i.rating for i in rated_interactions) / len(rated_interactions)
                # Update user score (simple weighted average)
                user.feature_discovery_score = (user.feature_discovery_score * 0.7) + (avg_rating * 0.3)
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Feedback recorded successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error providing feedback for interaction {request.interaction_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {str(e)}")

# User insights endpoint
@app.get("/insights/user/{user_id}", response_model=UserInsightsResponse)
async def get_user_insights(user_id: int, db: Session = Depends(get_db)):
    """Get insights about a user's feature discovery journey"""
    try:
        # Validate user
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get all user interactions
        interactions = db.query(UserFeatureInteraction).filter(
            UserFeatureInteraction.user_id == user.id
        ).all()
        
        # Get all features
        all_features = db.query(Feature).all()
        total_features = len(all_features)
        
        # Calculate metrics
        discovered_features = len([i for i in interactions if i.discovery_status > 0])
        fully_learned_features = len([i for i in interactions if i.discovery_status >= 0.9])
        
        # Calculate discovery rate
        discovery_rate = discovered_features / total_features if total_features > 0 else 0
        
        # Calculate category distribution
        category_distribution = {}
        for interaction in interactions:
            feature = db.query(Feature).filter(Feature.id == interaction.feature_id).first()
            if feature:
                category = feature.category
                if category in category_distribution:
                    category_distribution[category] += 1
                else:
                    category_distribution[category] = 1
        
        # Calculate time spent (rough estimate based on interactions)
        first_interaction = min([i.last_interaction for i in interactions], default=user.created_at) if interactions else user.created_at
        time_spent = (datetime.datetime.utcnow() - first_interaction).total_seconds() / 3600  # hours
        
        # Calculate efficiency (features discovered per hour)
        efficiency = discovered_features / time_spent if time_spent > 0 else 0
        
        return {
            "user_id": user.id,
            "discovery_score": user.feature_discovery_score,
            "discovered_features": discovered_features,
            "fully_learned_features": fully_learned_features,
            "total_features": total_features,
            "discovery_rate": discovery_rate,
            "category_distribution": category_distribution,
            "time_spent_hours": time_spent,
            "efficiency": efficiency
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting insights for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")

# Feature insights endpoint
@app.get("/insights/features", response_model=FeatureInsightsResponse)
async def get_feature_insights(db: Session = Depends(get_db)):
    """Get insights about feature discovery across all users"""
    try:
        # Import FeatureInsight directly in the function to avoid any import issues
        from app.schemas import FeatureInsight
        
        # Get all features
        features = db.query(Feature).all()
        
        feature_insights = []
        total_complexity = 0
        category_counts = {}
        
        for feature in features:
            # Get all interactions for this feature
            interactions = db.query(UserFeatureInteraction).filter(
                UserFeatureInteraction.feature_id == feature.id
            ).all()
            
            # Calculate metrics
            total_users = db.query(User).count()
            discovery_rate = len(interactions) / total_users if total_users > 0 else 0
            
            # Calculate average rating
            rated_interactions = [i for i in interactions if i.rating is not None]
            avg_rating = sum(i.rating for i in rated_interactions) / len(rated_interactions) if rated_interactions else 0
            
            # Calculate automation rate
            automation_rate = len([i for i in interactions if i.automation_uses > 0]) / len(interactions) if interactions else 0
            
            # Add to category counts
            if feature.category in category_counts:
                category_counts[feature.category] += 1
            else:
                category_counts[feature.category] = 1
            
            # Add to total complexity
            total_complexity += feature.complexity
            
            # Create insight
            insight = FeatureInsight(
                feature_id=feature.id,
                name=feature.name,
                category=feature.category,
                complexity=feature.complexity,
                popularity=feature.popularity,
                discovery_rate=discovery_rate,
                avg_rating=avg_rating,
                automation_rate=automation_rate
            )
            
            feature_insights.append(insight)
        
        # Calculate most popular category
        most_popular_category = max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None
        
        # Calculate average complexity
        avg_complexity = total_complexity / len(features) if features else 0
        
        return {
            "feature_insights": feature_insights,
            "total_features": len(features),
            "avg_complexity": avg_complexity,
            "most_popular_category": most_popular_category
        }
    except Exception as e:
        logger.error(f"Error getting feature insights: {e}")
        logger.error(traceback.format_exc())  # Add full traceback for better debugging
        raise HTTPException(status_code=500, detail=f"Failed to generate feature insights: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "services": {
            "llm": "available",
            "context_extractor": "available"
        }
    }

# uvicorn app.main:app --reload