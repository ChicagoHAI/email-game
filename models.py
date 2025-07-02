"""
AI Models and Services

This module contains all the AI-powered classes that interface with OpenAI's API
for email generation, evaluation, recipient simulation, and rubric creation.
"""

import streamlit as st
import openai
import os
from config import (
    DEFAULT_MODEL, 
    DEFAULT_EVALUATION_TEMPLATE,
    DEFAULT_RUBRIC_TEMPLATE,
    EVALUATION_PROMPT_PATH,
    RUBRIC_GENERATION_PROMPT_PATH
)
from utils import load_file_content, save_rubric_to_file, get_api_client, load_rubric_from_file


class EmailGenerator:
    """
    Generates email content using OpenAI's language models.
    
    This class provides functionality to generate contextually appropriate 
    email responses based on given scenarios using GPT-4o model.
    
    Attributes:
        client (openai.OpenAI): OpenAI API client instance
        
    Methods:
        generate_email(scenario, model): Generate email content for a scenario
    """
    def __init__(self):
        self.client = get_api_client()
    
    def generate_email(self, scenario: str, model: str = DEFAULT_MODEL) -> str:
        """Generate an email response for the given scenario"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are writing an email in response to the given scenario. Write only the email content, no additional commentary."},
                    {"role": "user", "content": scenario}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error generating email: {str(e)}")
            return None


class EmailEvaluator:
    """Evaluates emails using OpenAI models with custom rubrics."""
    
    def __init__(self):
        self.client = get_api_client()
    
    def evaluate_email(self, scenario: str, email: str, 
                      rubric: str, recipient_reply: str, model: str = DEFAULT_MODEL) -> str:
        """Evaluate an email using the specified model, rubric, and recipient response"""
        
        # Check if user provided a custom evaluation template in session state
        custom_template = st.session_state.get("evaluator_prompt", "")
        
        if custom_template.strip():
            # Use user-provided template
            evaluation_template = custom_template
            
            # Prepare template variables (user template may or may not use all of them)
            template_vars = {
                'scenario': scenario,
                'email': email,
                'response': recipient_reply
            }
            
            # Only add rubric if it's provided and the template contains the placeholder
            if rubric is not None and '{rubric}' in evaluation_template:
                template_vars['rubric'] = rubric
                
            evaluation_prompt = evaluation_template.format(**template_vars)
                
        else:
            evaluation_template = load_file_content(EVALUATION_PROMPT_PATH, DEFAULT_EVALUATION_TEMPLATE)

            if rubric is None:
                rubric = ""
            
            evaluation_prompt = evaluation_template.format(
                scenario=scenario,
                rubric=rubric,
                email=email,
                response=recipient_reply
            )
        # else:
            # # No rubric and no custom template - use fallback general evaluation
            # evaluation_prompt = f"""
            # Please evaluate this email based on the given scenario and the recipient's response.
            
            # Scenario:
            # {scenario}
            
            # Email:
            # {email}
            
            # Recipient's Response:
            # {recipient_reply}
            
            # Please provide a comprehensive evaluation of how well the email addresses the scenario. 
            # Consider factors such as:
            # - Clarity and communication effectiveness
            # - Appropriateness of tone
            # - Achievement of stated goals
            # - Overall persuasiveness and professionalism
            
            # End your evaluation with either "Yes" or "No" to indicate whether the email successfully achieved its primary goal.
            # """
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert email evaluator. Provide detailed, constructive feedback."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error evaluating email: {str(e)}")
            return None


class EmailRecipient:
    """Simulates email recipients and generates realistic replies."""
    
    def __init__(self):
        self.client = get_api_client()
    
    def generate_reply(self, recipient_prompt: str, user_email: str, 
                      model: str = DEFAULT_MODEL) -> str:
        """Generate a reply email from the recipient persona"""
        
        reply_prompt = f"""
        {recipient_prompt}
        
        You just received this email:
        {user_email}
        
        Please write a reply email as this character. Write only the email content, no additional commentary.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are roleplaying as the specified character. Write a natural email reply that fits your persona and responds appropriately to the received email."},
                    {"role": "user", "content": reply_prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error generating recipient reply: {str(e)}")
            return None


class RubricGenerator:
    """Generates and manages evaluation rubrics for email scenarios."""
    
    def __init__(self):
        self.client = get_api_client()
    
    def get_or_generate_rubric(self, scenario: str, scenario_filename: str, model: str = DEFAULT_MODEL) -> str:
        """Load existing rubric or generate and save a new one"""
        
        # First, check session state cache
        if 'cached_rubrics' not in st.session_state:
            st.session_state.cached_rubrics = {}
            
        if scenario_filename in st.session_state.cached_rubrics:
            return st.session_state.cached_rubrics[scenario_filename]
        
        # Second, try to load from file
        existing_rubric = load_rubric_from_file(scenario_filename)
        if existing_rubric:
            st.session_state.cached_rubrics[scenario_filename] = existing_rubric
            return existing_rubric
        
        # If no existing rubric, generate a new one
        new_rubric = self.generate_rubric(scenario, model)
        if new_rubric:
            st.session_state.cached_rubrics[scenario_filename] = new_rubric
            save_rubric_to_file(scenario_filename, new_rubric)
        
        return new_rubric
    
    def generate_rubric(self, scenario: str, model: str = DEFAULT_MODEL) -> str:
        """Generate a custom rubric for evaluating emails based on the scenario"""
        
        # Load rubric generation prompt
        rubric_template = load_file_content(RUBRIC_GENERATION_PROMPT_PATH, DEFAULT_RUBRIC_TEMPLATE)
        rubric_prompt = rubric_template.format(scenario=scenario)
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert educator creating detailed rubrics for email evaluation. Create specific, measurable criteria based on the given scenario."},
                    {"role": "user", "content": rubric_prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error generating rubric: {str(e)}")
            return None 