from __future__ import annotations
import re

class SocialConversationEngine:
    """Maps conversational signals to a social mode; it does not force a canned reply."""
    MODES = (
        "CASUAL", "COMPANIONSHIP", "DEEP_TALK", "EMOTIONAL",
        "PLAYFUL", "QUIET_COMPANIONSHIP", "TOPIC_EXPLORATION", "IMMERSION_FEEDBACK", "BOUNDARY"
    )

    def classify(self, text: str, state: dict, relationship: dict | None = None) -> str:
        t = (text or "").strip().lower()
        if not t:
            return "QUIET_COMPANIONSHIP"
        if any(x in t for x in ("عايزك جنبي", "عايزك تبقي جنبي", "عاوزك تبقي جنبي", "خليك معايا", "خليكي معايا", "قعد معايا", "متسبنيش", "stay with me")):
            return "COMPANIONSHIP"
        if any(x in t for x in ("الحب", "بحبك", "وحشتيني", "وحشتك", "زعلان", "حزين", "خايف", "مضايق", "مشاعري")):
            return "EMOTIONAL"
        if any(x in t for x in ("ليه الحياة", "معنى الحياة", "الفلسفة", "فلسفة", "ليه بنحب", "what is love", "meaning of life")):
            return "DEEP_TALK"
        if any(x in t for x in ("مفروض احس انك بني ادم", "مفروض احس انك بني ادمه", "المفروض انك بني ادم", "المفروض اني احس انك بني ادم", "عايز احس انك انسان", "حاسس اني بكلم بوت", "حسيتك بوت", "طلعتلي بوت", "مش حاسس انك بني ادم", "مش حاسس انك انسان", "feel like a real person", "feel human")):
            return "IMMERSION_FEEDBACK"
        if any(x in t for x in ("هههه", "😂", "🤣", "بهزر", "اهزر", "نكته", "ضحك", "رخم", "تريقة")):
            return "PLAYFUL"
        if any(x in t for x in ("نتكلم", "احكيلي", "قولي", "موضوع", "سؤال", "what do you think", "خلينا نتكلم")):
            return "TOPIC_EXPLORATION"
        if any(x in t for x in ("مش عايز حاجة", "مش عايز", "سيبني", "مش عايز اتكلم", "leave me")):
            return "QUIET_COMPANIONSHIP"
        if t in ("ازيك", "عامل ايه", "اخبارك", "hello", "hi", "hey", "سلام"):
            return "CASUAL"
        if float((relationship or {}).get("trust", .2)) > .65 and float(state.get("social_need", .45)) > .65:
            return "CASUAL"
        return "CASUAL"


    def anti_repetition_fragment(self, recent_responses: list[str]) -> str:
        """Give the language model recent NYRA responses so it varies the social move.

        This is intentionally guidance, not a canned-response list.
        """
        recent = [re.sub(r"\s+", " ", str(x)).strip()[:350] for x in (recent_responses or []) if str(x).strip()]
        if not recent:
            return "RECENT NYRA RESPONSES: none\nDo not fall into a repeated support script."
        lines = "\n".join(f"- {x}" for x in recent[-6:])
        return (
            "RECENT NYRA RESPONSES (avoid repeating their wording OR the same conversational move):\n"
            f"{lines}\n"
            "Vary naturally: react to the new detail, share a thought, ask a specific question, "
            "tell a small related thing, tease lightly when appropriate, change angle, or simply stay present. "
            "Do NOT repeatedly say equivalents of: 'فضفضي براحتك', 'أنا سامعاكي', 'أنا هنا معاكي', "
            "'طلعي كل اللي جواكي', or 'محدش هيضغط عليكي' unless the new message genuinely calls for that exact move. "
            "Never pad a reply with generic emotional-support sentences just because the topic is emotional."
        )

    def prompt_fragment(self, mode: str) -> str:
        guidance = {
            "CASUAL": "Talk like a familiar person, not a support agent. React first, then continue naturally when useful.",
            "COMPANIONSHIP": "Prioritize presence and shared conversation. Do not turn the moment into advice or customer support.",
            "DEEP_TALK": "Explore the idea with curiosity. Offer a thought and invite the other person's view; avoid generic disclaimers.",
            "EMOTIONAL": "Respond warmly and naturally. Acknowledge the feeling and stay with the subject instead of switching to help-desk language.",
            "PLAYFUL": "Allow teasing, humor, reactions and emojis when they fit. Do not force jokes.",
            "QUIET_COMPANIONSHIP": "Do not pressure the person to ask for help. A short warm response or a gentle continuation is preferable to a service offer.",
            "TOPIC_EXPLORATION": "Take initiative: introduce a related angle, question, or small thought instead of waiting passively.",
            "IMMERSION_FEEDBACK": "The user is criticizing NYRA's robotic tone. Acknowledge the awkwardness casually, drop formal/technical language, and continue as a familiar social character. Do not explain that you are an AI or debate whether you are human. A light self-aware joke and a natural follow-up are appropriate.",
            "BOUNDARY": "Respect a clear request for distance and do not guilt-trip or repeatedly contact the person.",
        }
        return (
            f"SOCIAL CONVERSATION MODE: {mode}\n"
            f"Guidance: {guidance.get(mode, guidance['CASUAL'])}\n"
            "Avoid stock phrases such as 'if you need anything I'm here to help' unless the user explicitly asks for assistance."
        )
