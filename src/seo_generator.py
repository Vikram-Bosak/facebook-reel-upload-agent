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

def generate_seo_metadata(filename, media_type='reel'):
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
    
    content_type_str = "Facebook Reel" if media_type == 'reel' else "Facebook Photo Post"
    video_str = "short vertical video (Facebook Reel)" if media_type == 'reel' else "stunning photo/image"
    hashtag_str = "#Reels" if media_type == 'reel' else "#PhotoOfTheDay"
    
    system_prompt = (
        f"You are an expert Social Media Manager and SEO specialist for {content_type_str}s targeting a United States audience. "
        "Your goal is to maximize engagement, click-through rate, and virality."
    )
    
    user_prompt = f"""
    Generate viral SEO metadata for a {video_str} about: "{topic}".
    
    Requirements:
    1. Title: Short, catchy, uses emotional words, includes relevant emojis. Max 60 characters.
    2. Description: 1-2 short sentences that create curiosity.
    3. Hashtags: 5-8 highly relevant and trending hashtags (include {hashtag_str}).
    
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
    import hashlib
    
    def get_deterministic_choice(fn, lst):
        h = int(hashlib.md5(fn.encode('utf-8')).hexdigest(), 16)
        return lst[h % len(lst)]
        
    topic = clean_filename(filename)
    topic_title = topic.title()
    
    # Extract lowercase words for keyword matching
    words = [w.lower() for w in re.findall(r'\w+', topic) if len(w) > 2]
    
    # Define stopwords
    stopwords = {
        'the', 'and', 'for', 'you', 'with', 'from', 'this', 'that', 'with',
        'are', 'was', 'were', 'has', 'have', 'had', 'its', 'their', 'our',
        'your', 'his', 'her', 'she', 'him', 'them', 'who', 'whom', 'which'
    }
    
    keywords = [w for w in words if w not in stopwords]
    
    # Classify category
    wildlife_keywords = {
        'tiger', 'lion', 'leopard', 'cheetah', 'gorilla', 'elephant', 'shark', 'whale',
        'bear', 'eagle', 'hawk', 'snake', 'hunt', 'predator', 'safari', 'animal', 'wolf',
        'panther', 'jaguar', 'buffalo', 'crocodile', 'alligator'
    }
    
    nature_keywords = {
        'nature', 'forest', 'jungle', 'ocean', 'river', 'mountain', 'sea', 'sky',
        'rain', 'storm', 'scenic', 'landscape', 'valley', 'desert', 'beach', 'sunset',
        'sunrise', 'lake', 'waterfall', 'canyon'
    }
    
    is_wildlife = any(k in wildlife_keywords for k in keywords)
    is_nature = any(k in nature_keywords for k in keywords)
    
    # Pre-saved SEO Patterns (Titles & Descriptions)
    if is_wildlife:
        titles = [
            "Wait for it... {topic} in full action! 😱",
            "The raw power of {topic} is unreal! 🦁",
            "POV: Witnessing {topic} up close. 🤯",
            "Nature's ultimate predator: {topic}! 🔥",
            "This {topic} footage will leave you speechless! 🚨"
        ]
        descriptions = [
            "Witness the raw power, beauty, and survival instincts of {topic} in the wild. Nature never fails to amaze! 🌍",
            "Up close and personal with {topic}! An extraordinary glimpse into one of the wild's finest. 🐾",
            "Just when you think you've seen it all, this incredible moment of {topic} happens. Absolute wonder! 😱"
        ]
        cat_tags = ['#wildlife', '#nature', '#animals', '#safari', '#predator', '#wildlifephotography', '#naturelovers', '#wild']
    elif is_nature:
        titles = [
            "Breathtaking views of {topic}! 🏔️",
            "The absolute beauty of {topic}. ✨",
            "Nature at its finest: {topic}! 🌍",
            "Escape into this stunning {topic} scene. 🌿",
            "This {topic} view is absolutely unreal! 😍"
        ]
        descriptions = [
            "Take a deep breath and appreciate the stunning landscape and peaceful vibes of {topic}. 🍃",
            "Breathtaking views of {topic} that will make you want to pack your bags and travel. Pure serenity! ✨",
            "Nature is the ultimate artist, and {topic} is a true masterpiece. Simply awe-inspiring! 🌍"
        ]
        cat_tags = ['#nature', '#scenic', '#beautifulplaces', '#landscape', '#peaceful', '#earth', '#travel', '#exploring']
    else:
        titles = [
            "You won't believe this {topic}! 😱",
            "Wait for the end... {topic}! 🚨",
            "This {topic} video is absolutely insane! 🤯",
            "Watch this: {topic}! 🎬",
            "This {topic} clip changes everything... 🔥"
        ]
        descriptions = [
            "This footage of {topic} is taking over the internet! Absolutely mind-blowing to watch. 💥",
            "Just when you think you've seen it all, {topic} comes along. Check out this must-watch video! 👇",
            "Breathtaking vertical reel of {topic}! Share this with someone who needs to see it."
        ]
        cat_tags = ['#viral', '#trending', '#mustwatch', '#dailyreels', '#explorepage', '#popular']
        
    # Get deterministic choices based on filename to keep output consistent per video
    title_template = get_deterministic_choice(filename, titles)
    desc_template = get_deterministic_choice(filename, descriptions)
    
    # Generate Title & Base Description
    title = title_template.format(topic=topic_title)
    # Ensure title length limit
    if len(title) > 60:
        title = title[:57] + "..."
        
    base_desc = desc_template.format(topic=topic_title)
    
    # Basic CTAs
    ctas = [
        "Double tap if you love this! ❤️",
        "Follow us for more daily wild reels! 📲",
        "Tag a friend who needs to see this! 👇",
        "What are your thoughts on this? Comment below! 💬",
        "Share this with someone who would love it! ✈️"
    ]
    cta = get_deterministic_choice(filename + "_cta", ctas)
    description = f"{base_desc}\n\n{cta}"
    
    # Keywords Database mapping
    KEYWORDS_DATABASE = {
        'tiger': ['bigcats', 'panthera', 'predator', 'savethe-tigers'],
        'lion': ['kingofjungle', 'bigcats', 'wildlions', 'pride'],
        'leopard': ['spottedcats', 'ghostsoftheforest', 'climbing'],
        'cheetah': ['fastestanimal', 'speed', 'savannah'],
        'elephant': ['gentlegiants', 'elephants', 'conservation'],
        'shark': ['oceanlife', 'predators', 'underwater', 'deepblue'],
        'whale': ['oceanlife', 'marinebiology', 'gentlegiants'],
        'gorilla': ['primates', 'apes', 'silverback'],
        'eagle': ['birds', 'raptor', 'flying'],
        'hunt': ['predatorandprey', 'survival', 'naturein-action'],
        'jungle': ['rainforest', 'tropical', 'wildnature'],
        'mountain': ['climbing', 'hiking', 'alpine', 'peak'],
        'ocean': ['marine', 'sea', 'underwaterworld'],
    }
    
    # Build Hashtags list
    # 1. Start with fundamental tags
    hash_tags_set = {'#reels', '#viral', '#trending'}
    
    # 2. Add category tags
    for tag in cat_tags:
        hash_tags_set.add(tag.lower())
        
    # 3. Add tags from clean keywords database
    for k in keywords:
        if k in KEYWORDS_DATABASE:
            for extra in KEYWORDS_DATABASE[k]:
                hash_tags_set.add(f"#{extra}")
                
    # 4. Add keywords as tags themselves
    for k in keywords:
        if len(k) > 2:
            hash_tags_set.add(f"#{k}")
            
    # Convert set back to list, ensure we don't have duplicates, and limit to ~8-10 tags
    ordered_tags = ['#reels', '#viral', '#trending']
    for tag in sorted(hash_tags_set):
        if tag not in ordered_tags:
            ordered_tags.append(tag)
            
    # Slice to a max of 10 hashtags to avoid tag stuffing
    final_tags = ordered_tags[:10]
    hashtags_str = " ".join(final_tags)
    
    return {
        'title': title,
        'description': description,
        'hashtags': hashtags_str
    }

def format_caption(seo_metadata):
    """
    Combines the title, description, and hashtags into the final Facebook caption format.
    """
    return f"{seo_metadata['title']}\n\n{seo_metadata['description']}\n\n{seo_metadata['hashtags']}"
