"""Coloured message log with repeat stacking."""
import textwrap

from settings import MSG_INFO


class Message:
    def __init__(self, text, color):
        self.plain_text = text
        self.color = color
        self.count = 1

    @property
    def full_text(self):
        if self.count > 1:
            return "{} (x{})".format(self.plain_text, self.count)
        return self.plain_text


class MessageLog:
    def __init__(self):
        self.messages = []

    def add(self, text, color=MSG_INFO, stack=True):
        if stack and self.messages and self.messages[-1].plain_text == text:
            self.messages[-1].count += 1
        else:
            self.messages.append(Message(text, color))
        # the log is unbounded in-game but we cap it so saves stay small
        if len(self.messages) > 500:
            del self.messages[:100]

    def wrapped(self, width):
        """Yield (text, color) newest-first, wrapped to `width` characters."""
        for message in reversed(self.messages):
            for line in reversed(textwrap.wrap(message.full_text, width)):
                yield line, message.color

    # ------------------------------------------------------------ save/load
    def to_dict(self):
        return [{"t": m.plain_text, "c": list(m.color), "n": m.count}
                for m in self.messages]

    @classmethod
    def from_dict(cls, data):
        log = cls()
        for entry in data:
            message = Message(entry["t"], tuple(entry["c"]))
            message.count = entry["n"]
            log.messages.append(message)
        return log
