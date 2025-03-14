# scripts/test_import.py

import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    print("Attempting to import FeatureInsight...")
    from app.schemas import FeatureInsight
    print("Successfully imported FeatureInsight")
    
    # Create an instance to verify it works
    insight = FeatureInsight(
        feature_id=1,
        name="Test Feature",
        category="Test Category",
        complexity=3,
        popularity=0.5,
        discovery_rate=0.7,
        avg_rating=4.5,
        automation_rate=0.3
    )
    print(f"Successfully created FeatureInsight instance: {insight}")
    
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Other error: {e}") 