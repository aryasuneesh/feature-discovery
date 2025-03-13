# scripts/test_api.py

import requests
import json
import os
import logging
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set defaults
API_URL = os.getenv("API_URL", "http://localhost:8000")

class APITester:
    """Utility class for testing the Feature Discovery Agent API"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.user_id = None
        self.feature_id = None
    
    def create_user(self, username="testuser", email="test@example.com", role="manager", experience="intermediate"):
        """Create a new user for testing"""
        url = f"{self.base_url}/users/"
        payload = {
            "username": username,
            "email": email,
            "product_role": role,
            "experience_level": experience
        }
        
        logger.info(f"Creating user: {username}")
        response = requests.post(url, json=payload)
        
        if response.status_code == 201:  # Created
            data = response.json()
            self.user_id = data["id"]
            logger.info(f"User created with ID: {self.user_id}")
            return data
        else:
            logger.error(f"Error creating user: {response.status_code} - {response.text}")
            return None
    
    def list_features(self):
        """List all available features"""
        url = f"{self.base_url}/features/"
        
        logger.info("Fetching features")
        response = requests.get(url)
        
        if response.status_code == 200:
            features = response.json()
            if features:
                logger.info(f"Found {len(features)} features")
                # Store the first feature ID for later use
                self.feature_id = features[0]["id"]
                return features
            else:
                logger.warning("No features found")
                return []
        else:
            logger.error(f"Error fetching features: {response.status_code} - {response.text}")
            return None
    
    def analyze_context(self, user_id=None, query=None):
        """Test context analysis with a sample HTML"""
        if not user_id and not self.user_id:
            logger.error("No user ID provided or created")
            return None
        
        user_id = user_id or self.user_id
        
        # Sample HTML for testing
        html_snapshot = """
        <html>
            <head><title>Project Dashboard - SaaS App</title></head>
            <body>
                <nav>
                    <a href="/dashboard" class="active">Dashboard</a>
                    <a href="/projects">Projects</a>
                    <a href="/tasks">Tasks</a>
                    <a href="/reports">Reports</a>
                </nav>
                <main>
                    <h1>Project Dashboard</h1>
                    <div class="stats">
                        <div class="stat-card">
                            <h3>Active Projects</h3>
                            <p class="stat">12</p>
                        </div>
                        <div class="stat-card">
                            <h3>Completed Tasks</h3>
                            <p class="stat">87</p>
                        </div>
                        <div class="stat-card">
                            <h3>Pending Tasks</h3>
                            <p class="stat">34</p>
                        </div>
                    </div>
                    <div class="features">
                        <h2>Available Features</h2>
                        <ul>
                            <li>Task automation feature can help you save time</li>
                            <li>Try our Gantt charts for better project planning</li>
                            <li>Generate custom reports with our reporting tool</li>
                        </ul>
                    </div>
                </main>
            </body>
        </html>
        """
        
        url = f"{self.base_url}/context/analyze"
        payload = {
            "user_id": user_id,
            "current_url": "/dashboard",
            "html_snapshot": html_snapshot,
            "user_query": query
        }
        
        logger.info(f"Analyzing context for user {user_id}")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("Context analysis successful")
            logger.info(f"Recommended features: {len(data['recommendations'])}")
            return data
        else:
            logger.error(f"Error analyzing context: {response.status_code} - {response.text}")
            return None
    
    def get_tutorial(self, feature_id=None, user_id=None):
        """Get a tutorial for a feature"""
        if not feature_id and not self.feature_id:
            logger.error("No feature ID provided or found")
            return None
        
        if not user_id and not self.user_id:
            logger.error("No user ID provided or created")
            return None
        
        feature_id = feature_id or self.feature_id
        user_id = user_id or self.user_id
        
        url = f"{self.base_url}/features/{feature_id}/tutorial"
        payload = {
            "user_id": user_id,
            "context_data": {
                "current_page": "dashboard",
                "user_intent": "learning"
            }
        }
        
        logger.info(f"Getting tutorial for feature {feature_id}")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Tutorial received: {data['tutorial']['title']}")
            return data
        else:
            logger.error(f"Error getting tutorial: {response.status_code} - {response.text}")
            return None
    
    def automate_feature(self, feature_id=None, user_id=None):
        """Test feature automation"""
        if not feature_id and not self.feature_id:
            logger.error("No feature ID provided or found")
            return None
        
        if not user_id and not self.user_id:
            logger.error("No user ID provided or created")
            return None
        
        feature_id = feature_id or self.feature_id
        user_id = user_id or self.user_id
        
        url = f"{self.base_url}/features/{feature_id}/automate"
        payload = {
            "user_id": user_id,
            "context_data": {
                "current_page": "dashboard",
                "form_values": {
                    "report_type": "weekly",
                    "include_charts": True
                }
            }
        }
        
        logger.info(f"Automating feature {feature_id}")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Automation successful: {len(data['automation']['steps'])} steps")
            return data
        else:
            logger.error(f"Error automating feature: {response.status_code} - {response.text}")
            return None
    
    def provide_feedback(self, interaction_id, rating=4, feedback_text="Very helpful!"):
        """Provide feedback on an interaction"""
        if not interaction_id:
            logger.error("No interaction ID provided")
            return None
        
        url = f"{self.base_url}/feedback"
        payload = {
            "interaction_id": interaction_id,
            "rating": rating,
            "feedback_text": feedback_text
        }
        
        logger.info(f"Providing feedback for interaction {interaction_id}")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Feedback submitted: {data['status']}")
            return data
        else:
            logger.error(f"Error submitting feedback: {response.status_code} - {response.text}")
            return None
    
    def get_user_insights(self, user_id=None):
        """Get insights for a user"""
        if not user_id and not self.user_id:
            logger.error("No user ID provided or created")
            return None
        
        user_id = user_id or self.user_id
        
        url = f"{self.base_url}/insights/user/{user_id}"
        
        logger.info(f"Getting insights for user {user_id}")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"User insights received: {data['discovery_score']:.2f}% discovery score")
            return data
        else:
            logger.error(f"Error getting user insights: {response.status_code} - {response.text}")
            return None
    
    def get_feature_insights(self):
        """Get insights on features"""
        url = f"{self.base_url}/insights/features"
        
        logger.info("Getting feature insights")
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Feature insights received: {data['total_features']} features analyzed")
            return data
        else:
            logger.error(f"Error getting feature insights: {response.status_code} - {response.text}")
            return None
    
    def run_all_tests(self):
        """Run all API tests in sequence"""
        logger.info("Starting API tests")
        
        # Create user
        user = self.create_user()
        if not user:
            return
        
        # List features
        features = self.list_features()
        if not features:
            return
        
        # Analyze context
        context = self.analyze_context()
        if not context:
            return
        
        # Get tutorial
        tutorial = self.get_tutorial()
        if not tutorial:
            return
        
        # Provide feedback
        feedback = self.provide_feedback(tutorial["interaction_id"])
        if not feedback:
            return
        
        # Automate feature
        automation = self.automate_feature()
        if not automation:
            return
        
        # Get user insights
        user_insights = self.get_user_insights()
        if not user_insights:
            return
        
        # Get feature insights
        feature_insights = self.get_feature_insights()
        if not feature_insights:
            return
        
        logger.info("All API tests completed successfully")

def main():
    """Main function to run the API tests"""
    parser = argparse.ArgumentParser(description="Test the Feature Discovery Agent API")
    parser.add_argument("--url", help="API base URL", default=API_URL)
    parser.add_argument("--test", choices=["all", "user", "features", "context", "tutorial", "automate", "insights"], 
                        default="all", help="Specific test to run")
    
    args = parser.parse_args()
    
    tester = APITester(args.url)
    
    if args.test == "all":
        tester.run_all_tests()
    elif args.test == "user":
        tester.create_user()
    elif args.test == "features":
        tester.list_features()
    elif args.test == "context":
        tester.create_user()
        tester.analyze_context()
    elif args.test == "tutorial":
        tester.create_user()
        tester.list_features()
        tester.get_tutorial()
    elif args.test == "automate":
        tester.create_user()
        tester.list_features()
        tester.automate_feature()
    elif args.test == "insights":
        tester.create_user()
        tester.list_features()
        tester.get_tutorial()
        tester.get_user_insights()
        tester.get_feature_insights()

if __name__ == "__main__":
    main()