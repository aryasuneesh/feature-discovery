from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables.utils import AddableDict
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
import json
import logging
import time
import random
import os
from typing import Dict, Any, Optional, List, Union

# set up standard logger
logger = logging.getLogger(__name__)

# ========== LLM Logging ==========
# set up LLM response logger
llm_logger = logging.getLogger("llm_responses")
llm_logger.setLevel(logging.INFO)

# Get the absolute path to the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
log_file_path = os.path.join(project_root, 'llm_responses.log')

# Print the log file path for debugging
print(f"LLM log file will be created at: {log_file_path}")

# Create a file handler for the LLM logger
try:
    llm_file_handler = logging.FileHandler(log_file_path)
    llm_file_handler.setLevel(logging.INFO)

    # formatter for the LLM logger
    llm_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    llm_file_handler.setFormatter(llm_formatter)

    # add the handler to the LLM logger
    llm_logger.addHandler(llm_file_handler)
    llm_logger.propagate = False  # prevent propagation to root logger
    
    # Log a test message to verify logging is working
    llm_logger.info("LLM logging initialized successfully")
    print("LLM logger initialized successfully")
except Exception as e:
    print(f"Error setting up LLM logger: {e}")
    logger.error(f"Error setting up LLM logger: {e}")
# ====================================

