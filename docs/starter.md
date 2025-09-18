# 🚀 Скрипт старта (starter)

Параметр `starter` в конфигурации указывает на Python-файл, который выполняется при запуске системы.
Имя класса может быть любым, может быть описано несколько классов, как стартовый класс используется первый найденный. 

## Пример

```python
class AppStarter:

    def __init__(self):
        self.adaptor = None

    async def handle(self, msg):
        if msg.get('command') == 'start':
            await self.start()
        else:
            return False
        return True

    async def start(self):
        name = 'web_face'
        body = {
            'class_desc': {'requires_dist': 'simple_web_face', 'class': 'SimpleWebFace'},
            'name': name
        }
        await self.adaptor.ask(self.adaptor.get_msg('create_actor', body), 10)
        body = {'params': [{'name': 'http_port', 'value': 9090}]}
        await self.adaptor.ask(self.adaptor.get_msg('set_params', body, name))
        await self.adaptor.ask(self.adaptor.get_msg('start', None, name))
```


[Предыдущий](configuration.md) [Начало](index.md) [Следующий](distributed.md)