import os
import re
import json
try:
    from .logger import logger
except ImportError:
    from logger import logger


def clean_filename(filename):
    """Remove extension and replace underscores/hyphens with spaces."""
    name_without_ext = os.path.splitext(filename)[0]
    cleaned = re.sub(r'[-_]', ' ', name_without_ext)
    return cleaned.strip()


def generate_seo_metadata(filename, media_type='reel'):
    """
    Generates SEO title, description, and hashtags for wildlife/nature content
    using the NVIDIA API with a wildlife-specific prompt.

    Returns a dict with keys: title, description, facebook_caption, hashtags, tags
    """
    api_key = os.environ.get('NVIDIA_API_KEY')
    if not api_key:
        logger.warning("NVIDIA_API_KEY not found. Using fallback metadata generator.")
        return generate_fallback_metadata(filename)

    try:
        from openai import OpenAI
    except ImportError:
        logger.error("openai package not installed. Install with: pip install openai")
        return generate_fallback_metadata(filename)

    client = OpenAI(
        api_key=api_key,
        base_url='https://integrate.api.nvidia.com/v1'
    )

    topic = clean_filename(filename)

    content_type_str = "Facebook Reel" if media_type == 'reel' else "Facebook Photo Post"
    video_str = "short vertical video (Facebook Reel)" if media_type == 'reel' else "stunning photo/image"
    hashtag_str = "#Reels" if media_type == 'reel' else "#PhotoOfTheDay"

    system_prompt = (
        "You are an expert Wildlife and Nature social media manager and SEO specialist "
        "targeting a United States audience. "
        "Your goal is to maximize engagement, click-through rate, and virality "
        "for wildlife, animal, and nature content."
    )

    user_prompt = f"""
    Generate viral SEO metadata for a {video_str} about: "{topic}".

    Requirements:
    1. short_headline: Short, catchy, uses emotional/wildlife words, includes a relevant emoji. Max 60 characters.
    2. story: 2-3 sentences that create curiosity about this wildlife/nature moment. Be vivid and dramatic.
    3. category: Choose exactly one from: Predator, Endangered, Attack, Nature, Underwater

    Format the output exactly as JSON (no markdown):
    {{
        "short_headline": "...",
        "story": "...",
        "category": "..."
    }}
    """

    try:
        response = client.chat.completions.create(
            model='meta/llama-3.1-70b-instruct',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )

        result_json = response.choices[0].message.content.strip()

        # Clean markdown code blocks if present
        if result_json.startswith("```"):
            result_json = re.sub(r'^```(?:json)?\n', '', result_json)
            result_json = re.sub(r'\n```$', '', result_json)
            result_json = result_json.strip()

        data = json.loads(result_json)

        title = data.get('short_headline', '')
        if len(title) > 60:
            title = title[:57] + "..."

        story = data.get('story', '')
        category = data.get('category', 'Nature')

        # Build description with story
        description = story

        # Generate upload metadata for Stage 2 (YouTube + Facebook)
        upload_meta = generate_upload_metadata(
            title=title,
            description=description,
            topic=topic,
            category=category,
            media_type=media_type
        )

        return {
            'title': title,
            'description': description,
            'facebook_caption': upload_meta['facebook_caption'],
            'hashtags': upload_meta['hashtags'],
            'tags': upload_meta['tags']
        }

    except Exception as e:
        logger.error(f"Error calling NVIDIA API: {e}")
        return generate_fallback_metadata(filename)


