import argparse
import json
from .service import ToolboxService


def main():
    parser = argparse.ArgumentParser(description='本地电商核对、需求线索、热词与代码体检')
    parser.add_argument('action', choices=['reconcile', 'radar', 'radar_file', 'trends', 'products', 'security'])
    parser.add_argument('--orders')
    parser.add_argument('--payments')
    parser.add_argument('--path')
    parser.add_argument('--keyword', default='')
    parser.add_argument('--limit', type=int, default=30)
    parser.add_argument('--export', dest='output')
    args = vars(parser.parse_args())
    action, output = args.pop('action'), args.pop('output')
    service = ToolboxService()
    service.run(action, **args)
    if output:
        print(json.dumps({'导出行数': service.export(output), '文件': output}, ensure_ascii=False))
    else:
        print(json.dumps(service.state(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
