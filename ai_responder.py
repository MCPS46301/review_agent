"""
AI response generation using Claude Opus 4.6.

Generates personalized review responses for Macomb Powersports:
- 1-2 star reviews: Empathetic, professional responses for owner approval
- 3-5 star reviews: Warm, welcoming responses that auto-post
"""

import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

BUSINESS_CONTEXT = f"""
You are writing review responses on behalf of {settings.business_name}, a powersports dealership
in Macomb, Michigan that sells and services motorcycles, ATVs, UTVs, watercraft, and snowmobiles.
The dealership is family-oriented, community-focused, and prides itself on excellent customer service.
Always sign responses warmly and represent the brand professionally.
"""

POSITIVE_RESPONSE_PROMPT = """
Write a warm, genuine, and personal response to this positive customer review for {business}.

Review details:
- Reviewer: {reviewer_name}
- Star rating: {rating}/5
- Review: "{review_text}"

Guidelines:
- Be warm, enthusiastic, and personal — not corporate or generic
- Specifically reference something from their review to show you read it
- Thank them sincerely for taking time to leave a review
- Welcome them to the "{business} family" naturally within the response
- Express genuine excitement to serve them again
- Keep it under 100 words
- Do NOT use exclamation points more than twice
- Do NOT start with "Thank you" — vary the opening
- Sound like a real, friendly business owner, not a bot

Write ONLY the response text — no quotes, no labels, no preamble.
"""

NEGATIVE_RESPONSE_PROMPT = """
Write a professional, empathetic response to this negative customer review for {business}.

Review details:
- Reviewer: {reviewer_name}
- Star rating: {rating}/5
- Review: "{review_text}"

Guidelines:
- Acknowledge the customer's experience and feelings first
- Sincerely apologize for falling short of their expectations
- Do NOT make excuses or get defensive
- Offer a concrete next step (e.g., call us directly, ask for the owner)
- Include a direct contact offer: invite them to call or visit so we can make it right
- Keep it under 150 words
- Sound empathetic and genuine, not scripted
- Show this is not the experience you want for any customer

The owner will review this response before it is sent, so it should be a solid starting draft.

Write ONLY the response text — no quotes, no labels, no preamble.
"""

NO_TEXT_FALLBACK = "(No written review — rating only)"


def generate_response(
    reviewer_name: str,
    rating: int,
    review_text: str | None,
) -> str:
    """
    Generate an AI review response using Claude Opus 4.6.

    Args:
        reviewer_name: The name of the reviewer
        rating: Star rating (1-5)
        review_text: The review content (may be None for rating-only reviews)

    Returns:
        Generated response text
    """
    text = review_text.strip() if review_text and review_text.strip() else NO_TEXT_FALLBACK

    if rating <= 2:
        prompt_template = NEGATIVE_RESPONSE_PROMPT
    else:
        prompt_template = POSITIVE_RESPONSE_PROMPT

    user_prompt = prompt_template.format(
        business=settings.business_name,
        reviewer_name=reviewer_name,
        rating=rating,
        review_text=text,
    )

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=400,
        thinking={"type": "adaptive"},
        system=BUSINESS_CONTEXT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    for block in response.content:
        if block.type == "text":
            return block.text.strip()

    return ""


def regenerate_response(
    reviewer_name: str,
    rating: int,
    review_text: str | None,
    owner_notes: str = "",
) -> str:
    """
    Regenerate a response incorporating optional owner feedback/notes.
    """
    text = review_text.strip() if review_text and review_text.strip() else NO_TEXT_FALLBACK

    if rating <= 2:
        base_prompt = NEGATIVE_RESPONSE_PROMPT
    else:
        base_prompt = POSITIVE_RESPONSE_PROMPT

    user_prompt = base_prompt.format(
        business=settings.business_name,
        reviewer_name=reviewer_name,
        rating=rating,
        review_text=text,
    )

    if owner_notes:
        user_prompt += f"\n\nAdditional guidance from the owner: {owner_notes}"

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=400,
        thinking={"type": "adaptive"},
        system=BUSINESS_CONTEXT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    for block in response.content:
        if block.type == "text":
            return block.text.strip()

    return ""
