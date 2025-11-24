import os
from aiohttp import web
import mimetypes
from pathlib import Path


class FileBrowserHandler:

    def __init__(self, browser_base_dir=None):
        self.base_directory = browser_base_dir or os.getcwd()
        self.base_path = Path(self.base_directory).resolve()

        # Добавляем MIME-типы для текстовых файлов
        mimetypes.add_type('text/plain', '.log')
        mimetypes.add_type('text/plain', '.txt')
        mimetypes.add_type('text/markdown', '.md')
        mimetypes.add_type('application/json', '.json')
        mimetypes.add_type('text/x-python', '.py')
        mimetypes.add_type('text/html', '.html')
        mimetypes.add_type('text/css', '.css')
        mimetypes.add_type('application/javascript', '.js')
        mimetypes.add_type('text/xml', '.xml')
        mimetypes.add_type('text/csv', '.csv')
        mimetypes.add_type('text/plain', '')

    async def handle_browse(self, request):
        """Хендлер для просмотра содержимого директорий"""
        try:
            # Получаем путь из URL параметра или используем корневую директорию
            relative_path = request.query.get('path', '')
            if relative_path == '.':
                relative_path = ''
            full_path = self.base_path / relative_path

            # Проверяем безопасность пути
            if not self._is_safe_path(full_path):
                return web.Response(text="Доступ запрещен", status=403)

            # Проверяем существование пути
            if not full_path.exists():
                return web.Response(text="Путь не существует", status=404)

            # Если это файл - отдаем его содержимое
            if full_path.is_file():
                return await self._serve_file(full_path, request)

            # Если это директория - показываем содержимое
            return await self._list_directory(full_path, relative_path)

        except Exception as e:
            return web.Response(text=f"Ошибка: {str(e)}", status=500)

    def _is_safe_path(self, path):
        """Проверяет, что путь находится внутри базовой директории"""
        try:
            path.resolve().relative_to(self.base_path)
            return True
        except ValueError:
            return False

    async def _serve_file(self, file_path, request):
        mime_type = self._get_mime_type_by_extension(file_path, file_path.suffix)
        is_text_file = self._is_text_file(file_path, mime_type)
        download = request.query.get('download')
        if download is not None:
            return await self._download_file(file_path, mime_type)
        if is_text_file and file_path.stat().st_size <= 5 * 1024 * 1024:  # 5MB
            return await self._serve_text_file(file_path, mime_type)
        else:
            return await self._download_file(file_path, mime_type)

    def _is_text_by_content(self, item_path):
        try:
            with open(item_path, 'rb') as f:
                sample = f.read(1024)
            if not sample:
                return True
            if b'\x00' in sample:
                return False
            try:
                sample.decode('utf-8')
                return True
            except UnicodeDecodeError:
                return False
        except IOError:
            return False

    def _get_mime_type_by_extension(self, item_path, extension):
        """Определяет MIME-тип по расширению файла"""
        text_extensions = {
            '.log': 'text/plain',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.py': 'text/x-python',
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.xml': 'text/xml',
            '.csv': 'text/csv',
            '.conf': 'text/plain',
            '.cfg': 'text/plain',
            '.ini': 'text/plain',
            '.sh': 'text/x-shellscript',
            '.bat': 'text/plain',
            '.ps1': 'text/plain',
        }
        text_extension = text_extensions.get(extension.lower())
        if text_extension:
            return text_extension
        else:
            if self._is_text_by_content(item_path):
                return 'text/plain'
            else:
                return 'application/octet-stream'

    def _is_text_file(self, file_path, mime_type):
        """Проверяет, является ли файл текстовым"""
        text_mime_types = [
            'text/plain', 'text/html', 'text/css', 'application/javascript',
            'text/x-python', 'application/json', 'text/markdown', 'text/xml',
            'text/csv', 'application/xml', 'text/x-shellscript'
        ]

        if mime_type in text_mime_types:
            return True

        # Дополнительная проверка по расширению
        text_extensions = {'.log', '.txt', '.md', '.py', '.html', '.css', '.js',
                           '.json', '.xml', '.csv', '.conf', '.cfg', '.ini', '.sh', '.bat', '.ps1'}
        return file_path.suffix.lower() in text_extensions

    async def _serve_text_file(self, file_path, mime_type):
        """Показывает содержимое текстового файла в браузере"""
        try:
            # Пытаемся прочитать файл как текст
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, UnicodeError):
            try:
                # Пробуем другие кодировки
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception:
                # Если не получается прочитать как текст - скачиваем
                return await self._download_file(file_path, mime_type)

        # Создаем HTML страницу для просмотра файла
        html = self._generate_file_view_html(file_path, content)
        return web.Response(text=html, content_type='text/html')

    def _generate_file_view_html(self, file_path, content):
        """Генерирует HTML страницу для просмотра файла"""
        escaped_content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Просмотр: {file_path.name}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #ddd; }}
                .actions {{ margin: 10px 0; }}
                .btn {{ 
                    display: inline-block; 
                    padding: 8px 16px; 
                    margin-right: 10px;
                    background: #007bff; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px;
                }}
                .btn:hover {{ background: #0056b3; }}
                .btn-download {{ background: #28a745; }}
                .btn-download:hover {{ background: #1e7e34; }}
                .content {{ 
                    background: #f8f9fa; 
                    padding: 15px; 
                    border-radius: 4px; 
                    border: 1px solid #dee2e6;
                    white-space: pre-wrap;
                    font-family: 'Courier New', monospace;
                    max-height: 70vh;
                    overflow: auto;
                }}
                .file-info {{ color: #6c757d; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Просмотр файла: {file_path.name}</h1>
                <div class="file-info">
                    Размер: {self._format_size(file_path.stat().st_size)} | 
                    Путь: {file_path}
                </div>
                <div class="actions">
                    <a href="/browse?path={file_path.parent.relative_to(self.base_path)}" class="btn">← Назад</a>
                    <a href="/browse?path={file_path.relative_to(self.base_path)}&download=1" class="btn btn-download">📥 Скачать</a>
                </div>
            </div>
            <div class="content">{escaped_content}</div>
        </body>
        </html>
        """
        return html

    async def _download_file(self, file_path, mime_type):
        """Скачивает файл"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            return web.Response(
                body=content,
                content_type=mime_type,
                headers={
                    'Content-Disposition': f'attachment; filename="{file_path.name}"'
                }
            )
        except Exception as e:
            return web.Response(text=f"Ошибка чтения файла: {str(e)}", status=500)

    async def _list_directory(self, dir_path, relative_path):
        """Показывает содержимое директории"""
        items = []

        # Добавляем ссылку на родительскую директорию (если не корневая)
        if relative_path:
            parent_path = str(Path(relative_path).parent)
            items.append({
                'name': '..',
                'path': parent_path,
                'type': 'directory',
                'size': None,
                'is_symlink': False
            })

        # Собираем информацию о файлах и папках
        for item in sorted(dir_path.iterdir()):
            try:
                is_symlink = item.is_symlink()

                # Определяем тип элемента (учитывая символьные ссылки)
                if item.is_dir() and not is_symlink:
                    item_type = 'directory'
                elif item.is_file() and not is_symlink:
                    item_type = 'file'
                elif is_symlink:
                    # Для символьных ссылок определяем тип целевого объекта
                    try:
                        target = item.resolve()
                        if target.exists():
                            if target.is_dir():
                                item_type = 'symlink_directory'
                            else:
                                item_type = 'symlink_file'
                        else:
                            item_type = 'symlink_broken'
                    except:
                        item_type = 'symlink_broken'
                else:
                    item_type = 'unknown'

                item_info = {
                    'name': item.name,
                    'path': str(Path(relative_path) / item.name) if relative_path else item.name,
                    'type': item_type,
                    'is_symlink': is_symlink,
                }

                if item_type in ['file', 'symlink_file']:
                    try:
                        item_info['size'] = item.stat().st_size
                        item_info['modified'] = item.stat().st_mtime
                        # Добавляем информацию о типе файла
                        item_info['is_text'] = (
                            self._is_text_file(item, self._get_mime_type_by_extension(item.absolute(), item.suffix)))
                    except OSError:
                        item_info['size'] = 0
                        item_info['modified'] = 0
                        item_info['is_text'] = False
                else:
                    item_info['size'] = None
                    try:
                        item_info['modified'] = item.stat().st_mtime
                    except OSError:
                        item_info['modified'] = 0
                    item_info['is_text'] = False

                items.append(item_info)
            except OSError:
                continue

        # Генерируем HTML страницу
        html = self._generate_directory_html(items, relative_path)
        return web.Response(text=html, content_type='text/html')

    def _generate_directory_html(self, items, current_path):
        """Генерирует HTML страницу с содержимым директории"""
        title = f"Содержимое: /{current_path}" if current_path else "Корневая директория"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:hover {{ background-color: #f5f5f5; }}
                a {{ text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .file-size {{ text-align: right; }}
                .directory {{ color: #28a745; }}
                .file {{ color: #6c757d; }}
                .text-file {{ color: #007bff; }}
                .symlink {{ color: #ff9800; }}
                .symlink-broken {{ color: #dc3545; }}
                .icon {{ margin-right: 5px; }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <table>
                <thead>
                    <tr>
                        <th>Имя</th>
                        <th>Тип</th>
                        <th class="file-size">Размер</th>
                        <th>Дата изменения</th>
                    </tr>
                </thead>
                <tbody>
        """

        for item in items:
            # Определяем иконку и класс в зависимости от типа элемента
            if item['type'] == 'directory':
                icon = "📁"
                type_class = "directory"
                link = f'/browse?path={item["path"]}'
                type_text = "Папка"
            elif item['type'] == 'symlink_directory':
                icon = "📂🔗"
                type_class = "symlink"
                link = f'/browse?path={item["path"]}'
                type_text = "Симв. ссылка (папка)"
            elif item['type'] == 'symlink_file':
                icon = "📄🔗"
                type_class = "symlink"
                link = f'/browse?path={item["path"]}'
                type_text = "Симв. ссылка (файл)"
            elif item['type'] == 'symlink_broken':
                icon = "❌🔗"
                type_class = "symlink-broken"
                link = f'/browse?path={item["path"]}'
                type_text = "Битая симв. ссылка"
            else:
                if item.get('is_text', False):
                    icon = "📄"
                    type_class = "text-file"
                else:
                    icon = "💾"
                    type_class = "file"
                link = f'/browse?path={item["path"]}'
                type_text = "Файл"

            size = self._format_size(item['size']) if item['size'] is not None else "-"
            modified = self._format_timestamp(item['modified']) if 'modified' in item and item['modified'] else "-"

            html += f"""
                    <tr>
                        <td>
                            <span class="icon">{icon}</span>
                            <a href="{link}" class="{type_class}">{item['name']}</a>
                        </td>
                        <td>{type_text}</td>
                        <td class="file-size">{size}</td>
                        <td>{modified}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </body>
        </html>
        """

        return html

    def _format_size(self, size_bytes):
        """Форматирует размер файла в читаемом виде"""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f} {size_names[i]}"

    def _format_timestamp(self, timestamp):
        """Форматирует timestamp в читаемую дату"""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

'''
import os
from aiohttp import web
import mimetypes
from pathlib import Path


class FileBrowserHandler:

    def __init__(self, browser_base_dir=None):
        self.base_directory = browser_base_dir or os.getcwd()
        self.base_path = Path(self.base_directory).resolve()

        # Добавляем MIME-типы для текстовых файлов
        mimetypes.add_type('text/plain', '.log')
        mimetypes.add_type('text/plain', '.txt')
        mimetypes.add_type('text/markdown', '.md')
        mimetypes.add_type('application/json', '.json')
        mimetypes.add_type('text/x-python', '.py')
        mimetypes.add_type('text/html', '.html')
        mimetypes.add_type('text/css', '.css')
        mimetypes.add_type('application/javascript', '.js')
        mimetypes.add_type('text/xml', '.xml')
        mimetypes.add_type('text/csv', '.csv')
        mimetypes.add_type('text/plain', '')

    async def handle_browse(self, request):
        """Хендлер для просмотра содержимого директорий"""
        try:
            # Получаем путь из URL параметра или используем корневую директорию
            relative_path = request.query.get('path', '')
            if relative_path == '.':
                relative_path = ''
            full_path = self.base_path / relative_path

            # Проверяем безопасность пути
            if not self._is_safe_path(full_path):
                return web.Response(text="Доступ запрещен", status=403)

            # Проверяем существование пути
            if not full_path.exists():
                return web.Response(text="Путь не существует", status=404)

            # Если это файл - отдаем его содержимое
            if full_path.is_file():
                return await self._serve_file(full_path, request)

            # Если это директория - показываем содержимое
            return await self._list_directory(full_path, relative_path)

        except Exception as e:
            return web.Response(text=f"Ошибка: {str(e)}", status=500)

    def _is_safe_path(self, path):
        """Проверяет, что путь находится внутри базовой директории"""
        try:
            path.resolve().relative_to(self.base_path)
            return True
        except ValueError:
            return False

    async def _serve_file(self, file_path, request):
        mime_type = self._get_mime_type_by_extension(file_path, file_path.suffix)
        is_text_file = self._is_text_file(file_path, mime_type)
        download = request.query.get('download')
        if download is not None:
            return await self._download_file(file_path, mime_type)
        if is_text_file and file_path.stat().st_size <= 5 * 1024 * 1024:  # 5MB
            return await self._serve_text_file(file_path, mime_type)
        else:
            return await self._download_file(file_path, mime_type)

    def _is_text_by_content(self, item_path):
        try:
            with open(item_path, 'rb') as f:
                sample = f.read(1024)
            if not sample:
                return True
            if b'\x00' in sample:
                return False
            try:
                sample.decode('utf-8')
                return True
            except UnicodeDecodeError:
                return False
        except IOError:
            return False

    def _get_mime_type_by_extension(self, item_path, extension):
        """Определяет MIME-тип по расширению файла"""
        text_extensions = {
            '.log': 'text/plain',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.py': 'text/x-python',
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.xml': 'text/xml',
            '.csv': 'text/csv',
            '.conf': 'text/plain',
            '.cfg': 'text/plain',
            '.ini': 'text/plain',
            '.sh': 'text/x-shellscript',
            '.bat': 'text/plain',
            '.ps1': 'text/plain',
        }
        text_extension = text_extensions.get(extension.lower())
        if text_extension:
            return text_extension
        else:
            if self._is_text_by_content(item_path):
                return 'text/plain'
            else:
                return 'application/octet-stream'

    def _is_text_file(self, file_path, mime_type):
        """Проверяет, является ли файл текстовым"""
        text_mime_types = [
            'text/plain', 'text/html', 'text/css', 'application/javascript',
            'text/x-python', 'application/json', 'text/markdown', 'text/xml',
            'text/csv', 'application/xml', 'text/x-shellscript'
        ]

        if mime_type in text_mime_types:
            return True

        # Дополнительная проверка по расширению
        text_extensions = {'.log', '.txt', '.md', '.py', '.html', '.css', '.js',
                           '.json', '.xml', '.csv', '.conf', '.cfg', '.ini', '.sh', '.bat', '.ps1'}
        return file_path.suffix.lower() in text_extensions

    async def _serve_text_file(self, file_path, mime_type):
        """Показывает содержимое текстового файла в браузере"""
        try:
            # Пытаемся прочитать файл как текст
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, UnicodeError):
            try:
                # Пробуем другие кодировки
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception:
                # Если не получается прочитать как текст - скачиваем
                return await self._download_file(file_path, mime_type)

        # Создаем HTML страницу для просмотра файла
        html = self._generate_file_view_html(file_path, content)
        return web.Response(text=html, content_type='text/html')

    def _generate_file_view_html(self, file_path, content):
        """Генерирует HTML страницу для просмотра файла"""
        escaped_content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Просмотр: {file_path.name}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #ddd; }}
                .actions {{ margin: 10px 0; }}
                .btn {{ 
                    display: inline-block; 
                    padding: 8px 16px; 
                    margin-right: 10px;
                    background: #007bff; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 4px;
                }}
                .btn:hover {{ background: #0056b3; }}
                .btn-download {{ background: #28a745; }}
                .btn-download:hover {{ background: #1e7e34; }}
                .content {{ 
                    background: #f8f9fa; 
                    padding: 15px; 
                    border-radius: 4px; 
                    border: 1px solid #dee2e6;
                    white-space: pre-wrap;
                    font-family: 'Courier New', monospace;
                    max-height: 70vh;
                    overflow: auto;
                }}
                .file-info {{ color: #6c757d; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Просмотр файла: {file_path.name}</h1>
                <div class="file-info">
                    Размер: {self._format_size(file_path.stat().st_size)} | 
                    Путь: {file_path}
                </div>
                <div class="actions">
                    <a href="/browse?path={file_path.parent.relative_to(self.base_path)}" class="btn">← Назад</a>
                    <a href="/browse?path={file_path.relative_to(self.base_path)}&download=1" class="btn btn-download">📥 Скачать</a>
                </div>
            </div>
            <div class="content">{escaped_content}</div>
        </body>
        </html>
        """
        return html

    async def _download_file(self, file_path, mime_type):
        """Скачивает файл"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            return web.Response(
                body=content,
                content_type=mime_type,
                headers={
                    'Content-Disposition': f'attachment; filename="{file_path.name}"'
                }
            )
        except Exception as e:
            return web.Response(text=f"Ошибка чтения файла: {str(e)}", status=500)

    async def _list_directory(self, dir_path, relative_path):
        """Показывает содержимое директории"""
        items = []

        # Добавляем ссылку на родительскую директорию (если не корневая)
        if relative_path:
            parent_path = str(Path(relative_path).parent)
            items.append({
                'name': '..',
                'path': parent_path,
                'type': 'directory',
                'size': None
            })

        # Собираем информацию о файлах и папках
        for item in sorted(dir_path.iterdir()):
            try:
                item_info = {
                    'name': item.name,
                    'path': str(Path(relative_path) / item.name) if relative_path else item.name,
                    'type': 'directory' if item.is_dir() else 'file',
                }

                if item.is_file():
                    item_info['size'] = item.stat().st_size
                    item_info['modified'] = item.stat().st_mtime
                    # Добавляем информацию о типе файла
                    item_info['is_text'] = (
                        self._is_text_file(item, self._get_mime_type_by_extension(item.absolute(), item.suffix)))
                else:
                    item_info['size'] = None
                    item_info['modified'] = item.stat().st_mtime
                    item_info['is_text'] = False

                items.append(item_info)
            except OSError:
                continue

        # Генерируем HTML страницу
        html = self._generate_directory_html(items, relative_path)
        return web.Response(text=html, content_type='text/html')

    def _generate_directory_html(self, items, current_path):
        """Генерирует HTML страницу с содержимым директории"""
        title = f"Содержимое: /{current_path}" if current_path else "Корневая директория"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:hover {{ background-color: #f5f5f5; }}
                a {{ text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .file-size {{ text-align: right; }}
                .directory {{ color: #28a745; }}
                .file {{ color: #6c757d; }}
                .text-file {{ color: #007bff; }}
                .icon {{ margin-right: 5px; }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <table>
                <thead>
                    <tr>
                        <th>Имя</th>
                        <th>Тип</th>
                        <th class="file-size">Размер</th>
                        <th>Дата изменения</th>
                    </tr>
                </thead>
                <tbody>
        """

        for item in items:
            if item['type'] == 'directory':
                icon = "📁"
                type_class = "directory"
                link = f'/browse?path={item["path"]}'
            else:
                if item.get('is_text', False):
                    icon = "📄"
                    type_class = "text-file"
                else:
                    icon = "💾"
                    type_class = "file"
                link = f'/browse?path={item["path"]}'

            size = self._format_size(item['size']) if item['size'] is not None else "-"
            modified = self._format_timestamp(item['modified']) if 'modified' in item else "-"

            html += f"""
                    <tr>
                        <td>
                            <span class="icon">{icon}</span>
                            <a href="{link}" class="{type_class}">{item['name']}</a>
                        </td>
                        <td>{item['type']}</td>
                        <td class="file-size">{size}</td>
                        <td>{modified}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </body>
        </html>
        """

        return html

    def _format_size(self, size_bytes):
        """Форматирует размер файла в читаемом виде"""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f} {size_names[i]}"

    def _format_timestamp(self, timestamp):
        """Форматирует timestamp в читаемую дату"""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
'''
