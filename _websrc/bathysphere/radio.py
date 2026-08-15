"""The radio: scripted traffic from the surface, typed out letter by letter.

Most of the game's story arrives through this thing. Lines trigger on depth
and on events; each prints at teletype speed with a burst of static, and the
deeper you go, the worse the link - the script says so itself.
"""
from __future__ import annotations

from settings import WORLD_H

TYPE_SPEED = 28.0                  # characters per second

# (trigger, payload, text). Triggers: "depth" (fraction), "event" (name).
SCRIPT = [
    ("event", "start",
     "БАЗА: Батисфера, связь принята. Погружение разрешаю. Держите нас в курсе."),
    ("event", "first_ping",
     "БАЗА: Эхо чистое. Работайте сонаром экономно — внизу вы не одни, по данным «Глагола»."),
    ("depth", 0.16,
     "БАЗА: Проходите первый горизонт. Стены сходятся, дальше идите по эху."),
    ("depth", 0.30,
     "БАЗА: «Глагол» замолчал три недели назад на глубине станции. Маяк ещё работает. Слушайте."),
    ("event", "first_box",
     "БАЗА: Есть контакт с самописцем! Поднимите его память — это всё, что от них осталось."),
    ("depth", 0.45,
     "БАЗА: Ниже этой отметки гидрофон ловил... песню. Не отвечайте на неё. Просто не отвечайте."),
    ("event", "mother_first_call",
     "БАЗА: ...это она. Заглушите двигатели, если близко. Она идёт на шум и на сонар."),
    ("depth", 0.62,
     "БАЗА: Св-зь ух-дшается. Повторяю: маяк ст-нции слышен на гидрофоне. Ищите ритм... пять секунд."),
    ("event", "hull_low",
     "БАЗА: Корпус на пределе! Стравите скорость, никаких столкновений."),
    ("event", "oxygen_low",
     "БАЗА: Кислород меньше четверти. Решайте: вниз до станции или всплытие. Времени на оба нет."),
    ("depth", 0.85,
     "БАЗА: ...почти н- слыш-м вас. Огонёк на дне — это она, станция. Дотянитесь."),
    ("event", "docked",
     "«ГЛАГОЛ»: Шлюз принят. Давление выровнено. ...С возвращением в живой мир, Батисфера."),
]


class Radio:
    def __init__(self):
        self.fired = set()
        self.queue = []
        self.current = None
        self.shown = 0.0
        self.hold = 0.0

    # ------------------------------------------------------------ triggers
    def trigger_event(self, name):
        for i, (kind, payload, text) in enumerate(SCRIPT):
            if kind == "event" and payload == name and i not in self.fired:
                self.fired.add(i)
                self.queue.append(text)
                return True
        return False

    def trigger_depth(self, y):
        frac = y / WORLD_H
        fired_any = False
        for i, (kind, payload, text) in enumerate(SCRIPT):
            if kind == "depth" and frac >= payload and i not in self.fired:
                self.fired.add(i)
                self.queue.append(text)
                fired_any = True
        return fired_any

    # -------------------------------------------------------------- update
    def update(self, dt):
        started = False
        if self.current is None and self.queue:
            self.current = self.queue.pop(0)
            self.shown = 0.0
            self.hold = 0.0
            started = True                      # caller plays the static
        if self.current is not None:
            if self.shown < len(self.current):
                self.shown += TYPE_SPEED * dt
            else:
                self.hold += dt
                if self.hold > 4.0:
                    self.current = None
        return started

    @property
    def line(self):
        if self.current is None:
            return None
        count = int(self.shown)
        cursor = "_" if count < len(self.current) else ""
        return self.current[:count] + cursor
