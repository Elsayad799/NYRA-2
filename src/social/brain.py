from __future__ import annotations
import hashlib
import time

class SocialBrain:
    """Social participation + autonomous contact decisions.

    NYRA remains one shared fictional core. These decisions model continuity,
    attention, relationship and social initiative; they are not claims of
    literal consciousness.
    """
    def __init__(self, db, settings, attention=None, relationships=None):
        self.db, self.s = db, settings
        self.attention = attention
        self.relationships = relationships
        self.last_action_global = 0.0
        self.last_action_group = {}
        self.last_action_user = {}

    def observe_group(self, event):
        if event.chat_type == "private":
            return
        if self.attention:
            self.attention.observe(event)
        if self.relationships:
            self.relationships.observe(event)
        self.db.execute("""INSERT INTO social_groups(chat_id,activity,conversation_speed,last_message_at,last_bot_message_at,topic,engagement)
            VALUES(?,?,?,datetime('now'),NULL,'',0.45)
            ON CONFLICT(chat_id) DO UPDATE SET activity=MIN(1,activity+0.015),
            conversation_speed=MIN(1,conversation_speed+0.01),last_message_at=datetime('now')""",
            (event.chat_id, 0.5, 0.5))

    def group(self, chat_id):
        rows = self.db.query("SELECT * FROM social_groups WHERE chat_id=?", (chat_id,))
        return dict(rows[0]) if rows else {
            "activity": .5, "conversation_speed": .5, "engagement": .45,
            "topic": "", "last_bot_message_at": None
        }

    def choose(self, event, relationship, state):
        if event.chat_type == "private":
            return {"action":"reply", "target":"user", "score":1.0, "reason":"private_chat"}

        g = self.group(event.chat_id)
        text = (event.text or "").strip()
        low = text.lower()
        direct = bool(event.is_mention or event.is_reply_to_bot or any(x in low for x in ("nyra", "نايرا", "@nyra")))
        question = "?" in text or "؟" in text
        social_words = any(x in low for x in ("ضحك", "هههه", "😂", "مبروك", "حبيبي", "يا جماعة", "مين", "حد"))
        relevant = any(x in low for x in ("ai", "ذكاء", "بوت", "نايرا", "nyra", "minecraft", "ماينكرافت", "برمجة", "لعبة"))
        mood = str(state.get("mood", "neutral"))
        energy = float(state.get("energy", .75))
        social_need = float(state.get("social_need", .45))
        bored = mood == "bored" or social_need > .78
        curiosity = float(state.get("curiosity", .55))
        happiness = float(state.get("happiness", .55))
        sadness = float(state.get("sadness", .1))
        anger = float(state.get("anger", .05))
        familiarity = float((relationship or {}).get("familiarity", 0))
        attention_score = self.attention.score(event, relationship, state) if self.attention else 0.0

        if direct:
            action = "reply" if self._cooldown_ok(event, hard=True) else "ignore"
            return {"action":action, "target":"user", "score":1.0,
                    "reason":"directed_to_nyra" if action=="reply" else "cooldown", "attention":1.0}

        if not text or text.startswith("/") or len(text) < 3:
            return {"action":"ignore", "target":"none", "score":0.0, "reason":"not_conversational", "attention":0.0}

        score = .04
        score += .14 * curiosity if question else 0
        score += .10 * familiarity + .12 * attention_score + .10 * social_need
        score += .10 if bored else 0
        score += .08 * energy + (.08 if relevant else 0) + (.05 if social_words else 0)
        score += .06 * happiness - .12 * sadness - .10 * anger
        score -= .10 * max(0, g["conversation_speed"] - .75)
        score -= .08 * max(0, g["activity"] - .85)
        score = max(0.0, min(.72, score))
        seed = f"{event.chat_id}:{event.message_id}:{mood}:{round(energy,2)}:{round(curiosity,2)}"
        sample = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16) / 0xffffffff
        if sample < score and self._cooldown_ok(event):
            target = "user" if question or relevant else "group"
            reason = "curious_participation" if curiosity > .65 else "social_participation"
            if energy < .3: reason = "low_energy_but_interested"
            return {"action":"reply", "target":target, "score":score, "reason":reason, "attention":attention_score}
        return {"action":"ignore", "target":"none", "score":score, "reason":"not_worth_intervening", "attention":attention_score}

    def proactive_decision(self, chat_id, state, outcomes=None, goal=None):
        """Decide whether NYRA has a contextual reason to initiate a group conversation."""
        g = self.group(chat_id)
        now = time.time(); last = self.last_action_group.get(chat_id, 0.0)
        if now - last < max(self.s.group_cooldown * 2, 20):
            return {"action":"ignore", "reason":"group_cooldown"}
        if not g.get("last_message_at"):
            return {"action":"ignore", "reason":"no_observed_activity"}
        attention = self.attention.get(chat_id) if self.attention else {}
        focus = float(attention.get("focus", 0.0) or 0.0)
        topic = (attention.get("topic") or g.get("topic") or "").strip()
        energy = float(state.get("energy", .75)); curiosity = float(state.get("curiosity", .55))
        social_need = float(state.get("social_need", .45)); boredom = 1.0 if state.get("mood") == "bored" else 0.0
        goal_text = (goal.get('goal') if goal else '') or ''
        score = 0.0; reasons = []
        if topic and focus >= .35: score += .30; reasons.append("active_topic")
        if goal_text and topic: score += .16; reasons.append("goal_alignment")
        if boredom and social_need >= .60: score += .20; reasons.append("bored_social_need")
        if curiosity >= .75 and topic: score += .18; reasons.append("curiosity")
        if .30 <= g.get("activity",0) <= .78: score += .12; reasons.append("conversation_window")
        if energy < .25: score -= .20
        score = max(0.0, min(1.0, score))
        if outcomes: score = max(0.0, min(1.0, score + outcomes.bias("proactive_message", "+".join(reasons))))
        if score < .45: return {"action":"ignore", "reason":"no_strong_reason", "score":score}
        return {"action":"start", "target":"group", "score":score, "topic":topic,
                "reason":"+".join(reasons), "goal_id":(goal.get('id') if goal else None)}

    def private_candidates(self, limit=30):
        """Return users NYRA has actually interacted with and can potentially contact."""
        rows = self.db.query("""SELECT u.*, r.trust, r.familiarity, r.interaction_count AS relationship_interactions
            FROM users u LEFT JOIN relationships r ON r.user_id=u.user_id AND r.chat_id=u.user_id
            WHERE u.user_id IS NOT NULL AND u.interaction_count > 0
            ORDER BY u.last_seen ASC LIMIT ?""", (int(limit),))
        return [dict(r) for r in rows]

    def private_proactive_decision(self, user_row, state, outcomes=None):
        """Choose whether to start a private chat with a known user.

        Telegram delivery is asynchronous: if the user is temporarily offline,
        Telegram can deliver the message when they reconnect, subject to normal
        bot/user availability and whether the user blocked the bot.
        """
        user_id = int(user_row["user_id"])
        last_seen = str(user_row.get("last_seen") or "")
        now = time.time()
        last_action = self.last_action_user.get(user_id, 0.0)
        if now - last_action < max(self.s.user_cooldown * 10, 30):
            return {"action":"ignore", "reason":"user_cooldown", "score":0.0}
        try:
            recent = self.db.query("SELECT created_at FROM action_outcomes WHERE target_user_id=? AND action_type IN ('private_check_in','private_self_image') ORDER BY id DESC LIMIT 1", (user_id,))
        except Exception:
            recent = []
        if recent:
            try:
                if now - float(recent[0]["created_at"]) < 8 * 3600:
                    return {"action":"ignore", "reason":"recent_private_contact", "score":0.0}
            except Exception:
                pass
        if not last_seen:
            return {"action":"ignore", "reason":"unknown_last_seen", "score":0.0}

        # SQLite timestamps are UTC. Keep this calculation conservative: stale
        # records are only a signal, never proof that a person is literally offline.
        stale_signal = min(1.0, max(0.0, (now - self._parse_sqlite_now(last_seen)) / 86400.0))
        familiarity = float(user_row.get("familiarity") or 0.0)
        trust = float(user_row.get("trust") or 0.2)
        social_need = float(state.get("social_need", .45)); desire_to_talk = float(state.get("desire_to_talk", social_need)); curiosity = float(state.get("curiosity", .55))
        energy = float(state.get("energy", .75)); mood = str(state.get("mood", "neutral"))
        attachment = float(state.get("attachment", .25))
        score = 0.0; reasons=[]
        if stale_signal >= .18: score += .28; reasons.append("silence")
        if stale_signal >= .55: score += .16; reasons.append("long_silence")
        if familiarity >= .20: score += .16; reasons.append("familiarity")
        if trust >= .45: score += .08; reasons.append("trust")
        if social_need >= .65: score += .12; reasons.append("social_drive")
        if desire_to_talk >= .70: score += .10; reasons.append("desire_to_talk")
        if curiosity >= .75: score += .08; reasons.append("curiosity")
        if attachment >= .55: score += .10; reasons.append("attachment")
        if mood in ("sad", "bored", "curious") and energy >= .30: score += .08; reasons.append("mood")
        if energy < .25: score -= .20
        if outcomes: score += outcomes.bias("private_check_in", "+".join(reasons))
        score=max(0.0,min(1.0,score))
        threshold=.58
        if score < threshold:
            return {"action":"ignore","reason":"not_now","score":score,"user_id":user_id}
        kind = "check_in"
        if "long_silence" in reasons and familiarity >= .35: kind="missed_you"
        elif "curiosity" in reasons: kind="question"
        return {"action":"contact","target":"user","user_id":user_id,"score":score,"reason":"+".join(reasons),"kind":kind}

    @staticmethod
    def _parse_sqlite_now(value):
        import datetime
        try:
            dt=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
            if dt.tzinfo is None: dt=dt.replace(tzinfo=datetime.timezone.utc)
            return dt.timestamp()
        except Exception:
            # SQLite values can be slightly malformed; treat them as recent.
            return time.time()

    def mark_response(self, chat_id, user_id):
        now = time.monotonic(); self.last_action_global=now
        self.last_action_group[chat_id]=now; self.last_action_user[user_id]=now
        if self.attention: self.attention.mark_attention(chat_id,user_id)
        self.db.execute("UPDATE social_groups SET last_bot_message_at=datetime('now'), engagement=MIN(1,engagement+.03), conversation_speed=MAX(0,conversation_speed-.04) WHERE chat_id=?", (chat_id,))

    def _cooldown_ok(self, event, hard=False):
        now=time.monotonic()
        global_cd=self.s.global_cooldown if not hard else max(.5,self.s.global_cooldown)
        group_cd=self.s.group_cooldown if not hard else max(3,self.s.group_cooldown)
        user_cd=self.s.user_cooldown if not hard else max(1,self.s.user_cooldown)
        return (now-self.last_action_global >= global_cd and
                now-self.last_action_group.get(event.chat_id,0) >= group_cd and
                now-self.last_action_user.get(event.user_id,0) >= user_cd)