def generate_upload_metadata(title, description, topic, category='Nature', media_type='reel'):
    """
    Stage 2 SEO: Generate platform-specific upload metadata.
    Returns dict with YouTube and Facebook optimized content.
    """
    topic_title = topic.title()

    # ---- YouTube Metadata ----
    yt_title = f"{title} | {topic_title} Wildlife 🌍"
    if len(yt_title) > 100:
        yt_title = yt_title[:97] + "..."

    yt_description = (
        f"{description}\n\n"
        f"🎬 Incredible wildlife moment featuring {topic_title} in its natural habitat.\n\n"
        f"🌍 Welcome to our channel — your daily dose of the wild!\n"
        f"👇 LIKE, SUBSCRIBE & hit the 🔔 for more wildlife content!\n\n"
        f"🏷️ Keywords: {topic_title}, wildlife, animal, nature, safari, "
        f"wild animals, wildlife documentary, animal kingdom, wild encounters, "
        f"nature is amazing, predator, endangered species, animal attack, "
        f"underwater wildlife, marine life, forest animals, jungle wildlife\n\n"
        f"#Wildlife #Nature #Animals #{topic_title.replace(' ', '')} "
        f"#WildlifeDocumentary #AnimalKingdom #NatureIsAmazing #Safari"
    )

    yt_tags = [
        'wildlife', 'nature', 'animals', topic_title.lower().replace(' ', ''),
        'wildlife documentary', 'animal kingdom', 'nature is amazing',
        'safari', 'wild animals', 'nature video', 'wild encounters',
        'predator', 'endangered species', 'animal attack',
        'underwater wildlife', 'marine life', 'forest animals',
        'jungle wildlife', 'animal video', 'wildlife photography'
    ]

    # ---- Facebook Caption ----
    fb_ctas = [
        "🔥 Follow for daily wildlife content that will leave you speechless!",
        "🐾 Tag someone who needs to see this incredible moment!",
        "⚡ Share this with a wildlife lover — they'll thank you!",
        "🌍 Nature never ceases to amaze! Double tap if you agree!",
        "💥 This is why we protect the wild! Share to spread the word!"
    ]

    import hashlib
    cta_hash = int(hashlib.md5(f"{topic}_fb".encode()).hexdigest(), 16)
    fb_cta = fb_ctas[cta_hash % len(fb_ctas)]

    fb_caption = f"🐾 {title}\n\n{description}\n\n{fb_cta}"

    fb_hashtags = [
        '#wildlife', '#nature', '#animals', '#safari',
        '#wildlifephotography', '#naturelovers', '#animalsofinstagram',
        '#wildlifeonearth'
    ]

    # Add category-specific hashtags
    category_hashtag_map = {
        'Predator': ['#predator', '#apexpredator', '#huntingskills'],
        'Endangered': ['#endangered', '#conservation', '#savewildlife'],
        'Attack': ['#wildlifeencounter', '#predatorvsprey', '#animalattack'],
        'Nature': ['#naturephotography', '#earthfocus', '#ourplanet'],
        'Underwater': ['#underwater', '#marinebiology', '#oceanlife', '#deepblue']
    }
    fb_hashtags.extend(category_hashtag_map.get(category, []))

    hashtags_str = " ".join(fb_hashtags)

    return {
        'youtube_title': yt_title,
        'youtube_description': yt_description,
        'youtube_tags': yt_tags,
        'facebook_caption': fb_caption,
        'hashtags': hashtags_str,
        'tags': yt_tags
    }


