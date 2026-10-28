from contextlib import contextmanager
import csv
import json
import threading
import urllib.error
import urllib.request
import pytest
from toolbox.web import create_server
from toolbox.service import ToolboxService
from toolbox.license_guard import LicenseGuard
from key_fixtures import generate


@pytest.fixture
def server(tmp_path):
    service=ToolboxService(LicenseGuard('DRJ88A01',tmp_path/'license.json'))
    service.rows=[{'订单号':str(123456789012345678+i),'结果':'正常'} for i in range(22)]
    instance=create_server(service)
    thread=threading.Thread(target=instance.serve_forever,daemon=True);thread.start()
    yield instance
    instance.shutdown();instance.server_close();thread.join(timeout=5)


def request(server,path,body=None,headers=None):
    headers={'X-Session-Token':server.session_token,**(headers or {})}
    req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}'+path,data=body,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return r.status,r.read(),r.headers
    except urllib.error.HTTPError as e:return e.code,e.read(),e.headers


def test_web_trial_and_activation_real_http(server):
    status,body,_=request(server,'/api/state')
    data=json.loads(body);assert status==200 and data['total']==22 and len(data['preview'])==10
    status,body,headers=request(server,'/api/export?format=csv')
    assert status==200 and len(body.decode('utf-8-sig').splitlines())==11
    payload=json.dumps({'key':generate('DRJ88A01','sha')}).encode()
    assert request(server,'/api/activate',payload,{'Content-Type':'application/json'})[0]==200
    status,body,_=request(server,'/api/export?format=csv')
    assert status==200 and len(body.decode('utf-8-sig').splitlines())==23


@pytest.mark.parametrize('path',['/api/state','/api/export?format=csv','/api/export?format=xlsx'])
def test_web_rejects_no_token(server,path):
    assert request(server,path,headers={'X-Session-Token':''})[0]==403


@pytest.mark.parametrize('origin',['https://evil.example.cn','http://localhost:1234','null'])
def test_web_rejects_cross_origin(server,origin):
    assert request(server,'/api/activate',b'{}',{'Origin':origin})[0]==403


def test_web_host_rebinding_protection(server):
    assert request(server,'/',headers={'Host':'evil.example.cn'})[0]==403
    assert request(server,'/')[0]==200
    assert request(server,'/api/export?format=html')[0]==400
    assert request(server,'/missing')[0]==404


def multipart(action,files):
    boundary='----LocalTestBoundary'
    body=f'--{boundary}\r\nContent-Disposition: form-data; name="action"\r\n\r\n{action}\r\n'.encode()
    for field,(filename,content) in files.items():
        body+=f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\nContent-Type: text/plain\r\n\r\n'.encode()+content+b'\r\n'
    body+=f'--{boundary}--\r\n'.encode()
    return body,{'Content-Type':'multipart/form-data; boundary='+boundary}


def test_web_upload_reconciliation(server):
    body,headers=multipart('reconcile',{'orders':('orders.csv','订单号,金额\n001,2.00\n002,3.00\n'.encode()),
        'payments':('flow.csv','订单号,金额\n001,2.00\n'.encode())})
    status,body,_=request(server,'/api/run',body,headers)
    data=json.loads(body)
    assert status==200 and data['total']==2 and data['preview'][0]['状态']=='漏收款'


@pytest.mark.parametrize('action,files',[('radar_file',{'path':('leads.csv','标题,内容\n对账太耗时,想找工具\n'.encode())}),
    ('products',{'path':('prices.csv','商品名称,销售价,采购成本\n收纳盒,20,10\n'.encode())}),
    ('security_inline',{'codes':('review.py',b'import subprocess\nsubprocess.run(user,shell=True)\n')})])
def test_web_all_local_features(server,action,files):
    body,headers=multipart(action,files)
    status,body,_=request(server,'/api/run',body,headers)
    assert status==200 and json.loads(body)['total']>=1


def test_web_invalid_request_is_explicit(server):
    assert request(server,'/api/run',b'{}',{'Content-Type':'application/json'})[0]==400
    assert request(server,'/api/activate',b'{broken',{'Content-Type':'application/json'})[0]==400
