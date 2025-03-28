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

class FormField(BaseModel):
    type: str
    id: str = ""
    name: str = ""
    placeholder: Optional[str] = ""
    label: Optional[str] = ""
    value: str = ""

class NavItem(BaseModel):
    text: str
    href: str = ""
    active: bool = False
    has_icon: bool = False

class Button(BaseModel):
    text: str
    id: str = ""
    class_: Optional[str] = Field(default="", alias="class")
    disabled: bool = False
    type: str = ""

class ContextData(BaseModel):
    title: str
    url: str
    current_section: str
    form_fields: List[FormField]
    nav_items: List[NavItem]
    headings: List[str]
    buttons: List[Button]
    potential_features: List[str]
    error_messages: List[str]
    metadata: Dict[str, str] = {}
    user_info: Dict[str, str] = {}
    domain: str = ""

class RecommendedFeature(BaseModel):
    id: int
    name: str
    reason: str
    nudge: str

class ContextResponse(BaseModel):
    context_id: int
    extracted_context: ContextData
    recommendations: List[RecommendedFeature]
    explanation: str
    can_automate: bool

# Tutorial schemas
class TutorialRequest(BaseModel):
    user_id: int
    context_data: Optional[Dict[str, Any]] = None

class TutorialStep(BaseModel):
    description: str

class Tutorial(BaseModel):
    title: str
    introduction: str
    steps: List[str]
    tips: List[str]
    related_features: List[str]
    can_automate: bool

class TutorialResponse(BaseModel):
    interaction_id: int
    tutorial: Tutorial
    discovery_status: float
    can_automate: bool

# Automation schemas
class AutomationRequest(BaseModel):
    user_id: int
    context_data: Dict[str, Any]

class Automation(BaseModel):
    steps: List[str]
    explanation: str
    success: bool

class AutomationResponse(BaseModel):
    interaction_id: int
    automation: Automation
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