def generate_fallback_metadata(filename):
    """Deterministic fallback SEO generator with viral wildlife-specific templates."""
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
        'the', 'and', 'for', 'you', 'with', 'from', 'this', 'that',
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

    # More viral, wildlife-specific fallback templates
    if is_wildlife:
        titles = [
            "This {topic} moment is absolutely INSANE! 😱🔥",
            "You won't survive watching {topic} in action! 🦁💥",
            "Nature's most powerful {topic} just did THIS! 🤯🐾",
            "POV: {topic} is hunting and it's TERRIFYING! ⚡👀",
            "When {topic} goes FULL BEAST MODE... 🏆🔥",
            "WARNING: {topic} footage too intense for most! 🚨🐾",
            "This {topic} just ended someone's whole career! 💀🦁",
            "The {topic} didn't come to play — pure WILD! 🐾⚡"
        ]
        descriptions = [
            "Witness the raw, untamed power of {topic} like never before! Nature's ultimate predator at its finest — this is the real animal kingdom. 🌍🐾",
            "This is NOT a movie — this is REAL wildlife! {topic} in full hunting mode is something you have to see to believe. Absolutely jaw-dropping! 😱🔥",
            "The moment {topic} decided to show everyone who's boss. Pure adrenaline, pure nature, pure WILD. Nature always wins! 💥🦁",
            "They said wildlife was beautiful — they didn't mention it could be THIS intense! {topic} in its element is both terrifying and magnificent. ⚡🌍"
        ]
        cat_tags = ['#wildlife', '#nature', '#animals', '#safari', '#predator',
                    '#wildlifephotography', '#naturelovers', '#wild', '#animalattack',
                    '#bigcats', '#apexpredator']
    elif is_nature:
        titles = [
            "This {topic} view is illegally beautiful! 😍🏔️",
            "Nature really said 'hold my beer' with this {topic}! 🌿✨",
            "I can't believe this {topic} is REAL! 🤯🌈",
            "POV: You found Earth's best kept secret — {topic}! 🌍💚",
            "This {topic} scenery belongs on another planet! 🪐💫",
            "WARNING: {topic} will make you quit your job and travel! ✈️🌍"
        ]
        descriptions = [
            "This is what heaven looks like on Earth. {topic} in all its breathtaking glory — nature really is the greatest artist of all time! 🎨🏔️",
            "Stop scrolling. Take a deep breath and let {topic} heal your soul. Nature therapy at its absolute finest! 🍃💚",
            "If this view of {topic} doesn't make you appreciate planet Earth, nothing will. Pure magic, pure nature, pure bliss! ✨🌍",
            "Pack your bags. We're going to {topic}. This stunning scenery is calling and you NEED to answer! 🏞️🎒"
        ]
        cat_tags = ['#nature', '#scenic', '#beautifulplaces', '#landscape', '#peaceful',
                    '#earth', '#travel', '#exploring', '#naturephotography', '#wanderlust']
    else:
        titles = [
            "I can't believe what just happened with this {topic}! 😱🔥",
            "WATCH: {topic} moment that broke the internet! 🤯💥",
            "This {topic} footage is absolutely UNHINGED! 🚨👀",
            "The {topic} clip you didn't know you needed today! 🎬⚡",
            "Stop everything — this {topic} is NEXT LEVEL! 🏆🔥",
            "This {topic} video is giving main character energy! 💫🐾"
        ]
        descriptions = [
            "You are NOT ready for this {topic} footage! This is the kind of content that stops your scroll and leaves you speechless. Absolute MUST-watch! 🔥💥",
            "The internet didn't know it needed this {topic} moment — but here we are, and it's everything! Share this before it blows up! 🚀👇",
            "We've seen a lot of {topic} content but THIS is the one that takes the crown. Pure entertainment, pure chaos, pure wild! 👑⚡"
        ]
        cat_tags = ['#viral', '#trending', '#mustwatch', '#dailyreels', '#explorepage',
                    '#popular', '#fyp', '#reelsviral']

    # Get deterministic choices based on filename to keep output consistent per video
    title_template = get_deterministic_choice(filename, titles)
    desc_template = get_deterministic_choice(filename, descriptions)

    # Generate Title & Base Description
    title = title_template.format(topic=topic_title)
    # Ensure title length limit
    if len(title) > 60:
        title = title[:57] + "..."

    base_desc = desc_template.format(topic=topic_title)

    # Wildlife-themed CTAs
    ctas = [
        "🔥 Follow for DAILY wildlife content that will blow your mind!",
        "🐾 Tag a friend who NEEDS to see this incredible moment!",
        "🌍 Double tap if nature just left you SPEECHLESS!",
        "💥 Share this with someone who loves the wild!",
        "⚡ Comment 'WILD' if this gave you chills! 🥶",
        "🦁 Hit that follow button — the wild never stops! 📲",
        "🎬 Save this for later — you'll want to watch it again! 🔖",
        "🌍 Nature always finds a way. Share to spread the word! 🌎"
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

    # Convert set back to list, ensure no duplicates, and limit to ~8-10 tags
    ordered_tags = ['#reels', '#viral', '#trending']
    for tag in sorted(hash_tags_set):
        if tag not in ordered_tags:
            ordered_tags.append(tag)

    # Slice to a max of 10 hashtags to avoid tag stuffing
    final_tags = ordered_tags[:10]
    hashtags_str = " ".join(final_tags)

    # Generate tags list (YouTube-style)
    tags_list = [k for k in keywords if len(k) > 2]
    tags_list.extend(['wildlife', 'nature', 'animals', 'safari'])

    # Determine category for upload metadata
    if is_wildlife:
        category = 'Predator'
    elif is_nature:
        category = 'Nature'
    else:
        category = 'Nature'

    # Generate upload metadata for Stage 2
    upload_meta = generate_upload_metadata(
        title=title,
        description=description,
        topic=topic,
        category=category,
        media_type='reel'
    )

    return {
        'title': title,
        'description': description,
        'facebook_caption': upload_meta['facebook_caption'],
        'hashtags': hashtags_str,
        'tags': upload_meta['tags']
    }


def format_caption(seo_metadata):
    """
    Combines the title, description, and hashtags into the final Facebook caption format.
    """
    return f"{seo_metadata['title']}\n\n{seo_metadata['description']}\n\n{seo_metadata['hashtags']}"
