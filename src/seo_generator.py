import os
import re
from openai import OpenAI
import json
try:
    from .logger import logger
except ImportError:
    from logger import logger

def clean_filename(filename):
    # Remove extension and replace underscores/hyphens with spaces
    name_without_ext = os.path.splitext(filename)[0]
    cleaned = re.sub(r'[-_]', ' ', name_without_ext)
    return cleaned.strip()

def generate_seo_metadata(filename):
    """
    Generates SEO title, description, and hashtags based on the video filename.
    Returns a dictionary with 'title', 'description', and 'hashtags'.
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        logger.warning("OPENAI_API_KEY not found. Using fallback metadata generator.")
        return generate_fallback_metadata(filename)
        
    base_url = os.environ.get('OPENAI_API_BASE_URL')
    model = os.environ.get('OPENAI_API_MODEL', 'gpt-3.5-turbo')
    
    if base_url:
        client = OpenAI(api_key=api_key, base_url=base_url)
    else:
        client = OpenAI(api_key=api_key)
        
    topic = clean_filename(filename)
    
    system_prompt = (
        "You are an expert Social Media Manager and SEO specialist for Facebook Reels targeting a United States audience. "
        "Your goal is to maximize engagement, click-through rate, and virality."
    )
    
    user_prompt = f"""
    Generate viral SEO metadata for a short vertical video (Facebook Reel) about: "{topic}".
    
    Requirements:
    1. Title: Short, catchy, uses emotional words, includes relevant emojis. Max 60 characters.
    2. Description: 1-2 short sentences that create curiosity.
    3. Hashtags: 5-8 highly relevant and trending hashtags (include #Reels).
    
    Format the output exactly as JSON:
    {{
        "title": "...",
        "description": "...",
        "hashtags": "#tag1 #tag2 ..."
    }}
    """
    
    try:
        params = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7
        }
        if "gpt-" in model:
            params["response_format"] = {"type": "json_object"}
            
        response = client.chat.completions.create(**params)
        
        result_json = response.choices[0].message.content.strip()
        
        # Clean markdown code blocks if present
        if result_json.startswith("```"):
            result_json = re.sub(r'^```(?:json)?\n', '', result_json)
            result_json = re.sub(r'\n```$', '', result_json)
            result_json = result_json.strip()
            
        data = json.loads(result_json)
        
        return {
            'title': data.get('title', topic.title()),
            'description': data.get('description', f"Amazing video about {topic}!"),
            'hashtags': data.get('hashtags', "#Reels #Viral #Trending")
        }
        
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return generate_fallback_metadata(filename)

def generate_fallback_metadata(filename):
    topic = clean_filename(filename).title()
    return {
        'title': f"{topic} 🔥",
        'description': f"Check out this amazing video! #Reels #Viral #{topic.replace(' ', '')}",
        'hashtags': f"#Reels #Viral #Trending #{topic.replace(' ', '')}"
    }

def format_caption(seo_metadata):
    """
    Combines the title, description, and hashtags into the final Facebook caption format.
    """
    return f"{seo_metadata['title']}\n\n{seo_metadata['description']}\n\n{seo_metadata['hashtags']}"
