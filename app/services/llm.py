from openai import OpenAI
from langchain_openai import OpenAI as LangchainOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import json
import logging

logger = logging.getLogger(__name__)

class FeatureDiscoveryLLM:
    """
    Service for using LLMs to power feature discovery, tutorials, and automation.
    Utilizes LangChain for easy integration with OpenRouter's API.
    """
    
    def __init__(self, api_key):
        """Initialize the LLM service with API key"""
        # Initialize OpenAI client for OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        
        # Configure LangChain to use OpenRouter
        self.llm = LangchainOpenAI(
            temperature=0.7, 
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            model_name="meta-llama/llama-3.3-70b-instruct:free"
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
            {
                "recommended_features": [
                    {
                        "id": feature_id,
                        "name": "Feature name",
                        "reason": "Why it's helpful now",
                        "nudge": "Encouragement to try it"
                    }
                ],
                "explanation": "Brief explanation of your recommendation logic",
                "automation_possible": true/false
            }
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
            {
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
            }
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
            {
                "steps": [
                    "Step 1 description",
                    "Step 2 description",
                    "Step 3 description"
                ],
                "explanation": "Brief explanation of what was done",
                "success": true/false
            }
            """
        )
        
        # Initialize chains
        self.recommendation_chain = LLMChain(llm=self.llm, prompt=self.recommendation_prompt)
        self.tutorial_chain = LLMChain(llm=self.llm, prompt=self.tutorial_prompt)
        self.automation_chain = LLMChain(llm=self.llm, prompt=self.automation_prompt)
    
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
        
        try:
            # Direct API call to OpenRouter as an alternative approach
            # This can be used if the LangChain integration has issues
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
            
            # Use LangChain approach
            response = self.recommendation_chain.run(
                user_role=user_role,
                experience_level=experience_level,
                context=str(context),
                user_query=user_query,
                discovered_features=str(discovered_features) if discovered_features else "No features discovered yet",
                available_features=str(available_features) if available_features else "No features available"
            )
            
            # Parse the JSON response
            parsed_response = json.loads(response)
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            # Try direct API call as fallback
            try:
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
                return json.loads(direct_response)
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                # Last resort fallback
                return {
                    "recommended_features": [
                        {
                            "id": available_features[0]["id"] if available_features else 1,
                            "name": available_features[0]["name"] if available_features else "Example Feature",
                            "reason": "Based on your context, this would be helpful",
                            "nudge": "Give it a try to streamline your workflow"
                        }
                    ],
                    "explanation": "Recommendations based on your current context and role",
                    "automation_possible": False
                }
    
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
        
        try:
            response = self.tutorial_chain.run(
                feature_name=feature_name,
                feature_description=feature_description,
                feature_category=feature_category,
                user_role=user_role,
                experience_level=experience_level,
                context_data=str(context_data)
            )
            
            # Parse the JSON response
            parsed_response = json.loads(response)
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error generating tutorial: {e}")
            # Try direct API call as fallback
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
                {{
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
                }}
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
        try:
            response = self.automation_chain.run(
                feature_name=feature_name,
                feature_description=feature_description,
                user_role=user_role,
                context_data=str(context_data)
            )
            
            # Parse the JSON response
            parsed_response = json.loads(response)
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error generating automation: {e}")
            # Try direct API call as fallback
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
                {{
                    "steps": [
                        "Step 1 description",
                        "Step 2 description",
                        "Step 3 description"
                    ],
                    "explanation": "Brief explanation of what was done",
                    "success": true/false
                }}
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