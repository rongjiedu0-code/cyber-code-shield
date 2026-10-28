import ctypes
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .service import ToolboxService

TITLE = '电商财务对账与商机雷达一体机'


class DesktopApp:
    def __init__(self, root, service=None):
        self.root = root
        self.service = service or ToolboxService()
        self.messages = queue.Queue()
        self.busy = False
        root.title(TITLE)
        root.geometry('1120x800')
        root.minsize(920, 650)
        root.configure(bg='#f2f6f7')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('Microsoft YaHei UI', 10))
        style.configure('TButton', padding=(12, 7))
        style.configure('Accent.TButton', background='#087f8c', foreground='white')
        style.configure('Treeview', rowheight=30, font=('Microsoft YaHei UI', 9))
        style.configure('Treeview.Heading', font=('Microsoft YaHei UI', 9, 'bold'))
        header = tk.Frame(root, bg='#123b46', padx=20, pady=16)
        header.pack(fill='x')
        tk.Label(header, text=TITLE, fg='white', bg='#123b46', font=('Microsoft YaHei UI', 20, 'bold')).pack(anchor='w')
        tk.Label(header, text='账目核对 · 需求线索 · 商品报价分析 · 本地代码体检', fg='#bce6e7', bg='#123b46').pack(anchor='w', pady=(6, 0))
        bar = ttk.Frame(root, padding=12)
        bar.pack(fill='x')
        self.license_label = ttk.Label(bar)
        self.license_label.pack(side='left')
        ttk.Button(bar, text='复制机器码', command=self.copy_machine).pack(side='left', padx=8)
        self.key_entry = ttk.Entry(bar, width=26)
        self.key_entry.pack(side='left', padx=6)
        ttk.Button(bar, text='输入激活码解锁', command=self.activate).pack(side='left')
        self.update_license()
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill='x', padx=14)
        self.paths = {}
        self.actions = {}
        account = self.tab('① 电商账单核对')
        ttk.Label(account, text='选择或拖入 CSV / XLSX。长订单号保留为文本；精度不足会标为待核实。').pack(anchor='w')
        self.path_row(account, 'orders', '订单表', False)
        self.path_row(account, 'payments', '流水表', False)
        mapping = ttk.Frame(account)
        mapping.pack(fill='x', pady=5)
        self.mapping = {}
        for key, label in [('order_id', '订单号列'), ('order_amount', '应收列'), ('payment_id', '流水订单号列'), ('payment_amount', '实收列')]:
            ttk.Label(mapping, text=label).pack(side='left', padx=(3, 2))
            var = tk.StringVar(value='自动')
            self.mapping[key] = var
            ttk.Entry(mapping, textvariable=var, width=12).pack(side='left', padx=(0, 8))
        actions = ttk.Frame(account)
        actions.pack(fill='x', pady=6)
        self.button(actions, '开始核对', lambda: self.launch('reconcile', orders=self.paths['orders'].get(), payments=self.paths['payments'].get(), mapping={k:v.get() for k,v in self.mapping.items()}))
        ttk.Button(actions, text='载入随附样例（明确标记）', command=self.load_samples).pack(side='left', padx=8)
        radar = self.tab('② 客户需求线索')
        ttk.Label(radar, text='公开社区内容仅作为线索；分数是规则排序，不代表已验证购买需求。').pack(anchor='w')
        radar_form = ttk.Frame(radar)
        radar_form.pack(fill='x', pady=8)
        ttk.Label(radar_form, text='关键词（可留空）').pack(side='left')
        self.keyword = tk.StringVar()
        ttk.Entry(radar_form, textvariable=self.keyword, width=30).pack(side='left', padx=8)
        self.button(radar_form, '抓取公开社区', lambda: self.launch('radar', keyword=self.keyword.get()))
        self.path_row(radar, 'signals', '本地内容表', False)
        self.button(radar, '分析本地需求内容', lambda: self.launch('radar_file', path=self.paths['signals'].get(), keyword=self.keyword.get()))
        trend = self.tab('③ 热词与商品报价')
        ttk.Label(trend, text='热榜快照用于发现线索；真实价格带与毛利来自你导入的报价表，不把热度当销量。').pack(anchor='w')
        trend_form = ttk.Frame(trend)
        trend_form.pack(fill='x', pady=8)
        ttk.Label(trend_form, text='热词筛选（可留空）').pack(side='left')
        self.trend_keyword = tk.StringVar()
        ttk.Entry(trend_form, textvariable=self.trend_keyword, width=30).pack(side='left', padx=8)
        self.button(trend_form, '获取国内公开热榜', lambda: self.launch('trends', keyword=self.trend_keyword.get()))
        self.path_row(trend, 'products', '商品报价表', False)
        self.button(trend, '计算价格带与估算毛利', lambda: self.launch('products', path=self.paths['products'].get()))
        security = self.tab('④ Python / JS 代码体检')
        ttk.Label(security, text='只读取源码并扫描，不执行被检查代码。支持 Python / JS / TS，报告会脱敏常见密钥。').pack(anchor='w')
        self.path_row(security, 'project', '项目目录', True)
        self.button(security, '开始本地安全体检', lambda: self.launch('security', path=self.paths['project'].get()))
        ttk.Label(security, text='未命中规则不等于绝对安全；外部权限和业务流程仍需人工检查。').pack(anchor='w', pady=6)
        bottom = ttk.Frame(root, padding=(14, 8))
        bottom.pack(fill='both', expand=True)
        toolbar = ttk.Frame(bottom)
        toolbar.pack(fill='x', pady=(0, 7))
        self.status = tk.StringVar(value='就绪。所有计算功能均可试用；未激活可导出前 10 行。')
        ttk.Label(toolbar, textvariable=self.status).pack(side='left')
        ttk.Button(toolbar, text='导出 Excel', command=lambda:self.export('.xlsx')).pack(side='right', padx=5)
        ttk.Button(toolbar, text='导出 CSV', command=lambda:self.export('.csv')).pack(side='right', padx=5)
        grid = ttk.Frame(bottom)
        grid.pack(fill='both', expand=True)
        self.table = ttk.Treeview(grid, show='headings')
        self.table.tag_configure('alert', background='#fde3e3', foreground='#8e2525')
        ys = ttk.Scrollbar(grid, orient='vertical', command=self.table.yview)
        xs = ttk.Scrollbar(grid, orient='horizontal', command=self.table.xview)
        self.table.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.table.grid(row=0,column=0,sticky='nsew')
        ys.grid(row=0,column=1,sticky='ns')
        xs.grid(row=1,column=0,sticky='ew')
        grid.columnconfigure(0,weight=1)
        grid.rowconfigure(0,weight=1)
        ttk.Label(root, text='本地处理账单与源码 · 联系 / 定制：rongjiedu1@gmail.com', padding=(16, 6)).pack(anchor='w')
        self.root.after(100, self.poll)
        self.enable_file_drop()

    def tab(self, text):
        frame = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(frame, text=text)
        return frame

    def button(self, parent, text, command):
        button = ttk.Button(parent, text=text, style='Accent.TButton', command=command)
        button.pack(side='left' if isinstance(parent, ttk.Frame) and parent not in self.tabs.winfo_children() else 'top', anchor='w', pady=3)
        self.actions[text] = button
        return button

    def path_row(self, parent, key, label, folder):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=6)
        ttk.Label(frame,text=label,width=12).pack(side='left')
        var = tk.StringVar()
        self.paths[key] = var
        ttk.Entry(frame,textvariable=var).pack(side='left',fill='x',expand=True,padx=6)
        def select():
            value = filedialog.askdirectory() if folder else filedialog.askopenfilename(filetypes=[('表格','*.csv *.xlsx *.tsv *.txt')])
            if value:
                var.set(value)
        ttk.Button(frame,text='选择目录' if folder else '选择文件',command=select).pack(side='left')

    def copy_machine(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.service.guard.machine)
        self.status.set('机器码已复制，可发给卖家获取本机激活码。')

    def update_license(self):
        self.license_label.configure(text='机器码：' + self.service.guard.machine + ('  已永久激活' if self.service.guard.activated else '  试用：导出前 10 行'))

    def activate(self):
        try:
            self.service.guard.activate(self.key_entry.get())
            self.update_license()
            self.render()
            self.status.set('已永久激活本机，可导出全部计算结果。')
        except (ValueError, OSError) as error:
            messagebox.showerror('激活未完成',str(error),parent=self.root)

    def load_samples(self):
        examples = Path(__file__).resolve().parents[1] / '示例表格'
        self.paths['orders'].set(str(examples/'示例_订单表.csv'))
        self.paths['payments'].set(str(examples/'示例_流水表.csv'))
        self.paths['products'].set(str(examples/'示例_商品报价.csv'))
        self.paths['signals'].set(str(examples/'示例_客户需求.csv'))
        self.paths['project'].set(str(examples/'示例代码'))
        self.status.set('已载入人工构造的功能样例，请点击开始核对；处理客户文件时选择真实表格。')

    def launch(self, action, **options):
        if self.busy:
            return
        self.busy = True
        self.status.set('正在处理，请稍候… 网络功能最多等待公开接口响应。')
        def work():
            try:
                self.service.run(action, **options)
                self.messages.put(('ok', None))
            except Exception as error:
                self.messages.put(('error', str(error)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, data = self.messages.get_nowait()
                self.busy = False
                if kind == 'ok':
                    self.render()
                else:
                    self.status.set('处理未完成：' + data)
                    messagebox.showerror('请检查输入',data,parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100,self.poll)

    def render(self):
        state = self.service.state()
        rows = state['preview']
        headers = list(dict.fromkeys(k for row in rows for k in row if not k.startswith('__')))
        self.table.delete(*self.table.get_children())
        self.table['columns'] = headers
        for key in headers:
            self.table.heading(key,text=key)
            width = 240 if key in {'订单号','状态','说明','标题','代码片段','内容摘录'} else 140
            self.table.column(key,width=width,minwidth=100,stretch=False)
        for row in rows:
            self.table.insert('', 'end', values=[str(row.get(k,'')) for k in headers], tags=('alert',) if row.get('异常')=='是' else ())
        self.status.set(f'已完成 {state["total"]} 行；预览 {len(rows)} 行。' + ('已激活，可全量导出。' if state['activated'] else '试用可导出前 10 行。'))

    def export(self, extension):
        if self.busy:
            return
        target = filedialog.asksaveasfilename(defaultextension=extension,initialfile='核对与分析结果'+extension,filetypes=[('结果文件','*'+extension)])
        if target:
            try:
                count = self.service.export(target)
                self.status.set(f'已导出 {count} 行：{target}')
            except Exception as error:
                messagebox.showerror('导出未完成',str(error),parent=self.root)

    def accept_dropped_paths(self, paths):
        for path in paths:
            if Path(path).is_dir():
                self.paths['project'].set(path)
                self.tabs.select(3)
            elif not self.paths['orders'].get():
                self.paths['orders'].set(path)
                self.tabs.select(0)
            else:
                self.paths['payments'].set(path)
                self.tabs.select(0)
        self.status.set('文件已接收，请核对订单表和流水表的位置，再开始计算。')

    def enable_file_drop(self):
        if os.name != 'nt':
            return
        from ctypes import wintypes
        self.root.update_idletasks()
        user = ctypes.windll.user32
        shell = ctypes.windll.shell32
        user.GetParent.argtypes = [wintypes.HWND]
        user.GetParent.restype = wintypes.HWND
        shell.DragAcceptFiles.argtypes = [wintypes.HWND,wintypes.BOOL]
        hwnd = user.GetParent(self.root.winfo_id())
        pointer = ctypes.c_ssize_t
        callback_type = ctypes.WINFUNCTYPE(pointer, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        set_proc = user.SetWindowLongPtrW
        set_proc.argtypes = [wintypes.HWND, ctypes.c_int, pointer]
        set_proc.restype = pointer
        user.CallWindowProcW.argtypes = [pointer, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user.CallWindowProcW.restype = pointer
        shell.DragQueryFileW.argtypes = [wintypes.HANDLE,wintypes.UINT,wintypes.LPWSTR,wintypes.UINT]
        shell.DragFinish.argtypes = [wintypes.HANDLE]
        @callback_type
        def dropped(window, message, wparam, lparam):
            if message == 0x233:
                paths = []
                try:
                    count = shell.DragQueryFileW(wparam,0xffffffff,None,0)
                    for i in range(count):
                        length = shell.DragQueryFileW(wparam,i,None,0)
                        buffer = ctypes.create_unicode_buffer(length+1)
                        shell.DragQueryFileW(wparam,i,buffer,length+1)
                        paths.append(buffer.value)
                finally:
                    shell.DragFinish(wparam)
                self.root.after(0,lambda:self.accept_dropped_paths(paths))
                return 0
            return user.CallWindowProcW(self._old_proc,window,message,wparam,lparam)
        self._drop_callback = dropped
        self._drop_hwnd = hwnd
        self._old_proc = set_proc(hwnd,-4,ctypes.cast(dropped,ctypes.c_void_p).value)
        shell.DragAcceptFiles(hwnd,True)
        def close():
            shell.DragAcceptFiles(hwnd,False)
            set_proc(hwnd,-4,self._old_proc)
            self.root.destroy()
        self.root.protocol('WM_DELETE_WINDOW',close)


def main():
    root = tk.Tk()
    DesktopApp(root)
    root.mainloop()
