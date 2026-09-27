from __future__ import annotations
import time, logging
from dotenv import load_dotenv
from src.core.config import Settings, BASE_DIR
from src.core.logging import setup_logging
from src.database.db import Database
from src.memory.store import MemoryStore
from src.personality.state import StateStore
from src.providers.manager import ProviderManager
from src.decisions.engagement import EngagementDecision
from src.agent.agent import NYRAAgent
from src.telegram.adapter import TelegramAdapter
from src.tools.registry import ToolRegistry
from src.tools.builtin import register_builtins
from src.agent.scheduler import AutonomousScheduler

log=logging.getLogger('NYRA')

def build_and_run(settings):
    db=Database(settings.database_url)
    memory=MemoryStore(db,settings.max_memories)
    providers=ProviderManager(settings)
    state=StateStore(db)
    tools=ToolRegistry(); register_builtins(tools)
    agent=NYRAAgent(db,memory,providers,state,EngagementDecision(settings),settings,tools)
    scheduler=AutonomousScheduler(agent,settings.autonomous_mode,settings.autonomous_interval,settings.autonomous_budget_per_hour)
    TelegramAdapter(settings,agent,scheduler).run()
    db.close()

def main():
    load_dotenv(BASE_DIR / '.env')
    settings=Settings.load(); setup_logging(settings.debug)
    print('NYRA AI starting — Telegram token only; supplied AI sources are internal.')
    delay=3
    while True:
        try:
            build_and_run(settings)
            delay=3
            time.sleep(1)
        except KeyboardInterrupt:
            print('NYRA stopped by user.')
            break
        except Exception as exc:
            log.exception('NYRA main loop crashed; persistent state is retained. Restarting in %ss',delay)
            time.sleep(delay)
            delay=min(delay*2,60)

if __name__=='__main__': main()
