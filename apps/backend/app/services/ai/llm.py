from google import genai
from google.genai import types
from typing import Optional, Dict, Any
import json
import logging
import re
import asyncio
from datetime import datetime
from app.core.config import settings
from app.models.llm.llm_email import LLMEmailInput, LLMEmailOutput, EmailIntent
from app.models.api.job_application import ApplicationStatus
from app.models.api.application_event import ApplicationEventType
from .prompt_loader import format_email_analysis_prompt

client = genai.Client(api_key=settings.GEMINI_API_KEY)

logger = logging.getLogger(__name__)

def _get_fallback_output(
    notes: str = "Processing error occurred"
) -> LLMEmailOutput:
    """Return a safe fallback output when processing fails."""
    return LLMEmailOutput(
        intent=EmailIntent.GENERAL,
        company="Unknown Company",
        role="Unknown Role",
        status=ApplicationStatus.APPLIED,
        location=None,
        salary_range=None,
        notes=notes,
        event_type=None,
        event_description=None,
        event_date=None
    )

def _clean_response(content: str) -> str:
    """Clean up LLM response to extract valid JSON."""
    content = content.strip()
    
    # Remove code fence markers if present
    content = re.sub(r'^```(?:json)?', '', content, flags=re.MULTILINE)
    content = re.sub(r'```$', '', content, flags=re.MULTILINE)
    content = content.strip()
    
    json_start = content.find("{")
    if json_start >= 0:
        brace_count = 0
        for i, char in enumerate(content[json_start:], json_start):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    return content[json_start:i+1]
    
    return content

async def _call_gemini_with_retry(
    system_prompt: str,
    user_prompt: str,
    model_name: str = "gemini-2.5-flash-lite-preview-06-17",
    max_retries: int = 3
) -> str:
    """
    Call Gemini API with exponential backoff retry.
    
    Model Strategy:
    - Primary: gemini-2.5-flash-lite-preview-06-17 (higher daily quota, lower RPM)
    - Fallback: gemini-2.0-flash-lite (higher RPM, lower daily quota)
    """
    
    config = types.GenerateContentConfig(
        temperature=0,
        response_mime_type="application/json"
    )
    
    # Build contents - combine system and user prompts since system role isn't supported
    combined_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
    
    contents = [types.Content(
        role="user", 
        parts=[types.Part(text=combined_prompt)]
    )]
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            
            # Extract text from response
            if response.candidates and len(response.candidates) > 0:
                content = response.candidates[0].content
                if content and content.parts and len(content.parts) > 0:
                    text = content.parts[0].text
                    if text:
                        return text.strip()
            
            logger.warning(f"No content found in response (attempt {attempt + 1})")
            return "{}"
            
        except Exception as e:
            if "BlockedPromptError" in str(type(e).__name__) or "blocked" in str(e).lower():
                logger.warning(f"Prompt blocked by Gemini (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
            else:
                logger.warning(f"Gemini API error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
    
    raise Exception("Max retries exceeded")

async def extract_job_info(email_input: LLMEmailInput) -> LLMEmailOutput:
    """
    Extract job application information from an email using Google's Gemini model.
    Enhanced with robust error handling, retry logic, and direct Pydantic validation.
    
    Args:
        email_input: LLMEmailInput containing email subject, body, and optional HTML
        
    Returns:
        LLMEmailOutput with extracted job information and intent classification
    """
    
    prompt = format_email_analysis_prompt(
        subject=email_input.subject,
        body_text=email_input.body_text,
        body_html=email_input.body_html
    )
    
    try:
        system_prompt, user_prompt = prompt
        content = await _call_gemini_with_retry(system_prompt, user_prompt)
        logger.info(f"LLM raw response: {content}")
        
        cleaned_content = _clean_response(content)
        
        try:
            parsed_data = json.loads(cleaned_content)
            logger.info(f"Parsed LLM data: {parsed_data}")
            
            result = LLMEmailOutput.model_validate(parsed_data)
            
            logger.info(f"Successfully extracted job info: {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Cleaned content: {cleaned_content}")
            raise
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            logger.error(f"Parsed data: {parsed_data}")
            raise
            
    except Exception as e:
        if "BlockedPromptError" in str(type(e).__name__) or "blocked" in str(e).lower():
            logger.error("Prompt blocked by Gemini safety filters")
            return _get_fallback_output("Content blocked by safety filters")
        
        logger.error(f"First attempt failed: {e}")
        
        try:
            logger.info("Retrying with gemini-2.0-flash-lite")
            content = await _call_gemini_with_retry(
                system_prompt, 
                user_prompt,
                model_name="gemini-2.0-flash-lite",
                max_retries=1
            )
            
            cleaned_content = _clean_response(content)
            parsed_data = json.loads(cleaned_content)
            result = LLMEmailOutput.model_validate(parsed_data)
            
            logger.info(f"Fallback attempt successful: {result}")
            return result
            
        except Exception as fallback_error:
            logger.error(f"Fallback attempt failed: {fallback_error}")
            return _get_fallback_output(f"Both attempts failed: {str(e)}")



