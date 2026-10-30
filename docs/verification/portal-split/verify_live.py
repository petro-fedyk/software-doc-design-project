"""Opt-in write verification on the original coursework database, designated portal.qa records only.
Run from repo root: .venv/bin/python docs/verification/portal-split/verify_live.py
No reset, cloning, migrations, or modification of existing catalog records.
"""
import json, os, sys, time, uuid, urllib.request, urllib.error
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'apps/backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings
from django.utils import timezone
from pharmacy import models as m
assert settings.DATABASES['default']['NAME'] == 'internet_pharmacy'
CUSTOMER='http://127.0.0.1:4173/api'
MANAGEMENT='http://127.0.0.1:4174/api'
DIRECT='http://127.0.0.1:8000/api'
PASSWORD='Portal-QA-2026-Only'
results=[]
def call(base,path,method='GET',body=None,token=None,expected=200):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request(base+path, data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response: status=response.status; data=json.load(response)
    except urllib.error.HTTPError as error:
        status=error.code; data=json.loads(error.read())
    assert status == expected, (path,status,data)
    results.append({'request':method+' '+path,'origin':base,'status':status,'result':'PASS'})
    return data

def rows(path,token):
    data=call(MANAGEMENT,path,token=token); output=data if isinstance(data,list) else data['results']
    while isinstance(data,dict) and data.get('next'):
        from urllib.parse import urlsplit
        url=urlsplit(data['next']); data=call(MANAGEMENT,url.path.removeprefix('/api')+'?'+url.query,token=token); output.extend(data['results'])
    return output

def ensure(path,key,value,body,token):
    found=next((r for r in rows(path,token) if r.get(key)==value),None)
    return found or call(MANAGEMENT,path,'POST',body,token,201)

admin=call(MANAGEMENT,'/auth/token/','POST',{'username':'admin','password':'admin'})['access']
me=call(MANAGEMENT,'/me/',token=admin); assert me['role']=='ADMIN'
branch=ensure('/pharmacies/','code','PORTAL-QA-1',{'code':'PORTAL-QA-1','name':'Portal QA pharmacy','city':'Навчальна','address':'Синтетичний запис перевірки порталів','phone':'','is_active':True},admin)
other=ensure('/pharmacies/','code','PORTAL-QA-2',{'code':'PORTAL-QA-2','name':'Portal QA other pharmacy','city':'Навчальна','address':'Синтетичний запис перевірки порталів','phone':'','is_active':True},admin)
staff=ensure('/admin/users/','username','portal.qa.staff',{'username':'portal.qa.staff','email':'portal.qa.staff@example.test','password':PASSWORD,'role':'STAFF','is_active':True},admin)
assignments=rows('/admin/assignments/',admin)
if not any(r['user']==staff['id'] and r['pharmacy']==branch['id'] for r in assignments): call(MANAGEMENT,'/admin/assignments/','POST',{'user':staff['id'],'pharmacy':branch['id'],'is_active':True},admin,201)
category=rows('/categories/',admin)[0]['id']; maker=rows('/manufacturers/',admin)[0]['id']
product=ensure('/products/','sku','PORTAL-QA-OTC',{'sku':'PORTAL-QA-OTC','name':'Portal QA навчальний товар','description':'Синтетичний товар для перевірки двох порталів','category':category,'manufacturer':maker,'prescription_required':False,'is_active':True},admin)
# Inventory has no create endpoint; seed only this newly designated row through the existing model.
m.PharmacyInventory.objects.get_or_create(pharmacy_id=branch['id'],product_id=product['id'],defaults={'unit_price':'17.25','on_hand':20,'reserved':0,'is_listed':True,'updated_at':timezone.now(),'version':0})
if not m.Users.objects.filter(username='portal.qa.customer').exists():
    session=call(CUSTOMER,'/auth/register/','POST',{'username':'portal.qa.customer','email':'portal.qa.customer@example.test','password':PASSWORD,'full_name':'Portal QA Customer'},expected=201)
    customer=session['access']
else: customer=call(CUSTOMER,'/auth/token/','POST',{'username':'portal.qa.customer','password':PASSWORD})['access']
staff_token=call(MANAGEMENT,'/auth/token/','POST',{'username':'portal.qa.staff','password':PASSWORD})['access']
call(MANAGEMENT,'/auth/token/','POST',{'username':'portal.qa.customer','password':PASSWORD},expected=403)
call(CUSTOMER,'/auth/token/','POST',{'username':'admin','password':'admin'},expected=403)
call(MANAGEMENT,'/auth/register/','POST',{},expected=403)
call(DIRECT,'/admin/users/',token=customer,expected=403)
call(DIRECT,'/admin/statistics/',token=staff_token,expected=403)
call(MANAGEMENT,f"/pharmacies/{other['id']}/inventory/{product['id']}/",'PATCH',{'unit_price':'99.00'},staff_token,403)
call(MANAGEMENT,f"/pharmacies/{branch['id']}/inventory/{product['id']}/",'PATCH',{'unit_price':'17.50'},staff_token)
public=call(CUSTOMER,f"/products/{product['id']}/availability/")
assert any(r['pharmacy_id']==branch['id'] and str(r['unit_price'])=='17.50' for r in public)
call(CUSTOMER,f"/products/{product['id']}/")
call(CUSTOMER,'/cart/','PUT',{'product_id':product['id'],'quantity':1},customer)
quote=call(CUSTOMER,'/checkout/quote/','POST',{'pharmacy_id':branch['id'],'fulfillment_method':'PICKUP','items':[{'product_id':product['id'],'quantity':1}]},customer)
order=call(CUSTOMER,'/orders/','POST',{'pharmacy_id':branch['id'],'fulfillment_method':'PICKUP','payment_method':'CARD','items':[{'product_id':product['id'],'quantity':1,'expected_unit_price':quote['lines'][0]['price']}],'expected_total':quote['grand_total']},customer,201)
order_id=order['id']
assert m.Orders.objects.filter(id=order_id,customer__username='portal.qa.customer').exists()
call(CUSTOMER,f'/orders/{order_id}/pay/','POST',{'idempotency_key':'portal-qa-'+str(uuid.uuid4())},customer,202)
for attempt in range(20):
    fulfillment=call(CUSTOMER,f'/orders/{order_id}/fulfillment/',token=customer)
    if any(p['status']=='SUCCEEDED' for p in fulfillment.get('payments',[])): break
    time.sleep(1)
assert any(p['status']=='SUCCEEDED' for p in fulfillment.get('payments',[])), fulfillment
call(MANAGEMENT,f'/orders/{order_id}/verify-prescription/','POST',{'approved':True},admin,403)
for state in ['PROCESSING','READY_FOR_PICKUP','COMPLETED']:
    call(MANAGEMENT,f'/orders/{order_id}/transition/','POST',{'status':state},staff_token)
final=call(CUSTOMER,f'/orders/{order_id}/',token=customer)
assert final['status']=='COMPLETED'
call(CUSTOMER,'/cart/','PUT',{'product_id':product['id'],'quantity':0},customer)
call(MANAGEMENT,'/admin/statistics/',token=admin)
call(MANAGEMENT,'/admin/audit/',token=admin)
# Expired JWT with correct signature for the designated customer must be rejected by Django.
import jwt
from pharmacy.api.auth import fingerprint
user=m.Users.objects.get(username='portal.qa.customer')
expired=jwt.encode({'sub':str(user.id),'iat':int(time.time())-120,'exp':int(time.time())-60,'type':'access','pwd':fingerprint(user),'iss':'internet-pharmacy','aud':'pharmacy-api'},settings.SECRET_KEY,algorithm='HS256')
call(DIRECT,'/me/',token=expired,expected=401)
output={'date':str(timezone.now()),'database':settings.DATABASES['default']['NAME'],'fixture':{'staff_id':staff['id'],'pharmacy_id':branch['id'],'other_pharmacy_id':other['id'],'product_id':product['id'],'order_id':order_id},'checks':results}
(ROOT/'docs/verification/portal-split/live-results.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'result':'PASS','requests':len(results),'fixture':output['fixture']},ensure_ascii=False))
