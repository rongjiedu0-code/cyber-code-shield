from pathlib import Path
from .license_guard import LicenseGuard
from .tables import read_table, write_rows
from .reconcile import reconcile_files
from .radar import collect_community, analyze_signals
from .trends import collect_trends, analyze_products
from .security import scan_path, scan_code


class ToolboxService:
    def __init__(self, guard=None):
        self.guard = guard or LicenseGuard()
        self.rows = []
        self.last_action = ''

    def run(self, action, **options):
        if action == 'reconcile':
            rows = reconcile_files(options['orders'], options['payments'], options.get('mapping'))
        elif action == 'radar':
            rows = collect_community(int(options.get('limit', 30)), options.get('keyword', ''))
        elif action == 'radar_file':
            rows = analyze_signals(read_table(options['path']), options.get('keyword', ''))
        elif action == 'trends':
            rows = collect_trends(int(options.get('limit', 30)), options.get('keyword', ''))
        elif action == 'products':
            rows = analyze_products(read_table(options['path']))
        elif action == 'security':
            rows = scan_path(options['path'])
        elif action == 'security_inline':
            rows = []
            files = options.get('files', [])
            if not files or len(files) > 5000:
                raise ValueError('请选择 1–5000 个代码文件')
            for item in files:
                if len(item['content'].encode('utf-8')) > 1024*1024:
                    raise ValueError('单个代码文件不得超过 1MB')
                rows.extend(scan_code(item['content'], Path(item['name']).name))
        else:
            raise ValueError('未知功能')
        self.rows = rows
        self.last_action = action
        return rows

    def export(self, path):
        return write_rows(path, self.rows, self.guard)

    def state(self):
        return {'machine': self.guard.machine, 'activated': self.guard.activated,
                'total': len(self.rows), 'preview': self.rows[:100] if self.guard.activated else self.rows[:10],
                'action': self.last_action, 'export_limit': None if self.guard.activated else 10}
