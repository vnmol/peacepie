# ⚙️ Конфигурация системы

Файл конфигурации передаётся как аргумент при запуске.

Пример `config.cfg`:

```ini
system_name=king
host_name=first
process_name=main
intra_role=master
intra_host=localhost
intra_port=5998
inter_port=5999
developing_mode=True
log_config=../config/log.cfg
safe_config=../config/safe.cfg
extra-index-url=http://localhost:9000
package_dir=../packages
plugin_dir=../plugins
log_dir=../logs
separate_log_per_process=True
starter=../config/app_starter.py
```

## Ключевые параметры

ПАРАМЕТР        | НАЗНАЧЕНИЕ                                               |
----------------|----------------------------------------------------------|
intra_role      | master или slave (только один master)                    |
intra_port      | Порт для связи внутри системы (между процессами/хостами) |
inter_port      | Порт для связи с другими системами                       |
extra-index-url | Альтернативный источник пакетов                          |
starter         | Скрипт инициализации                                     |



[Предыдущий](messages.md) [Начало](index.md) [Следующий](starter.md)