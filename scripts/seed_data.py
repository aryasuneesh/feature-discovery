# scripts/seed_data.py

import sys
import os
import logging
import argparse
from sqlalchemy.orm import Session

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Feature, User

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample features for a project management SaaS
features = [
    {
        "name": "Task Automation",
        "description": "Automate repetitive tasks with custom rules and triggers",
        "category": "Productivity",
        "complexity": 4,
        "keywords": ["automation", "workflow", "rules", "tasks"]
    },
    {
        "name": "Kanban Board",
        "description": "Visual project management with customizable boards and lanes",
        "category": "Project Management",
        "complexity": 2,
        "keywords": ["kanban", "board", "visual", "cards", "lanes"]
    },
    {
        "name": "Time Tracking",
        "description": "Track time spent on tasks and generate detailed reports",
        "category": "Analytics",
        "complexity": 3,
        "keywords": ["time", "tracking", "hours", "reports"]
    },
    {
        "name": "Document Collaboration",
        "description": "Edit documents together with your team in real-time",
        "category": "Collaboration",
        "complexity": 3,
        "keywords": ["documents", "collaboration", "editing", "real-time"]
    },
    {
        "name": "Gantt Charts",
        "description": "Visualize project timelines and dependencies",
        "category": "Project Management",
        "complexity": 4,
        "keywords": ["gantt", "timeline", "dependencies", "schedule"]
    },
    {
        "name": "API Integration",
        "description": "Connect your project with external tools and services",
        "category": "Integration",
        "complexity": 5,
        "keywords": ["api", "integration", "webhook", "connector"]
    },
    {
        "name": "Custom Dashboards",
        "description": "Create personalized views with the metrics that matter to you",
        "category": "Analytics",
        "complexity": 4,
        "keywords": ["dashboard", "metrics", "visualization", "widgets"]
    },
    {
        "name": "Automated Reports",
        "description": "Schedule and generate reports automatically",
        "category": "Analytics",
        "complexity": 3,
        "keywords": ["reports", "automated", "schedule", "export"]
    },
    {
        "name": "Team Chat",
        "description": "Communicate with your team through integrated messaging",
        "category": "Collaboration",
        "complexity": 2,
        "keywords": ["chat", "messaging", "communication", "team"]
    },
    {
        "name": "Resource Allocation",
        "description": "Optimize team workload and resource distribution",
        "category": "Project Management",
        "complexity": 4,
        "keywords": ["resources", "allocation", "workload", "optimization"]
    }
]

# Sample user roles
users = [
    {
        "username": "admin_user",
        "email": "admin@example.com",
        "product_role": "admin",
        "experience_level": "advanced"
    },
    {
        "username": "manager_user",
        "email": "manager@example.com",
        "product_role": "manager",
        "experience_level": "intermediate"
    },
    {
        "username": "new_user",
        "email": "new@example.com",
        "product_role": "user",
        "experience_level": "beginner"
    }
]

def seed_database(force_user_seed=False):
    """
    Seed the database with initial data
    
    Args:
        force_user_seed (bool): If True, re-add user seed data even if users already exist
    """
    db = SessionLocal()
    try:
        # Check if features already exist
        existing_features = db.query(Feature).count()
        if existing_features == 0:
            # Add features
            for feature_data in features:
                feature = Feature(**feature_data)
                db.add(feature)
            
            logger.info(f"Added {len(features)} features to the database")
        else:
            logger.info(f"Found {existing_features} existing features. Skipping feature seed.")
        
        # Check if users already exist
        existing_users = db.query(User).count()
        if existing_users == 0 or force_user_seed:
            if force_user_seed and existing_users > 0:
                logger.info(f"Force user seed enabled. Re-adding user seed data.")
            
            # Add users
            for user_data in users:
                # check if user already exists using email
                existing_user = db.query(User).filter(User.email == user_data["email"]).first()
                
                if existing_user and force_user_seed:
                    # update existing user
                    for key, value in user_data.items():
                        setattr(existing_user, key, value)
                    logger.info(f"Updated existing user: {user_data['username']}")
                elif not existing_user:
                    # create new user
                    user = User(**user_data, feature_discovery_score=0.0)
                    db.add(user)
                    logger.info(f"Added new user: {user_data['username']}")
            
            logger.info(f"User seed completed")
        else:
            logger.info(f"Found {existing_users} existing users. Skipping user seed.")
        
        db.commit()
        logger.info("Database seeding completed successfully")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Seed the database with initial data')
    parser.add_argument('--force-user-seed', action='store_true', 
                        help='Force re-adding user seed data even if users already exist')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    seed_database(force_user_seed=args.force_user_seed)