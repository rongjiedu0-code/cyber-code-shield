"""Loopback-only web UI with authenticated same-origin mutation endpoints."""
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import tempfile
import threading
from urllib.parse import urlsplit, parse_qs
import webbrowser
from .service import ToolboxService


def create_server(service=None, port=0):
    service = service or ToolboxService()
    token = secrets.token_urlsafe(32)
    lock = threading.Lock()
    page = (Path(__file__).with_name('web_ui.html')).read_text(encoding='utf-8').replace('__SESSION_TOKEN__', token)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, body, mime='application/json; charset=utf-8', attachment=''):
            if not isinstance(body, bytes):
                body = (json.dumps(body, ensure_ascii=False) if mime.startswith('application/json') else str(body)).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
            if attachment:
                self.send_header('Content-Disposition', 'attachment; filename="results.' + attachment + '"')
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def authenticated(self):
            supplied = self.headers.get('X-Session-Token', '')
            if not supplied:
                supplied = parse_qs(urlsplit(self.path).query).get('token', [''])[0]
            origin = self.headers.get('Origin')
            expected = f'http://127.0.0.1:{self.server.server_port}'
            return self.valid_host() and secrets.compare_digest(supplied, token) and (origin is None or origin == expected)

        def do_GET(self):
            path = urlsplit(self.path).path
            if not self.valid_host():
                return self.reply(403, {'error': '请求来源不正确'})
            if path == '/':
                return self.reply(200, page, 'text/html; charset=utf-8')
            if not self.authenticated():
                return self.reply(403, {'error': '会话无效，请使用本机窗口打开'})
            if path == '/api/state':
                return self.reply(200, service.state())
            if path == '/api/export':
                kind = parse_qs(urlsplit(self.path).query).get('format', ['csv'])[0]
                if kind not in {'csv', 'xlsx'}:
                    return self.reply(400, {'error': '导出格式不正确'})
                try:
                    with tempfile.TemporaryDirectory(prefix='cn-export-') as temporary:
                        output = Path(temporary) / ('results.'+kind)
                        with lock:
                            service.export(output)
                        return self.reply(200, output.read_bytes(), 'application/octet-stream', kind)
                except (ValueError, OSError) as error:
                    return self.reply(400, {'error': str(error)})
            return self.reply(404, {'error': '页面不存在'})

        def do_POST(self):
            if not self.authenticated():
                # Drain small rejected bodies so Windows does not reset the socket
                # before the browser can read the explicit 403 response.
                try:
                    rejected_length = int(self.headers.get('Content-Length', '0'))
                    if 0 < rejected_length <= 65536:
                        self.rfile.read(rejected_length)
                except ValueError:
                    pass
                return self.reply(403, {'error': '会话无效或请求来源不正确'})
            if not lock.acquire(blocking=False):
                return self.reply(409, {'error': '正在处理另一项任务，请稍后再试'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 60*1024*1024:
                    return self.reply(413, {'error': '上传内容须在 60MB 内'})
                body = self.rfile.read(length)
                if self.path == '/api/activate':
                    service.guard.activate(json.loads(body)['key'])
                    return self.reply(200, service.state())
                if self.path != '/api/run':
                    return self.reply(404, {'error': '功能不存在'})
                content_type = self.headers.get('Content-Type', '')
                if not content_type.startswith('multipart/form-data;'):
                    return self.reply(400, {'error': '请使用页面中的文件表单'})
                message = BytesParser(policy=default).parsebytes(('Content-Type: '+content_type+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+body)
                with tempfile.TemporaryDirectory(prefix='cn-upload-') as temporary:
                    options, uploaded = {}, []
                    for part in message.iter_parts():
                        name = part.get_param('name', header='content-disposition')
                        filename = part.get_filename()
                        raw = part.get_payload(decode=True) or b''
                        if filename:
                            suffix = Path(filename).suffix.lower()
                            if name == 'codes':
                                uploaded.append(dict(name=Path(filename).name, content=raw.decode('utf-8-sig')))
                            else:
                                if suffix not in {'.csv', '.xlsx', '.tsv', '.txt'}:
                                    raise ValueError('请上传 CSV / XLSX 表格')
                                target = Path(temporary) / (secrets.token_hex(8)+suffix)
                                target.write_bytes(raw)
                                options[name] = str(target)
                        else:
                            options[name] = raw.decode('utf-8')
                    action = options.pop('action', '')
                    if uploaded:
                        options['files'] = uploaded
                    if 'mapping' in options:
                        options['mapping'] = json.loads(options['mapping'])
                    service.run(action, **options)
                    return self.reply(200, service.state())
            except Exception as error:
                return self.reply(400, {'error': str(error)})
            finally:
                lock.release()

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.timeout = 1
    server.service = service
    server.session_token = token
    return server


def main():
    server = create_server()
    url = f'http://127.0.0.1:{server.server_port}'
    threading.Thread(target=server.serve_forever,daemon=True).start()
    webbrowser.open(url)
    import tkinter as tk
    from tkinter import ttk
    window = tk.Tk()
    window.title('本地网页服务正在运行')
    ttk.Label(window,text='浏览器模式已打开。关闭此小窗口即可结束本地服务。',padding=20).pack()
    ttk.Button(window,text='重新打开网页',command=lambda:webbrowser.open(url)).pack(pady=10)
    def close():
        server.shutdown()
        server.server_close()
        window.destroy()
    window.protocol('WM_DELETE_WINDOW',close)
    window.mainloop()
