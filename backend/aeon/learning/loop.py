import asyncio

class MockTrainer:
    def __init__(self):
        self.threshold = 0.75
    def update_threshold(self, value):
        self.threshold += value

class MockDreamState:
    def __init__(self):
        self.is_active = False
        self.events_replayed = 0
        self.before_latency_ms = 0.0
        self.after_latency_ms = 0.0
        self.last_run_ts = None
        self.last_result = "never_run"
    async def optimize(self):
        pass

class LearningLoop:
    def __init__(self, memory, qnn, model_dir):
        self.trainer = MockTrainer()
        self.false_alarms_flagged = 0
        self.training_state = "idle"
        self.last_train_ts = None
        self.adaptation_progress_pct = 0
        self.dream_state = MockDreamState()

    def attach_bus(self, ws_bus):
        pass

    def attach_graph(self, graph):
        pass

    async def run(self):
        while True:
            await asyncio.sleep(3600)
