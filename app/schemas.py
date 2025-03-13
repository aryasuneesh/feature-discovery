# app/schemas.py

from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any
import datetime

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    product_role: str
    experience_level: str

class UserCreate(UserBase):
    pass

class UserInDB(UserBase):
    id: int
    feature_discovery_score: float
    created_at: datetime.datetime

    class Config:
        orm_mode = True

class UserResponse(UserInDB):
    pass

# Feature schemas
class FeatureBase(BaseModel):
    name: str
    description: str
    category: str
    complexity: int = Field(..., ge=1, le=5)
    keywords: List[str]

class FeatureCreate(FeatureBase):
    pass

class FeatureInDB(FeatureBase):
    id: int
    popularity: float

    class Config:
        orm_mode = True

class FeatureResponse(FeatureInDB):
    pass

# Context schemas
class ContextRequest(BaseModel):
    user_id: int
    current_url: str
    html_snapshot: str
    user_query: Optional[str] = None

class ContextData(BaseModel):
    title: str
    url: str
    current_section: str
    form_fields: List[Dict[str, Any]]
    nav_items: List[Dict[str, Any]]
    headings: List[str]
    buttons: List[Dict[str, Any]]
    potential_features: List[str]
    error_messages: List[str]

class ContextResponse(BaseModel):
    context_id: int
    extracted_context: ContextData
    recommendations: List[Dict[str, Any]]
    explanation: str
    can_automate: bool

# Tutorial schemas
class TutorialRequest(BaseModel):
    user_id: int
    context_data: Optional[Dict[str, Any]] = None

class TutorialStep(BaseModel):
    step_number: int
    description: str

class TutorialResponse(BaseModel):
    interaction_id: int
    tutorial: Dict[str, Any]
    discovery_status: float
    can_automate: bool

# Automation schemas
class AutomationRequest(BaseModel):
    user_id: int
    context_data: Dict[str, Any]

class AutomationResponse(BaseModel):
    interaction_id: int
    automation: Dict[str, Any]
    discovery_status: float

# Feedback schemas
class FeedbackRequest(BaseModel):
    interaction_id: int
    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = None

    @validator('rating')
    def rating_must_be_valid(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

class FeedbackResponse(BaseModel):
    status: str
    message: str

# Insights schemas
class UserInsightsResponse(BaseModel):
    user_id: int
    discovery_score: float
    discovered_features: int
    fully_learned_features: int
    total_features: int
    discovery_rate: float
    category_distribution: Dict[str, int]
    time_spent_hours: float
    efficiency: float

class FeatureInsight(BaseModel):
    feature_id: int
    name: str
    category: str
    complexity: int
    popularity: float
    discovery_rate: float
    avg_rating: float
    automation_rate: float

class FeatureInsightsResponse(BaseModel):
    feature_insights: List[FeatureInsight]
    total_features: int
    avg_complexity: float
    most_popular_category: Optional[str]