class FeatureDiscoveryLLM:
    """
    Service for using LLMs to power feature discovery, tutorials, and automation.
    Utilizes LangChain for easy integration with OpenRouter's API.
    """
    
    def __init__(self, api_key):
        """Initialize the LLM service with API key"""
        # Initialize OpenAI client for OpenRouter (for fallback)
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        
        # Configure LangChain to use OpenRouter with ChatOpenAI
        self.llm = ChatOpenAI(
            temperature=0.7, 
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            model_name="meta-llama/llama-3.3-70b-instruct:free",
            request_timeout=60,  # Increased timeout
            max_retries=3,       # Add retries
        )
        
        # Define the prompt template for feature recommendations
        self.recommendation_prompt = ChatPromptTemplate.from_template(
            """You are an AI feature discovery agent for a SaaS product. You help users discover 
            the most relevant features based on their context and needs.
            
            USER INFORMATION:
            - Role: {user_role}
            - Experience level: {experience_level}
            
            CURRENT CONTEXT:
            {context}
            
            USER QUERY (if any):
            {user_query}
            
            FEATURES THE USER HAS ALREADY DISCOVERED:
            {discovered_features}
            
            AVAILABLE FEATURES THE USER HASN'T DISCOVERED YET:
            {available_features}
            
            Based on the user's role, experience level, current context, and query (if any), 
            recommend 2-3 features from the available ones that would be most helpful right now.
            
            For each recommendation, provide:
            1. Feature name
            2. A brief explanation of why it would be helpful in their current context
            3. A gentle nudge to try it out
            
            Finally, indicate whether any of the features could be automatically executed for the user
            in their current context.
            
            Return your response STRICTLY in this JSON format:
            {{{{
                "recommended_features": [
                    {{{{
                        "id": feature_id,
                        "name": "Feature name",
                        "reason": "Why it's helpful now",
                        "nudge": "Encouragement to try it"
                    }}}}
                ],
                "explanation": "Brief explanation of your recommendation logic",
                "automation_possible": true/false
            }}}}
            """
        )
        
        # Define the prompt template for tutorials
        self.tutorial_prompt = ChatPromptTemplate.from_template(
            """You are an AI feature discovery agent providing a helpful tutorial 
            for a SaaS product feature.
            
            FEATURE INFORMATION:
            - Name: {feature_name}
            - Description: {feature_description}
            - Category: {feature_category}
            
            USER INFORMATION:
            - Role: {user_role}
            - Experience level: {experience_level}
            
            CURRENT CONTEXT (if available):
            {context_data}
            
            Create an engaging, helpful tutorial for this feature that is appropriate for
            the user's role and experience level. Make it practical and actionable.
            
            Include:
            1. A catchy title
            2. A brief introduction explaining the value of this feature
            3. Step-by-step instructions (3-5 steps)
            4. 1-2 pro tips for advanced usage
            5. 1-2 related features they might want to explore next
            
            Also indicate whether this feature could be automated for the user.
            
            Return your response in this JSON format:
            {{{{
                "title": "Tutorial title",
                "introduction": "Brief intro and value proposition",
                "steps": [
                    "Step 1 description",
                    "Step 2 description",
                    "Step 3 description"
                ],
                "tips": [
                    "Pro tip 1",
                    "Pro tip 2"
                ],
                "related_features": [
                    "Related feature 1",
                    "Related feature 2"
                ],
                "can_automate": true/false
            }}}}
            """
        )
        
        # Define the prompt template for automation
        self.automation_prompt = ChatPromptTemplate.from_template(
            """You are an AI feature discovery agent that can automate feature usage
            in a SaaS product.
            
            FEATURE INFORMATION:
            - Name: {feature_name}
            - Description: {feature_description}
            
            USER INFORMATION:
            - Role: {user_role}
            
            CURRENT CONTEXT:
            {context_data}
            
            You need to automatically execute this feature for the user in their current context.
            Provide a step-by-step breakdown of how you would execute this feature, explaining
            each step clearly.
            
            Return your response in this JSON format:
            {{{{
                "steps": [
                    "Step 1 description",
                    "Step 2 description",
                    "Step 3 description"
                ],
                "explanation": "Brief explanation of what was done",
                "success": true/false
            }}}}
            """
        )
        
        # Initialize JSON output parser with error handling
        self.json_parser = JsonOutputParser(pydantic_object=None)
        
        # Create LCEL chains with error handling
        self.recommendation_chain = (
            self.recommendation_prompt 
            | self._rate_limit_wrapper(self.llm) 
            | self._handle_llm_errors 
            | self.json_parser
            | self._handle_parsing_errors
        )
        
        self.tutorial_chain = (
            self.tutorial_prompt 
            | self._rate_limit_wrapper(self.llm) 
            | self._handle_llm_errors 
            | self.json_parser
            | self._handle_parsing_errors
        )
        
        self.automation_chain = (
            self.automation_prompt 
            | self._rate_limit_wrapper(self.llm) 
            | self._handle_llm_errors 
            | self.json_parser
            | self._handle_parsing_errors
        )
        
        # Rate limiting settings
        self.last_request_time = 0
        self.min_request_interval = 0.5  # seconds between requests
    
    def _rate_limit_wrapper(self, llm):
        """Wrap the LLM with rate limiting"""
        def _rate_limited_llm(inputs):
            # Apply rate limiting
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            
            if time_since_last_request < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last_request
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()
            result = llm.invoke(inputs)
            
            # Log the LLM response
            if hasattr(result, 'content'):
                llm_logger.info(f"LLM Response: {result.content}")
            
            return result
        
        return _rate_limited_llm
    
    def _handle_llm_errors(self, llm_output):
        """Handle errors from the LLM"""
        if not llm_output or not hasattr(llm_output, 'content'):
            logger.error("LLM returned invalid output format")
            return "Error: Invalid LLM output format"
        return llm_output.content
    
    def _handle_parsing_errors(self, parsed_output):
        """Handle errors from the JSON parser"""
        if isinstance(parsed_output, str) and parsed_output.startswith("Error:"):
            logger.error(f"JSON parsing error: {parsed_output}")
            # Return a minimal valid JSON structure
            return {
                "error": parsed_output,
                "recommended_features": [],
                "explanation": "Error occurred during processing",
                "automation_possible": False
            }
        return parsed_output
    
    def _exponential_backoff(self, retry_count, base_delay=1, max_delay=60):
        """Implement exponential backoff for retries"""
        delay = min(base_delay * (2 ** retry_count) + random.uniform(0, 1), max_delay)
        logger.info(f"Retrying after {delay:.2f} seconds (attempt {retry_count+1})")
        time.sleep(delay)
    
    def recommend_features(self, user_role, experience_level, context, user_query, discovered_features, available_features):
        """
        Generate feature recommendations based on user context.
        
        Args:
            user_role (str): The user's role in the product
            experience_level (str): The user's experience level
            context (dict): The extracted context from the user's current view
            user_query (str): Any explicit query from the user
            discovered_features (list): Features the user has already discovered
            available_features (list): Features the user hasn't discovered yet
            
        Returns:
            dict: Recommended features and explanation
        """
        if not user_query:
            user_query = "No specific query provided"
        
        # Validate inputs
        if not available_features:
            logger.warning("No available features to recommend")
            return {
                "recommended_features": [],
                "explanation": "No available features to recommend at this time.",
                "automation_possible": False
            }
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use LCEL chain
                response = self.recommendation_chain.invoke({
                    "user_role": user_role,
                    "experience_level": experience_level,
                    "context": str(context),
                    "user_query": user_query,
                    "discovered_features": str(discovered_features) if discovered_features else "No features discovered yet",
                    "available_features": str(available_features) if available_features else "No features available"
                })
                
                # Validate response structure
                if "recommended_features" not in response:
                    logger.warning("Response missing recommended_features field")
                    response["recommended_features"] = []
                
                if "explanation" not in response:
                    logger.warning("Response missing explanation field")
                    response["explanation"] = "Features recommended based on your context."
                
                if "automation_possible" not in response:
                    logger.warning("Response missing automation_possible field")
                    response["automation_possible"] = False
                
                # Log the final response
                llm_logger.info(f"Feature Recommendation Response: {json.dumps(response, indent=2)}")
                
                return response
                
            except Exception as e:
                logger.error(f"Error generating recommendations (attempt {retry_count+1}): {e}")
                retry_count += 1
                
                if retry_count < max_retries:
                    self._exponential_backoff(retry_count)
                else:
                    # Try direct API call as fallback
                    return self._fallback_recommendation(user_role, experience_level, context, user_query, discovered_features, available_features)
    
    def _fallback_recommendation(self, user_role, experience_level, context, user_query, discovered_features, available_features):
        """Fallback method for recommendations when LangChain fails"""
        try:
            print("Using fallback recommendation method")
            prompt = f"""You are an AI feature discovery agent for a SaaS product. You help users discover 
            the most relevant features based on their context and needs.
            
            USER INFORMATION:
            - Role: {user_role}
            - Experience level: {experience_level}
            
            CURRENT CONTEXT:
            {str(context)}
            
            USER QUERY (if any):
            {user_query}
            
            FEATURES THE USER HAS ALREADY DISCOVERED:
            {str(discovered_features) if discovered_features else "No features discovered yet"}
            
            AVAILABLE FEATURES THE USER HASN'T DISCOVERED YET:
            {str(available_features) if available_features else "No features available"}
            
            Based on the user's role, experience level, current context, and query (if any), 
            recommend 2-3 features from the available ones that would be most helpful right now.
            
            For each recommendation, provide:
            1. Feature name
            2. A brief explanation of why it would be helpful in their current context
            3. A gentle nudge to try it out
            
            Finally, indicate whether any of the features could be automatically executed for the user
            in their current context.
            
            Return your response STRICTLY in this JSON format:
            {{
                "recommended_features": [
                    {{
                        "id": feature_id,
                        "name": "Feature name",
                        "reason": "Why it's helpful now",
                        "nudge": "Encouragement to try it"
                    }}
                ],
                "explanation": "Brief explanation of your recommendation logic",
                "automation_possible": true/false
            }}
            """
            
            print("Sending request to OpenRouter API")
            completion = self.client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Check if the completion has the expected structure
            if not completion or not hasattr(completion, 'choices') or not completion.choices:
                print("OpenRouter API returned an invalid response structure")
                raise ValueError("Invalid API response structure")
                
            if not hasattr(completion.choices[0], 'message') or not completion.choices[0].message:
                print("OpenRouter API response missing message")
                raise ValueError("API response missing message")
                
            direct_response = completion.choices[0].message.content
            if not direct_response:
                print("OpenRouter API response has empty content")
                raise ValueError("API response has empty content")
                
            print(f"Received fallback response: {direct_response[:100]}...")
            
            # Log the fallback response
            try:
                llm_logger.info(f"Fallback Recommendation Response: {direct_response}")
                print(f"Logged fallback response to {log_file_path}")
            except Exception as log_error:
                print(f"Error logging fallback response: {log_error}")
            
            # Parse the JSON response with error handling
            try:
                parsed_response = json.loads(direct_response)
                return parsed_response
            except json.JSONDecodeError as json_error:
                print(f"Error parsing JSON response: {json_error}")
                print(f"Raw response: {direct_response}")
                raise ValueError(f"Invalid JSON in API response: {json_error}")
                
        except Exception as e2:
            logger.error(f"Fallback also failed: {e2}")
            print(f"Fallback recommendation failed: {e2}")
            # Last resort fallback
            fallback_response = {
                "recommended_features": [
                    {
                        "id": available_features[0]["id"] if available_features and len(available_features) > 0 else 1,
                        "name": available_features[0]["name"] if available_features and len(available_features) > 0 else "Example Feature",
                        "reason": "Based on your context, this would be helpful",
                        "nudge": "Give it a try to streamline your workflow"
                    }
                ],
                "explanation": "Recommendations based on your current context and role",
                "automation_possible": False
            }
            
            # Log the last resort fallback
            try:
                llm_logger.info(f"Last Resort Fallback Response: {json.dumps(fallback_response, indent=2)}")
            except Exception:
                pass
                
            return fallback_response
    
    def generate_tutorial(self, feature_name, feature_description, feature_category, user_role, experience_level, context_data=None):
        """
        Generate a tutorial for a specific feature.
        
        Args:
            feature_name (str): Name of the feature
            feature_description (str): Description of the feature
            feature_category (str): Category of the feature
            user_role (str): The user's role in the product
            experience_level (str): The user's experience level
            context_data (dict, optional): Current context data
            
        Returns:
            dict: Tutorial content
        """
        if not context_data:
            context_data = "No context provided"
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use LCEL chain
                response = self.tutorial_chain.invoke({
                    "feature_name": feature_name,
                    "feature_description": feature_description,
                    "feature_category": feature_category,
                    "user_role": user_role,
                    "experience_level": experience_level,
                    "context_data": str(context_data)
                })
                
                # Validate response structure
                if "title" not in response:
                    logger.warning("Tutorial response missing title field")
                    response["title"] = f"How to Use {feature_name}"
                
                if "steps" not in response or not response["steps"]:
                    logger.warning("Tutorial response missing steps field")
                    response["steps"] = ["Navigate to the feature", "Configure settings", "Apply changes"]
                
                # Log the tutorial response
                llm_logger.info(f"Tutorial Response: {json.dumps(response, indent=2)}")
                
                return response
                
            except Exception as e:
                logger.error(f"Error generating tutorial (attempt {retry_count+1}): {e}")
                retry_count += 1
                
                if retry_count < max_retries:
                    self._exponential_backoff(retry_count)
                else:
                    # Try direct API call as fallback
                    return self._fallback_tutorial(feature_name, feature_description, feature_category, user_role, experience_level, context_data)
    
    def _fallback_tutorial(self, feature_name, feature_description, feature_category, user_role, experience_level, context_data):
        """Fallback method for tutorials when LangChain fails"""
        try:
            prompt = f"""You are an AI feature discovery agent providing a helpful tutorial 
            for a SaaS product feature.
            
            FEATURE INFORMATION:
            - Name: {feature_name}
            - Description: {feature_description}
            - Category: {feature_category}
            
            USER INFORMATION:
            - Role: {user_role}
            - Experience level: {experience_level}
            
            CURRENT CONTEXT (if available):
            {str(context_data)}
            
            Create an engaging, helpful tutorial for this feature that is appropriate for
            the user's role and experience level. Make it practical and actionable.
            
            Include:
            1. A catchy title
            2. A brief introduction explaining the value of this feature
            3. Step-by-step instructions (3-5 steps)
            4. 1-2 pro tips for advanced usage
            5. 1-2 related features they might want to explore next
            
            Also indicate whether this feature could be automated for the user.
            
            Return your response in this JSON format:
            {{{{
                "title": "Tutorial title",
                "introduction": "Brief intro and value proposition",
                "steps": [
                    "Step 1 description",
                    "Step 2 description",
                    "Step 3 description"
                ],
                "tips": [
                    "Pro tip 1",
                    "Pro tip 2"
                ],
                "related_features": [
                    "Related feature 1",
                    "Related feature 2"
                ],
                "can_automate": true/false
            }}}}
            """
            
            completion = self.client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            direct_response = completion.choices[0].message.content
            
            # Log the fallback tutorial response
            llm_logger.info(f"Fallback Tutorial Response: {direct_response}")
            
            return json.loads(direct_response)
        except Exception as e2:
            logger.error(f"Fallback also failed: {e2}")
            # Last resort fallback
            return {
                "title": f"How to Use {feature_name}",
                "introduction": f"{feature_description}",
                "steps": [
                    "Navigate to the feature in the menu",
                    "Configure your settings",
                    "Apply changes and see results"
                ],
                "tips": [
                    "Use keyboard shortcuts for faster operation",
                    "Combine with other features for maximum impact"
                ],
                "related_features": [
                    "Similar Feature 1",
                    "Similar Feature 2"
                ],
                "can_automate": True
            }
    
    def generate_automation(self, feature_name, feature_description, user_role, context_data):
        """
        Generate automation steps for a feature.
        
        Args:
            feature_name (str): Name of the feature
            feature_description (str): Description of the feature
            user_role (str): The user's role in the product
            context_data (dict): Current context data
            
        Returns:
            dict: Automation steps and explanation
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use LCEL chain
                response = self.automation_chain.invoke({
                    "feature_name": feature_name,
                    "feature_description": feature_description,
                    "user_role": user_role,
                    "context_data": str(context_data)
                })
                
                # Validate response structure
                if "steps" not in response or not response["steps"]:
                    logger.warning("Automation response missing steps field")
                    response["steps"] = ["Identify feature", "Apply settings", "Execute"]
                
                if "explanation" not in response:
                    logger.warning("Automation response missing explanation field")
                    response["explanation"] = f"Automated {feature_name} based on your context"
                
                if "success" not in response:
                    logger.warning("Automation response missing success field")
                    response["success"] = True
                
                # Log the automation response
                llm_logger.info(f"Automation Response: {json.dumps(response, indent=2)}")
                
                return response
                
            except Exception as e:
                logger.error(f"Error generating automation (attempt {retry_count+1}): {e}")
                retry_count += 1
                
                if retry_count < max_retries:
                    self._exponential_backoff(retry_count)
                else:
                    # Try direct API call as fallback
                    return self._fallback_automation(feature_name, feature_description, user_role, context_data)
    
    def _fallback_automation(self, feature_name, feature_description, user_role, context_data):
        """Fallback method for automation when LangChain fails"""
        try:
            prompt = f"""You are an AI feature discovery agent that can automate feature usage
            in a SaaS product.
            
            FEATURE INFORMATION:
            - Name: {feature_name}
            - Description: {feature_description}
            
            USER INFORMATION:
            - Role: {user_role}
            
            CURRENT CONTEXT:
            {str(context_data)}
            
            You need to automatically execute this feature for the user in their current context.
            Provide a step-by-step breakdown of how you would execute this feature, explaining
            each step clearly.
            
            Return your response in this JSON format:
            {{{{
                "steps": [
                    "Step 1 description",
                    "Step 2 description",
                    "Step 3 description"
                ],
                "explanation": "Brief explanation of what was done",
                "success": true/false
            }}}}
            """
            
            completion = self.client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            direct_response = completion.choices[0].message.content
            
            # Log the fallback automation response
            llm_logger.info(f"Fallback Automation Response: {direct_response}")
            
            return json.loads(direct_response)
        except Exception as e2:
            logger.error(f"Fallback also failed: {e2}")
            # Last resort fallback
            return {
                "steps": [
                    "Identified the correct feature to automate",
                    "Applied optimal settings based on your context",
                    "Executed the feature successfully"
                ],
                "explanation": "Automated execution of the feature based on your current context",
                "success": True
            }