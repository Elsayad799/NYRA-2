from __future__ import annotations
import threading,time,logging
log=logging.getLogger("Scheduler")
class AutonomousScheduler:
    def __init__(self,agent,enabled=False,interval=60,budget_per_hour=6,callback=None):
        self.agent,self.enabled,self.interval,self.budget,self.callback=agent,enabled,max(15,interval),max(0,budget_per_hour),callback
        self._stop=threading.Event(); self._thread=None; self._history=[]
    def start(self):
        if not self.enabled or self._thread: return
        self._thread=threading.Thread(target=self._loop,name="nyra-autonomy",daemon=True); self._thread.start()
    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join(timeout=2)
    def _loop(self):
        while not self._stop.wait(self.interval):
            try:
                if not self._budget_ok(): continue
                action=self.agent.autonomous_tick()
                if action:
                    self._history.append(time.time())
                    if self.callback:
                        self.callback(action)
            except Exception: log.exception("autonomous tick failed")
    def _budget_ok(self):
        now=time.time(); self._history=[x for x in self._history if now-x<3600]
        return len(self._history)<self.budget
