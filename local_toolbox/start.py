from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '_deps'))

if __name__ == '__main__':
    try:
        if '--web' in sys.argv:
            from toolbox.web import main
        else:
            from toolbox.desktop import main
        main()
    except Exception:
        import os
        import traceback
        location = Path(os.environ.get('LOCALAPPDATA', str(ROOT))) / 'CNBusinessToolbox/startup-error.log'
        location.parent.mkdir(parents=True, exist_ok=True)
        location.write_text(traceback.format_exc(), encoding='utf-8')
        import tkinter.messagebox
        tkinter.messagebox.showerror('启动未完成', '错误记录已保存：' + str(location))
