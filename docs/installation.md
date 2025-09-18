# 💾 Установка и запуск

## Установка

```bash
pip install peacepie
```

## Запуск системы

Создайте основной скрипт запуска, например, main.py:

```Python
import asyncio
import multiprocessing
import sys
from peacepie import PeaceSystem
# import uvloop
# import ujson


multiprocessing.set_start_method('spawn', force=True)


async def main():
    # asyncio.set_event_loop_policy(uvloop.EventLoopPolicy()) # Для использования "uvloop"
    param = sys.argv[1] if len(sys.argv) > 1 else None
    pp = PeaceSystem(param) # pp = PeaceSystem(param, json_package=ujson) Для использования "ujson"
    await pp.start()
    await pp.task


if __name__ == '__main__':
    asyncio.run(main())
```

Для ознакомительных целей первый раз скрипт можно запускать без параметров:

```bash
python main.py
```

В случае запуска без параметров, создается необходимое окружение (папки config, logs, packages), 
устанавливается пакет **peacepie_example** из репозитория Test PyPI с зависимостями. 
Из указанного пакета импортируется и создается актор типа SimpleWebFace, который обеспечивает
простейший веб-интерфейс к системе, доступный по адресу http://localhost:9090/.
При повторных запусках желательно указывать параметр, ссылающийся на конфигурационный файл,
чтобы избежать повторных действий по созданию окружения и установке необходимых пакетов.
Если после первоначального запуска скрипта без параметров ничего не менялось, то необходимый
конфигурационный файл должен находиться по адресу **"./config/peacepie.cfg"**, а запуск должен
выглядеть так:

```bash
python main.py ./config/peacepie.cfg
```

[Начало](index.md) [Следующий](actors.md)