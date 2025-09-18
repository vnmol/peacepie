# 🧱 Акторы: как писать поведение

Актор — это класс, реализующий поведение в изолированном контексте.

## Обязательные элементы

* adaptor — ссылка на API фреймворка.
* handle(msg) — асинхронный метод, обрабатывающий входящие сообщения.

```python
class MyActor:

    def __init__(self):
        self.adaptor = None  # будет установлен фреймворком

    async def handle(self, msg): # асинхронный метод, обрабатывающий входящие сообщения.
        command = msg.get('command')
        if command == 'command_0':
            await self.command_0()
        elif command == 'command_1':
            await self.command_1()
        # ...
        else:
           return False  # если команда не распознана
        return True
```

Реальный минимальный пример:

```python
class Dummy:
    
    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        if msg.get('command') == 'start':
            await self.start(msg.get('sender'))
        else:
            return False
        return True

    async def start(self, recipient):
        if recipient:
            response = self.adaptor.get_msg('started', None, recipient)
            await self.adaptor.send(response)
```

Актор типа Dummy при получении сообщения, содержащего команду 'start', извлекает отправителя и, если тот не равен None, отвечает отправителю командой 'started'.


[Предыдущий](installation.md) [Начало](index.md) [Следующий](messages.md)