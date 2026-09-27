from __future__ import annotations

def describe_social(decision: dict, state: dict, relationship: dict, group: dict) -> str:
    return (
        f"Social decision={decision.get('action')}; target={decision.get('target')}; reason={decision.get('reason')}; "
        f"score={decision.get('score',0):.2f}. Mood={state.get('mood')}; energy={state.get('energy',0):.2f}; "
        f"social_need={state.get('social_need',0):.2f}; familiarity={relationship.get('familiarity',0):.2f}; "
        f"group_activity={group.get('activity',0):.2f}; conversation_speed={group.get('conversation_speed',0):.2f}."
    )
