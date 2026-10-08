"""Bounded in-memory history of editor settings, never audio files."""
class EditHistory:
    def __init__(self, limit=100):
        self.limit = limit
        self.current = None
        self.past = []
        self.future = []

    def reset(self, state):
        self.current = tuple(state)
        self.past.clear()
        self.future.clear()

    def record(self, state):
        state = tuple(state)
        if self.current is None:
            self.reset(state)
        elif state != self.current:
            self.past.append(self.current)
            self.past = self.past[-self.limit:]
            self.current = state
            self.future.clear()

    def undo(self):
        if self.past:
            self.future.append(self.current)
            self.current = self.past.pop()
        return self.current

    def redo(self):
        if self.future:
            self.past.append(self.current)
            self.current = self.future.pop()
        return self.current
