from __future__ import annotations
import logging,re
from src.agent.context import ContextBuilder
from src.agent.events import Event
from src.agent.learning import LearningEngine
from src.agent.reflection import ReflectionEngine
from src.agent.goals import GoalStore
from src.agent.outcomes import OutcomeLearner
from src.agent.planner import PlanStore, PlanningEngine
from src.database.db import Database
from src.memory.store import MemoryStore
from src.memory.active_recall import ActiveRecall
from src.personality.identity import IDENTITY
from src.personality.state import StateStore
from src.providers.manager import ProviderManager
from src.decisions.engagement import EngagementDecision
from src.tools.registry import ToolRegistry
from src.social.brain import SocialBrain
from src.social.attention import AttentionManager
from src.social.relationship import RelationshipEngine
from src.social.conflict import ConflictEngine
from src.identity.presentation import PresentationEngine
from src.media.memory import MediaMemory
from src.media.image_generator import ImageGenerator
from src.media.shazam import ShazamEngine
from src.media.visual_identity import VisualIdentityStore
from src.agent.autonomous_private import PrivateAutonomy
from src.agent.self_model import SelfModel
from src.social.conversation import SocialConversationEngine
log=logging.getLogger('Agent')

class NYRAAgent:
    def __init__(self,db,memory,providers,state,decision,settings,tools=None):
        self.db,self.memory,self.providers,self.state,self.decision,self.settings=db,memory,providers,state,decision,settings
        self.goals=GoalStore(db); self.outcomes=OutcomeLearner(db); self.plans=PlanStore(db); self.planner=PlanningEngine(db,providers,self.plans); self.active_recall=ActiveRecall(db,memory)
        self.learning=LearningEngine(memory); self.reflection=ReflectionEngine(db,memory); self.self_model=SelfModel(db); self.conversation=SocialConversationEngine(); self.tools=tools or ToolRegistry()
        self.attention=AttentionManager(db); self.relationships=RelationshipEngine(db); self.conflicts=ConflictEngine(db); self.social=SocialBrain(db,settings,self.attention,self.relationships); self.presentations=PresentationEngine(db); self.media_memory=MediaMemory(db); self.image_generator=ImageGenerator(); self.shazam=ShazamEngine(); self.visual_identity=VisualIdentityStore(db,providers); self.private_autonomy=PrivateAutonomy(self); self.context=ContextBuilder(db,memory,settings,state,self.goals,self.active_recall,self.presentations,self.media_memory)
        try:
            self.tools.register("identify_audio", "Identify a short audio/voice clip and return title/artist when recognizable.", self.shazam.recognize_file)
        except Exception:
            pass
        self.self_model.record_capability("conversation", evidence="core NYRA response pipeline initialized", confidence=.95)
        self.self_model.record_capability("memory", evidence="persistent memory store initialized", confidence=.95)
        self.self_model.record_capability("social_decision", evidence="social brain initialized", confidence=.9)
        self.self_model.record_capability("image_generation", available=self.image_generator.available, evidence="image provider router", confidence=.8)
        self.self_model.record_capability("audio_identification", available=bool(self.shazam), evidence="Shazam engine registered", confidence=.75)
        self.self_model.observe_environment(tools=[t.name for t in self.tools.list()])
    def observe(self,e:Event):
        self.db.execute("INSERT INTO events(chat_id,user_id,message_id,event_type,text,created_at) VALUES(?,?,?,?,?,datetime('now'))",(e.chat_id,e.user_id,e.message_id,'MESSAGE_RECEIVED',e.text))
        if e.chat_type!='private':
            self.db.execute("INSERT INTO groups(chat_id,title,chat_type,first_seen,last_seen,message_count) VALUES(?,?,?,datetime('now'),datetime('now'),1) ON CONFLICT(chat_id) DO UPDATE SET last_seen=datetime('now'),message_count=message_count+1,title=excluded.title",(e.chat_id,e.chat_title,e.chat_type))
        self.db.execute("INSERT INTO users(user_id,name,username,first_seen,last_seen,interaction_count) VALUES(?,?,?,datetime('now'),datetime('now'),1) ON CONFLICT(user_id) DO UPDATE SET name=excluded.name,username=excluded.username,last_seen=datetime('now'),interaction_count=interaction_count+1",(e.user_id,e.user_name,e.username))
        self.db.execute("INSERT INTO relationships(user_id,chat_id,interaction_count) VALUES(?,?,1) ON CONFLICT(user_id,chat_id) DO UPDATE SET interaction_count=interaction_count+1,familiarity=MIN(1,familiarity+.01)",(e.user_id,e.chat_id))
        self.learning.observe(e.user_id,e.chat_id,e.text)
        if e.media_type and e.file_id:
            self.media_memory.remember(chat_id=e.chat_id,user_id=e.user_id,file_id=e.file_id,media_type=e.media_type,caption=e.caption,unique_id=e.file_unique_id,mime_type=e.mime_type,metadata=e.media_meta)
            summary=f"User {e.user_id} shared {e.media_type}; {e.caption or 'no caption'}; metadata={e.media_meta}"
            self.memory.upsert('user',e.user_id,'media_observation',summary,.35,.45,'telegram_media')
            self.learning.learn_claim(self.db,e.user_id,e.chat_id,summary,'media_observation',.45,e.user_id,'observed')
        self.conflicts.observe(e.user_id,e.chat_id,e.text); self.outcomes.observe_message(e.chat_id,e.user_id,e.text); self.outcomes.resolve_silence(); self.memory.record_event(e.user_id,e.chat_id,e.text,.15 if e.chat_type!='private' else .2); self.state.update_from_event(e.text); self.self_model.observe_environment(chat_type=e.chat_type, media_type=e.media_type, tools=[t.name for t in self.tools.list()]); self.self_model.record_reflection(f"Observed interaction with user {e.user_id}: {e.text[:220]}"); self.social.observe_group(e)
    def respond(self,e:Event,reason:str):
        context,hist,rel=self.context.build(e); emotional=self.state.get(); conflict=self.conflicts.get(e.user_id,e.chat_id)
        attention=self.attention.get(e.chat_id)
        social_mode=self.conversation.classify(e.text, emotional, rel)
        if attention.get("topic"): context += f"\nCurrent social focus: {attention.get('topic')} (focus={attention.get('focus',0):.2f})"
        self_context=self.self_model.prompt_fragment(emotional, social_mode)
        social_context=self.conversation.prompt_fragment(social_mode)
        # memories is keyed by (scope, owner_id); it does not have a chat_id column.
        # Keep the recent-response recall aligned with the actual database schema.
        recent_nyra = self.db.query(
            """SELECT content FROM memories
               WHERE scope='episodic' AND owner_id=?
                 AND kind='nyra_response' AND source='agent_response'
               ORDER BY id DESC LIMIT 6""",
            (str(e.chat_id),)
        )
        recent_responses = [str(r['content']) for r in reversed(recent_nyra)]
        diversity = self.conversation.anti_repetition_fragment(recent_responses)
        system = IDENTITY + f"""\n{self.presentations.prompt_fragment(e.user_id,e.chat_id,e.chat_type)}\n{self_context}\n{social_context}\n{diversity}\nInternal behavioral state (simulation, not consciousness): {emotional}\nRelationship conflict state: {conflict}\nBehavior guidance: {self.conflicts.behavior_guidance(e.user_id,e.chat_id)}\nEngagement reason: {reason}\nAvailable tools:\n{self.tools.describe() or '- none'}\nRules: be natural and concise; never expose private memory; never invent memory; distinguish uncertainty; do not expose hidden chain-of-thought. React as a social participant, not a customer-service agent. For casual Egyptian Arabic, never start with a formal introduction or an offer to help. If the user comments that you sound like a bot or wants you to feel more human, treat that as social feedback: laugh/react naturally, drop the formal tone, and continue the conversation instead of giving an AI disclaimer. You may use brief action-asides such as *أبتسم* or *أتنهد* when they genuinely fit, but do not overuse them. Do not announce internal modes or state. If a tool is genuinely needed, use only an available named tool and explain the result briefly."""
        msgs=[{'role':'user','content':f"Speaker {r['user_id']}: {r['text'] or ''}"} for r in hist[-self.settings.max_history:]]
        msgs.append({'role':'user','content':f"Context:\n{context}\n\nCurrent message:\n{e.text}"})
        result=self.providers.generate(msgs,system,max_tokens=900); text=result.text.strip()
        text=re.sub(r'^(NYRA\s*:\s*)','',text,flags=re.I).strip(); text=text[:3500]
        self.memory.upsert('episodic',e.chat_id,'nyra_response',text[:500],.3,.65,'agent_response')
        self.social.mark_response(e.chat_id, e.user_id); self.reflection.reflect(e.chat_id,f"NYRA responded to user {e.user_id}; reason={reason}",.6)
        return text,result
    def autonomous_tick(self):
        self.state.tick()
        self.outcomes.resolve_silence()
        self.attention.decay()
        goals=self.goals.open(limit=3)

        # Private social initiative: NYRA can decide to contact a known user even
        # when that user has not sent a new message. Telegram itself handles
        # eventual delivery when the recipient reconnects, if the chat remains available.
        for user_row in self.social.private_candidates(limit=30):
            state = self.state.get()
            decision = self.social.private_proactive_decision(user_row, state, self.outcomes)
            if decision.get("action") != "contact":
                continue
            uid = int(user_row["user_id"])
            # A spontaneous visual share is a possible action, not a requirement.
            # It is bounded by the same social decision and daily/hourly scheduler budget.
            if self.image_generator.available and decision.get("score", 0) >= .82 and float(state.get("desire_to_share", .3)) >= .65:
                scene = "a spontaneous NYRA self-portrait chosen by her current mood and relationship context"
                prompt = self.visual_identity.build_prompt(uid, uid, state, scene=scene)
                self.social.mark_response(uid, uid)
                action_id = self.outcomes.record_action(uid, "private_self_image", decision.get("reason", ""), "private", uid, scene)
                self.reflection.reflect(uid, f"NYRA spontaneously shared a self-image with user {uid}", .5)
                return {"type":"proactive_image", "chat_id":uid, "prompt":scene, "reason":decision.get("reason"), "score":decision.get("score",0.0), "action_id":action_id}
            try:
                text = self.private_autonomy.build(user_row, decision)
            except Exception:
                log.exception("private proactive generation failed")
                continue
            if not text:
                continue
            self.social.mark_response(uid, uid)
            self.memory.upsert("episodic", uid, "nyra_proactive_private", text[:500], .35, .65, "agent_proactive")
            action_id = self.outcomes.record_action(uid, "private_check_in", decision.get("reason", ""), "private", uid, text)
            self.reflection.reflect(uid, f"NYRA proactively contacted user {uid}; reason={decision.get('reason')}", .5)
            return {"type":"proactive_message", "chat_id":uid, "text":text,
                    "reason":decision.get("reason"), "score":decision.get("score",0.0),
                    "action_id":action_id, "kind":decision.get("kind")}

        groups = self.db.query("SELECT chat_id FROM social_groups ORDER BY activity DESC, conversation_speed DESC LIMIT 20")
        for row in groups:
            chat_id = int(row["chat_id"])
            state = self.state.get()
            goal = self.goals.best_for_group(chat_id)
            decision = self.social.proactive_decision(chat_id, state, self.outcomes, goal=goal)
            if decision.get("action") != "start":
                continue
            topic = decision.get("topic") or "the current conversation"
            recent = self.db.query("SELECT user_id,text FROM events WHERE chat_id=? ORDER BY id DESC LIMIT 8", (chat_id,))
            recent_text = "\n".join(f"{r['user_id']}: {r['text'] or ''}" for r in reversed(recent))

            # If a group goal exists, create/resume a bounded multi-step plan.
            if goal:
                plan = self.planner.ensure_plan(goal, chat_id, topic, recent_text)
                if plan:
                    step = self.plans.next_step(plan["id"])
                    if step and step["action_type"] in ("observe", "reflect"):
                        self.plans.complete_step(step["id"], f"Completed internal step: {step['objective']}")
                        return {"type":"plan_progress","chat_id":chat_id,"goal_id":goal["id"],"plan_id":plan["id"],"step_id":step["id"]}
                    if step and step["action_type"] == "send_message":
                        context = self.active_recall.find(chat_id, 0, topic, limit=5)
                        memory_text = "\n".join(str(r["content"]) for r in context) if context else "No relevant memory."
                        system = IDENTITY + "\nYou are executing one approved plan step for a Telegram group. Do not claim consciousness. Do not invent memories or facts. Output only the natural message, or SKIP if sending it would be inappropriate now. Keep it short."
                        prompt = (f"Goal: {goal['goal']}\n{self.planner.execution_context(plan, step, goal, topic)}\nRecent group messages:\n{recent_text}\nRelevant memories:\n{memory_text}")
                        try:
                            result=self.providers.generate([{"role":"user","content":prompt}],system,max_tokens=220)
                            text=result.text.strip()
                        except Exception:
                            log.exception("planned step generation failed")
                            self.plans.fail_step(step["id"], "provider failure")
                            continue
                        if not text or text.upper() == "SKIP":
                            return {"type":"plan_wait","chat_id":chat_id,"goal_id":goal["id"],"plan_id":plan["id"],"step_id":step["id"]}
                        text=re.sub(r'^(NYRA\s*:\s*)','',text,flags=re.I).strip()[:1000]
                        if not text:
                            self.plans.fail_step(step["id"], "empty generated message")
                            continue
                        self.social.mark_response(chat_id, 0)
                        self.memory.upsert('episodic',chat_id,'nyra_planned_message',text[:500],.35,.65,'agent_plan')
                        action_id=self.outcomes.record_action(chat_id,'planned_message','goal_plan',topic,0,text,goal_id=goal["id"])
                        self.plans.complete_step(step["id"], text)
                        self.reflection.reflect(chat_id,f"NYRA executed plan {plan['id']} step {step['step_no']}",.55)
                        return {"type":"proactive_message","chat_id":chat_id,"text":text,"reason":"goal_plan","score":decision.get("score",0.0),"goal_id":goal["id"],"plan_id":plan["id"],"step_id":step["id"],"action_id":action_id}

            # Existing non-goal proactive behavior remains intact.
            context = self.active_recall.find(chat_id, 0, topic, limit=5)
            memory_text = "\n".join(str(r["content"]) for r in context) if context else "No relevant memory."
            system = IDENTITY + "\nYou are deciding whether to naturally start a group message. Do not claim to be human or conscious. Do not invent memories. Keep it short, conversational, and directly connected to the supplied topic/context. Do not mention internal state or decision scores."
            prompt = (f"Goal: none\nTopic: {topic}\nRecent group messages:\n{recent_text}\nRelevant memories:\n{memory_text}\n"
                      "Write one natural Telegram message NYRA could send now. If there is no sensible thing to say, output exactly SKIP.")
            try:
                result=self.providers.generate([{"role":"user","content":prompt}],system,max_tokens=220)
                text=result.text.strip()
            except Exception:
                log.exception("proactive generation failed")
                continue
            if not text or text.upper() == "SKIP":
                continue
            text=re.sub(r'^(NYRA\s*:\s*)','',text,flags=re.I).strip()[:1000]
            if not text:
                continue
            self.social.mark_response(chat_id, 0)
            self.memory.upsert('episodic',chat_id,'nyra_proactive_message',text[:500],.35,.65,'agent_proactive')
            action_id=self.outcomes.record_action(chat_id,'proactive_message',decision.get('reason',''),topic,0,text)
            self.reflection.reflect(chat_id,f"NYRA proactively joined the conversation; reason={decision.get('reason')}",.5)
            return {'type':'proactive_message','chat_id':chat_id,'text':text,'reason':decision.get('reason'),'score':decision.get('score',0.0)}
        return {'type':'review_goals','count':len(goals)} if goals else None
