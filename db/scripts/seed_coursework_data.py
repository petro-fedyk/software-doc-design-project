#!/usr/bin/env python3
"""Append a repeatable coursework dataset without deleting or resetting rows."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from migrate import ROOT, connect, load_env_file
from seed_learning_data import (
    CATEGORY_INDEX_BY_PRODUCT,
    CATEGORY_NAMES as ORIGINAL_CATEGORIES,
    MANUFACTURERS as ORIGINAL_MANUFACTURERS,
    PRODUCTS as ORIGINAL_PRODUCTS,
)

NOW = datetime.now().astimezone().replace(tzinfo=None, microsecond=0)
PHARMACY_CODES = [f'CW-PH-{i:03d}' for i in range(1, 50)]
CUSTOMERS = 50
STAFF = 50

# These are real registered Ukrainian medicine trade names and package variants.
# Prices and all customer/order/stock history generated below are fictional
# coursework data, not live pharmacy offers or real patient records.
PACKAGE_PRODUCTS = [
    # name, ingredient, registration, maker, category, prescription, image, source
    ('Нурофєн® 200 мг таблетки, №6', 'Ібупрофен 200 мг', 'UA/6313/02/02', 'Reckitt Benckiser Healthcare (UK) Limited', 'Pain management', False,
     'https://www.add.ua/media/catalog/product/cache/74c1057f7991b4edb2bc7bdaa94de933/n/u/nurofen-_6_-_-200-__5000167067460_1_1.jpg', 'https://compendium.com.ua/dec/271308/'),
    ('Нурофєн® 200 мг таблетки, №12', 'Ібупрофен 200 мг', 'UA/6313/02/02', 'Reckitt Benckiser Healthcare (UK) Limited', 'Pain management', False,
     'https://www.add.ua/media/catalog/product/cache/74c1057f7991b4edb2bc7bdaa94de933/n/u/nurofen-_12_-_-200-__5000167046878.jpg', 'https://compendium.com.ua/dec/271308/'),
    ('Нурофєн® 200 мг таблетки, №24', 'Ібупрофен 200 мг', 'UA/6313/02/02', 'Reckitt Benckiser Healthcare (UK) Limited', 'Pain management', False,
     'https://www.add.ua/media/catalog/product/cache/74c1057f7991b4edb2bc7bdaa94de933/n/u/nurofen-_24_-_-200-__5000167070118.jpg', 'https://compendium.com.ua/dec/271308/'),
    ('Нурофєн® 12+ 200 мг таблетки, №12', 'Ібупрофен 200 мг', 'UA/10906/01/01', 'Reckitt Benckiser Healthcare (UK) Limited', 'Pain management', False,
     'https://www.add.ua/media/catalog/product/cache/74c1057f7991b4edb2bc7bdaa94de933/n/u/nurofen-_12_-_-200-__5000167046878.jpg', 'https://compendium.com.ua/dec/261961/'),
    ('Нурофєн® Колд & Флю 200 мг + 5 мг, №12', 'Ібупрофен 200 мг; псевдоефедрин 5 мг', 'UA/17937/01/01', 'Reckitt Benckiser Healthcare International Limited', 'Respiratory care', False,
     None, 'https://compendium.com.ua/info/357974/'),
    ('Но-Шпа® 40 мг таблетки, №24', 'Дротаверину гідрохлорид 40 мг', 'UA/0391/01/02', 'Opella Healthcare Ukraine', 'Digestive health', False,
     'https://liki24.com/image/catalog/product/newupload/6649-133655092673297502.png?h=900&w=900', 'https://compendium.com.ua/dec/260653/'),
    ('Но-Шпа® 40 мг таблетки, №60', 'Дротаверину гідрохлорид 40 мг', 'UA/0391/01/02', 'Opella Healthcare Ukraine', 'Digestive health', False,
     'https://1sa.com.ua/media/catalog/product/cache/0cb86aa621afec2b43f6f8736c54c157/n/o/no-spa_60_01.png', 'https://compendium.com.ua/dec/260653/'),
    ('Но-Шпа® 40 мг таблетки, №100', 'Дротаверину гідрохлорид 40 мг', 'UA/0391/01/02', 'Opella Healthcare Ukraine', 'Digestive health', False,
     'https://www.add.ua/media/catalog/product/cache/74c1057f7991b4edb2bc7bdaa94de933/n/o/no-spa_100_03_png.webp', 'https://compendium.com.ua/dec/260653/'),
    ('Но-Шпа® Комфорт 40 мг таблетки, №24', 'Дротаверину гідрохлорид 40 мг', 'UA/15328/01/01', 'Opella Healthcare Ukraine', 'Digestive health', False,
     'https://liki24.com/image/catalog/product/newupload/6649-133655092673297502.png?h=900&w=900', 'https://compendium.com.ua/dec/550076/'),
    ('Но-Шпа® форте 80 мг таблетки, №24', 'Дротаверину гідрохлорид 80 мг', 'UA/8879/01/01', 'Opella Healthcare Ukraine', 'Digestive health', False,
     None, 'https://compendium.com.ua/dec/260653/'),
    ('Панадол® 500 мг таблетки, №12', 'Парацетамол 500 мг', 'UA/2562/01/01', 'GlaxoSmithKline Dungarvan Ltd.', 'Pain management', False,
     'https://online-apteka.com.ua/assets/cache_image/products/142987/panadol-12_0x0_e6a.webp', 'https://compendium.com.ua/dec/267269/'),
    ('Панадол® Екстра таблетки, №12', 'Парацетамол; кофеїн', 'UA/2562/01/01', 'GlaxoSmithKline Dungarvan Ltd.', 'Pain management', False,
     'https://www.add.ua/media/catalog/product/cache/74c1057f7991b4edb2bc7bdaa94de933/3/3/3333_6_1.jpg', 'https://compendium.com.ua/dec/267269/'),
    ('Панадол® Бебі суспензія 120 мг/5 мл, 100 мл', 'Парацетамол 120 мг/5 мл', 'UA/2562/02/01', 'GlaxoSmithKline Dungarvan Ltd.', 'Pediatric care', False,
     None, 'https://compendium.com.ua/dec/267269/'),
    ('Німесил® гранули 100 мг/2 г, №30', 'Німесулід 100 мг', 'UA/9855/01/01', 'Berlin-Chemie AG', 'Pain management', True,
     'https://liki24.com/image/catalog/product/newupload/50981-nimesil-gran-dp-susp-dperor-prim-100-mg-paket-odnodoz-2-g-30-1.png?h=1000&w=1000', 'https://compendium.com.ua/dec/275265/'),
    ('Німесил® гранули 100 мг/2 г, №9', 'Німесулід 100 мг', 'UA/9855/01/01', 'Berlin-Chemie AG', 'Pain management', True,
     'https://storage.googleapis.com/static-storage/products/images/v2/3257_VgriIozf_20250529_175915.jpg', 'https://compendium.com.ua/dec/275265/'),
    ('Лінекс® капсули, №16', 'Lactobacillus; Bifidobacterium; Enterococcus', 'UA/14267/01/01', 'Sandoz GmbH', 'Digestive health', False,
     'https://compendium.com.ua/img/dec/5352_113_78_22_20.jpg', 'https://compendium.com.ua/dec/265167/5352/'),
    ('Лінекс® капсули, №32', 'Lactobacillus; Bifidobacterium; Enterococcus', 'UA/14267/01/01', 'Sandoz GmbH', 'Digestive health', False,
     'https://compendium.com.ua/img/dec/5352_113_78_22_20.jpg', 'https://compendium.com.ua/dec/265167/'),
    ('Лінекс Форте® капсули, №14', 'Lactobacillus; Bifidobacterium', 'UA/14267/02/01', 'Sandoz GmbH', 'Digestive health', False,
     'https://compendium.com.ua/img/dec/165099_102_77_11_17.jpg', 'https://compendium.com.ua/uk/atc/a07fa01/'),
    ('Лінекс Бебі® порошок, №10', 'Bifidobacterium animalis subsp. lactis', 'UA/14267/03/01', 'Sandoz GmbH', 'Pediatric care', False,
     None, 'https://compendium.com.ua/uk/atc/a07fa01/'),
    ('Лінекс® капсули у флаконі, №32', 'Lactobacillus; Bifidobacterium; Enterococcus', 'UA/14267/01/01', 'Sandoz GmbH', 'Digestive health', False,
     'https://compendium.com.ua/img/dec/5352_113_78_22_20.jpg', 'https://compendium.com.ua/dec/265167/'),
    ('Креон® 10 000 капсули, №20', 'Панкреатин 150 мг', 'UA/9842/01/01', 'Abbott Laboratories GmbH', 'Digestive health', False,
     'https://www.add.ua/media/catalog/product/cache/207e23213cf636ccdef205098cf3c8a3/f/r/front_box_capsule_10000_ua_kreon.png', 'https://compendium.com.ua/dec/275246/'),
    ('Креон® 10 000 капсули, №50', 'Панкреатин 150 мг', 'UA/9842/01/01', 'Abbott Laboratories GmbH', 'Digestive health', False,
     'https://www.add.ua/media/catalog/product/cache/207e23213cf636ccdef205098cf3c8a3/f/r/front_box_capsule_10000_ua_kreon.png', 'https://compendium.com.ua/dec/275246/'),
    ('Креон® 25 000 капсули, №20', 'Панкреатин 300 мг', 'UA/9842/01/01', 'Abbott Laboratories GmbH', 'Digestive health', False,
     'https://liki24.com/image/catalog/product/newupload/42010-134070567349666474.png?h=1000&w=1000', 'https://compendium.com.ua/dec/275246/'),
    ('Ессенціалє® форте Н 300 мг капсули, №30', 'Есенціальні фосфоліпіди 300 мг', 'UA/8682/01/01', 'E. Nattermann & Cie GmbH', 'Liver care', False,
     'https://compendium.com.ua/img/inf/sanofi_essentiale_kaps.jpg?v=1598850952', 'https://compendium.com.ua/dec/273906/'),
    ('Мезим® форте 10 000 таблетки, №20', 'Панкреатин', 'UA/7977/01/01', 'Berlin-Chemie AG', 'Digestive health', False,
     'https://apteka911.ua/content/shop/products/1993/photos/19501-1993-big-1500-1500-9614.jpg', 'https://compendium.com.ua/dec/273153/'),
]

EXTRA_CATEGORIES = [
    'Anti-infectives', 'Cardiovascular care', 'Endocrine care', 'Respiratory care',
    'Digestive health', 'Allergy care', 'Pain management', 'Dermatology',
    'Neurology', 'Ophthalmology', 'Urology', 'Women’s health', 'Men’s health',
    'Vitamins and minerals', 'Immunology', 'Rheumatology', 'Hematology',
    'Oncology support', 'ENT care', 'Diabetes care', 'Wound care', 'Anesthesia',
    'Vaccines', 'Renal care', 'Pediatric care', 'Gastroenterology', 'Hepatology',
    'Antivirals', 'Antifungals', 'Antibacterials', 'Antihistamines', 'Analgesics',
    'Antipyretics', 'Antispasmodics', 'Probiotics', 'Enzyme preparations',
    'Venous circulation', 'Musculoskeletal care', 'Cold and flu', 'Nasal care',
    'Oral care', 'Eye care', 'Skin care', 'First aid', 'Medical devices',
    'Nutrition support', 'Sleep support', 'Smoking cessation', 'Travel health',
    'Pharmacy essentials',
    'Liver care',
]

EXTRA_MANUFACTURERS = [
    'Reckitt Benckiser Healthcare (UK) Limited', 'Reckitt Benckiser Healthcare International Limited',
    'Opella Healthcare Ukraine', 'Berlin-Chemie AG', 'GlaxoSmithKline Dungarvan Ltd.',
    'Sandoz GmbH', 'Abbott Laboratories GmbH', 'E. Nattermann & Cie GmbH',
    'Egis Pharmaceuticals PLC', 'Pharmaceutical Works Polpharma S.A.', 'UPSA SAS',
    'Biocodex', 'Lek Pharmaceuticals d.d.', 'Pfizer Inc.', 'Organon Heist B.V.',
    'Sanofi-Aventis Deutschland GmbH', 'Novo Nordisk A/S', 'KRKA d.d.',
    'Teva Pharmaceutical Industries Ltd.', 'Janssen Pharmaceutica NV',
    'Boehringer Ingelheim Pharma GmbH & Co. KG', 'Gedeon Richter Plc.',
    'Servier Laboratories', 'AstraZeneca AB', 'F. Hoffmann-La Roche Ltd.',
]

# Additional genuine pharmaceutical manufacturers, used to give the teaching
# catalogue realistic normalized reference data without inventing company names.
MORE_MANUFACTURERS = [
    'Bayer AG', 'Bayer Consumer Care AG', 'Johnson & Johnson', 'Merck KGaA',
    'MSD', 'Takeda Pharmaceutical Company Limited', 'AbbVie Inc.',
    'Bristol Myers Squibb', 'Eli Lilly and Company', 'Gilead Sciences, Inc.',
    'GlaxoSmithKline plc', 'Haleon plc', 'Ipsen Pharma', 'LUPIN Limited',
    'Menarini International Operations Luxembourg S.A.', 'Mylan Healthcare GmbH',
    'Orion Corporation', 'Recordati S.p.A.', 'STADA Arzneimittel AG',
    'Sun Pharmaceutical Industries Ltd.', 'UCB Pharma S.A.',
    'Viatris Healthcare GmbH', 'Zentiva k.s.', 'Angelini Pharma S.p.A.',
    'Bausch Health Ireland Limited', 'Bionorica SE', 'Dr. Reddy’s Laboratories',
    'Ferring Pharmaceuticals', 'Grindeks AS', 'Medochemie Ltd.',
    'Menarini Manufacturing Logistics and Services S.r.l.',
]

IMAGE_BY_PRODUCT = {
    'ДЕРМАЗОЛ': ('https://apteka911.ua/content/shop/products/1724/photos/15850-1724-big-1500-1500-ecd6.jpg', 'https://compendium.com.ua/dec/'),
    'ДЕТРАЛЕКС': ('https://compendium.com.ua/img/dec/servier_detreleks.jpg?v=1643618608', 'https://compendium.com.ua/dec/269068/'),
    'ДИКЛАК': ('https://ukrstore.com/media/catalog/product/cache/1/thumbnail/600x600/9df78eab33525d08d6e5fb8d27136e95/d/i/diclac_lipogel_gel_50g_1_tube_diclofenacum_.jpg', 'https://compendium.com.ua/dec/'),
    'ДИФЛЮКАН': ('https://apteka911.ua/content/drugs/973/top-product-image-1500-1500-bacb.jpg', 'https://compendium.com.ua/dec/'),
}

def insert_ignore(cur, table: str, columns: tuple[str, ...], values: tuple) -> None:
    marks = ','.join(['%s'] * len(columns))
    names = ','.join(f'`{name}`' for name in columns)
    cur.execute(f'INSERT IGNORE INTO `{table}` ({names}) VALUES ({marks})', values)


def get_id(cur, table: str, key: str, value):
    cur.execute(f'SELECT id FROM `{table}` WHERE `{key}`=%s', (value,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f'Could not find {table}.{key}={value!r} after insert')
    return row[0]


def ensure_simple(cur, table: str, key: str, value, columns: tuple[str, ...], values: tuple):
    insert_ignore(cur, table, columns, values)
    return get_id(cur, table, key, value)


def make_catalog():
    items = []
    for index, (name, ingredient, rx, low, high, reg, maker_index) in enumerate(ORIGINAL_PRODUCTS):
        maker = ORIGINAL_MANUFACTURERS[maker_index]
        category = ORIGINAL_CATEGORIES[CATEGORY_INDEX_BY_PRODUCT[index]]
        image_url, source_url = IMAGE_BY_PRODUCT.get(name.split('®')[0].strip(), (None, 'https://drlz.moz.gov.ua/register/products/'))
        items.append({
            'name': name, 'ingredient': ingredient, 'registration': reg,
            'manufacturer': maker, 'category': category, 'rx': bool(rx),
            'storage_min': low, 'storage_max': high, 'image': image_url,
            'source': source_url, 'pack': f'registered item {index + 1}',
        })
    for name, ingredient, reg, maker, category, rx, image, source in PACKAGE_PRODUCTS:
        items.append({
            'name': name, 'ingredient': ingredient, 'registration': reg,
            'manufacturer': maker, 'category': category, 'rx': rx,
            'storage_min': None, 'storage_max': None, 'image': image,
            'source': source, 'pack': name.rsplit(',', 1)[-1].strip(),
        })
    if len(items) != 50:
        raise RuntimeError(f'Expected 50 curated catalog rows, found {len(items)}')
    return items


def seed(cur):
    products = make_catalog()
    categories = list(dict.fromkeys([*ORIGINAL_CATEGORIES, *EXTRA_CATEGORIES]))
    # Make sure there are at least 50 distinct, meaningful catalog categories.
    categories.extend(f'Pharmacy category {i:02d}' for i in range(1, 51) if f'Pharmacy category {i:02d}' not in categories)
    manufacturers = list(dict.fromkeys([*ORIGINAL_MANUFACTURERS, *EXTRA_MANUFACTURERS, *MORE_MANUFACTURERS]))
    category_ids = {}
    for name in categories:
        category_ids[name] = ensure_simple(cur, 'categories', 'name', name, ('name',), (name,))
    manufacturer_ids = {}
    for name in manufacturers:
        manufacturer_ids[name] = ensure_simple(cur, 'manufacturers', 'name', name, ('name',), (name,))

    pharmacy_ids = []
    cities = ['Kyiv','Lviv','Odesa','Dnipro','Kharkiv','Vinnytsia','Poltava','Cherkasy','Zhytomyr','Rivne']
    streets = ['Shevchenka Avenue','Central Street','Soborna Street','Parkova Street','Myrna Street']
    for i, code in enumerate(PHARMACY_CODES, 1):
        insert_ignore(cur, 'pharmacies', ('code','name','address','city','phone','is_active'),
                      (code, f'Coursework Pharmacy {i:02d}', f'{streets[(i-1)%len(streets)]}, {10+i}', cities[(i-1)%len(cities)], f'+3800001{i:04d}', True))
        pharmacy_ids.append(get_id(cur, 'pharmacies', 'code', code))

    tier_ids = {}
    tier_values = [
        ('STANDARD', Decimal('0.0100'), Decimal('0.0000')),
        ('SOCIAL', Decimal('0.0250'), Decimal('0.0300')),
        ('PREMIUM', Decimal('0.0500'), Decimal('0.0700')),
    ]
    for code, bonus, discount in tier_values:
        insert_ignore(cur, 'loyalty_tiers', ('code','bonus_rate','discount_rate'), (code, bonus, discount))
        tier_ids[code] = get_id(cur, 'loyalty_tiers', 'code', code)

    customer_ids, staff_ids = [], []
    first_names = ['Olena','Andrii','Iryna','Maksym','Natalia','Dmytro','Sofiia','Bohdan','Kateryna','Roman']
    last_names = ['Kovalenko','Melnyk','Shevchenko','Bondarenko','Tkachenko','Koval','Moroz','Boyko','Kravchenko','Oliinyk']
    for i in range(1, CUSTOMERS + 1):
        username, email = f'cw.customer.{i:03d}', f'cw.customer.{i:03d}@example.test'
        insert_ignore(cur, 'users', ('username','email','password','role','is_active','is_staff','created_at'),
                      (username, email, '!', 'CUSTOMER', True, False, NOW-timedelta(days=90-i)))
        uid = get_id(cur, 'users', 'username', username); customer_ids.append(uid)
        fullname = f'{first_names[(i-1)%10]} {last_names[(i*3-1)%10]}'
        insert_ignore(cur, 'customer_profiles', ('user_id','phone','full_name','preferred_pharmacy_id'),
                      (uid, f'+3800002{i:04d}', fullname, pharmacy_ids[(i-1)%len(pharmacy_ids)]))
        insert_ignore(cur, 'carts', ('customer_id','updated_at'), (uid, NOW-timedelta(days=i%12)))
        insert_ignore(cur, 'notification_preferences', ('user_id','promotions_enabled','reminders_enabled'), (uid, i%2==0, True))
    for i in range(1, STAFF + 1):
        username, email = f'cw.pharmacist.{i:03d}', f'cw.pharmacist.{i:03d}@example.test'
        insert_ignore(cur, 'users', ('username','email','password','role','is_active','is_staff','created_at'),
                      (username, email, '!', 'STAFF', True, True, NOW-timedelta(days=180-i)))
        uid = get_id(cur, 'users', 'username', username); staff_ids.append(uid)
        pharmacy_id = pharmacy_ids[(i-1)%len(pharmacy_ids)]
        insert_ignore(cur, 'employee_assignments', ('user_id','pharmacy_id','is_active','created_at'), (uid, pharmacy_id, True, NOW-timedelta(days=120-i)))

    product_ids = []
    for i, item in enumerate(products, 1):
        sku = f'CW-{item["registration"].replace("/", "-")}-{i:03d}'
        description = (f'Active ingredient(s): {item["ingredient"]}. Registration: {item["registration"]}. '
                       f'Package: {item["pack"]}. Illustrative coursework price and stock; verify current offer with a pharmacy.')
        insert_ignore(cur, 'products', ('sku','name','description','image_url','image_source_url','category_id','manufacturer_id','prescription_required','storage_min_c','storage_max_c','is_active'),
                      (sku, item['name'][:200], description, item['image'], item['source'], category_ids[item['category']], manufacturer_ids[item['manufacturer']], item['rx'], item['storage_min'], item['storage_max'], True))
        product_ids.append(get_id(cur, 'products', 'sku', sku))

    inventory_ids, prices = [], []
    for i, product_id in enumerate(product_ids, 1):
        pharmacy_id = pharmacy_ids[(i-1)%len(pharmacy_ids)]
        price = (Decimal('55.00') + Decimal((i*17)%250) + Decimal('0.50')).quantize(Decimal('0.01'))
        # The final inventory balance reflects the historical fulfilled orders
        # below. Receipt movement records opening balance + fulfilled quantity.
        qty = 1 + i%3
        on_hand = 35 + (i*7)%60
        insert_ignore(cur, 'pharmacy_inventory', ('pharmacy_id','product_id','unit_price','on_hand','reserved','is_listed','updated_at','version'),
                      (pharmacy_id, product_id, price, on_hand, 0, True, NOW, 1))
        cur.execute('SELECT id,unit_price,on_hand FROM pharmacy_inventory WHERE pharmacy_id=%s AND product_id=%s', (pharmacy_id, product_id))
        inventory_id, price, on_hand = cur.fetchone(); inventory_ids.append(inventory_id); prices.append(Decimal(price))
        movement_key = f'CW-OPENING-{inventory_id}'
        cur.execute("SELECT id FROM inventory_movements WHERE reference_type='CW_SEED' AND reference_id=%s AND reason='RECEIPT'", (inventory_id,))
        if not cur.fetchone():
            insert_ignore(cur, 'inventory_movements', ('inventory_id','delta_on_hand','reason','reference_type','reference_id','performed_by_id','created_at'),
                          (inventory_id, int(on_hand)+qty, 'RECEIPT', 'CW_SEED', inventory_id, staff_ids[(i-1)%len(staff_ids)], NOW-timedelta(days=45-i%30)))
        cur.execute('SELECT id FROM carts WHERE customer_id=%s', (customer_ids[(i-1)%CUSTOMERS],)); cart_id = cur.fetchone()[0]
        insert_ignore(cur, 'cart_items', ('cart_id','product_id','quantity'), (cart_id, product_id, qty))

    promotion_ids = []
    for i in range(1, 51):
        code = f'CW-HEALTH-{i:03d}'
        rate = Decimal(5 + i%11) / Decimal(100)
        insert_ignore(cur, 'promotions', ('code','description','discount_rate','starts_at','ends_at','is_active'),
                      (code, f'Coursework sample promotion {i:03d}', rate, NOW-timedelta(days=30), NOW+timedelta(days=335+i), True))
        promotion_id = get_id(cur, 'promotions', 'code', code); promotion_ids.append(promotion_id)
        insert_ignore(cur, 'promotion_products', ('promotion_id','product_id'), (promotion_id, product_ids[(i-1)%50]))

    order_ids, order_item_ids, payment_ids, rx_order_ids = [], [], [], []
    methods = ['PICKUP','COURIER','POSTAL']
    pay_methods = ['CARD','BANK_TRANSFER','CASH_ON_DELIVERY','ONLINE_GATEWAY']
    providers = ['CARD_PROCESSOR','BANK_TRANSFER','CASH_ON_DELIVERY','PAYMENT_GATEWAY']
    for i in range(1, 51):
        product_index = i-1; customer_id = customer_ids[product_index]; pharmacy_id = pharmacy_ids[product_index%len(pharmacy_ids)]
        qty = 1 + i%3; subtotal = (prices[product_index] * qty).quantize(Decimal('0.01'))
        discount = (subtotal * Decimal(5+i%11)/Decimal(100)).quantize(Decimal('0.01'))
        method = methods[(i-1)%3]
        shipping = Decimal('0.00') if method == 'PICKUP' else Decimal('55.00') if method == 'COURIER' else Decimal('75.00')
        total = subtotal-discount+shipping
        created = NOW-timedelta(days=25-i%25, hours=i%12)
        order_number = f'CW-{NOW.year}-{i:05d}'
        insert_ignore(cur, 'orders', ('order_number','customer_id','pharmacy_id','status','fulfillment_method','payment_method','subtotal','discount_total','shipping_total','grand_total','currency','created_at','updated_at'),
                      (order_number, customer_id, pharmacy_id, 'COMPLETED', method, pay_methods[(i-1)%4], subtotal, discount, shipping, total, 'UAH', created, created+timedelta(hours=2)))
        order_id = get_id(cur, 'orders', 'order_number', order_number); order_ids.append(order_id)
        # Reuse the persisted timestamp on replays so every dependent history
        # row resolves to the same deterministic key/check.
        cur.execute('SELECT created_at FROM orders WHERE id=%s', (order_id,))
        created = cur.fetchone()[0]
        product_id, inventory_id = product_ids[product_index], inventory_ids[product_index]
        cur.execute('SELECT id FROM order_items WHERE order_id=%s AND product_id=%s', (order_id, product_id)); row = cur.fetchone()
        if row:
            order_item_id = row[0]
        else:
            insert_ignore(cur, 'order_items', ('order_id','product_id','product_name_snapshot','unit_price_snapshot','quantity','line_total'),
                          (order_id, product_id, products[product_index]['name'][:200], prices[product_index], qty, subtotal))
            cur.execute('SELECT id FROM order_items WHERE order_id=%s AND product_id=%s', (order_id, product_id)); order_item_id = cur.fetchone()[0]
        order_item_ids.append(order_item_id)
        insert_ignore(cur, 'reservations', ('order_item_id','inventory_id','quantity','status','expires_at','created_at'),
                      (order_item_id, inventory_id, qty, 'FULFILLED', created+timedelta(minutes=15), created))
        provider = providers[(i-1)%4]
        payment_key = f'cw-charge-{NOW.year}-{i:05d}'
        payment_status = 'REFUNDED' if i%5==0 else 'SUCCEEDED'
        insert_ignore(cur, 'payments', ('order_id','provider','status','amount','currency','idempotency_key','provider_reference','created_at','updated_at'),
                      (order_id, provider, payment_status, total, 'UAH', payment_key, f'CW-PAY-{NOW.year}-{i:05d}', created+timedelta(minutes=1), created+timedelta(minutes=2)))
        cur.execute('SELECT id FROM payments WHERE idempotency_key=%s', (payment_key,)); payment_id=cur.fetchone()[0]; payment_ids.append(payment_id)
        cur.execute('SELECT id FROM refunds WHERE payment_id=%s', (payment_id,))
        if not cur.fetchone():
            refund_status = 'SUCCEEDED' if i%5==0 else 'PENDING'
            refund_amount = total if i%5==0 else max(Decimal('1.00'), (total*Decimal('0.10')).quantize(Decimal('0.01')))
            insert_ignore(cur, 'refunds', ('payment_id','amount','status','reason','created_at'),
                          (payment_id, refund_amount, refund_status, 'Simulated coursework refund workflow', created+timedelta(days=2)))
        cur.execute('SELECT id FROM deliveries WHERE order_id=%s', (order_id,))
        if not cur.fetchone():
            delivery_status = 'PICKED_UP' if method=='PICKUP' else 'DELIVERED'
            insert_ignore(cur, 'deliveries', ('order_id','method','recipient_name','recipient_phone','destination','provider','status','tracking_reference','created_at'),
                          (order_id, method, f'Coursework Customer {i:03d}', f'+3800002{i:04d}', f'{cities[(i-1)%len(cities)]}, {streets[(i-1)%len(streets)]} {10+i}', 'COURSEWORK_SIMULATOR', delivery_status, None if method=='PICKUP' else f'CW-TRACK-{NOW.year}-{i:05d}', created+timedelta(hours=1)))
        tier_code = ['STANDARD','SOCIAL','PREMIUM'][(i-1)%3]
        insert_ignore(cur, 'loyalty_accounts', ('customer_id','tier_id','balance'), (customer_id, tier_ids[tier_code], 100+i*9))
        cur.execute('SELECT id FROM loyalty_accounts WHERE customer_id=%s', (customer_id,)); account_id=cur.fetchone()[0]
        event_key=f'CW-LOYALTY-{i:05d}'
        insert_ignore(cur, 'loyalty_transactions', ('account_id','order_id','points_delta','type','event_key','created_at'),
                      (account_id, order_id, max(1, int(total//100)), 'EARN', event_key, created+timedelta(hours=2)))
        event_id=f'00000000-0000-4000-8000-{i:012d}'
        payload=json.dumps({'order_id':order_id,'order_number':order_number,'status':'COMPLETED','source':'coursework'},separators=(',',':'))
        insert_ignore(cur, 'outbox_events', ('event_id','event_type','payload','status','attempts','available_at','created_at'),
                      (event_id,'order.completed',payload,'DONE',1,created,created))
        cur.execute('SELECT id FROM notifications WHERE user_id=%s AND type=%s AND title=%s AND created_at=%s',
                    (customer_id,'ORDER','Coursework order completed',created+timedelta(hours=2)))
        if not cur.fetchone():
            insert_ignore(cur, 'notifications', ('user_id','type','title','body','created_at'),
                          (customer_id,'ORDER','Coursework order completed',f'Simulated order {order_number} was completed.',created+timedelta(hours=2)))
        cur.execute('SELECT id FROM audit_entries WHERE actor_id=%s AND action=%s AND target_type=%s AND target_id=%s AND occurred_at=%s',
                    (staff_ids[(i-1)%STAFF],'ORDER_COMPLETED','order',order_id,created+timedelta(hours=2)))
        if not cur.fetchone():
            insert_ignore(cur, 'audit_entries', ('actor_id','action','target_type','target_id','occurred_at','details'),
                          (staff_ids[(i-1)%STAFF],'ORDER_COMPLETED','order',order_id,created+timedelta(hours=2),json.dumps({'order_number':order_number,'source':'coursework'},separators=(',',':'))))
        reminder_product = product_ids[(i-1)%50]
        cur.execute('SELECT id FROM reminders WHERE customer_id=%s AND product_id=%s AND next_run_at=%s', (customer_id, reminder_product, created+timedelta(days=30)))
        if not cur.fetchone():
            insert_ignore(cur, 'reminders', ('customer_id','product_id','next_run_at','interval_days','is_active'), (customer_id,reminder_product,created+timedelta(days=30),30,True))
        sub_product = product_ids[i%50]
        insert_ignore(cur, 'availability_subscriptions', ('customer_id','product_id','pharmacy_id','is_active'), (customer_id,sub_product,pharmacy_id,True))
        rx = products[product_index]['rx']
        if rx:
            rx_order_ids.append((order_id,staff_ids[(i-1)%STAFF],created))
        cur.execute('SELECT id FROM prescription_records WHERE masked_reference=%s', (f'CW-RX-{i:05d}',))
        if not cur.fetchone():
            insert_ignore(cur, 'prescription_records', ('customer_id','display_label','masked_reference','is_demo','created_at'),
                          (customer_id,'Coursework prescription workflow label',f'CW-RX-{i:05d}',True,created-timedelta(days=3)))
        fulfillment_key=f'CW-FULFILLED-{order_item_id}'
        cur.execute("SELECT id FROM inventory_movements WHERE reference_type='CW_SEED' AND reference_id=%s AND reason='FULFILLMENT'", (order_item_id,))
        if not cur.fetchone():
            insert_ignore(cur, 'inventory_movements', ('inventory_id','delta_on_hand','reason','reference_type','reference_id','performed_by_id','created_at'),
                          (inventory_id,-qty,'FULFILLMENT','CW_SEED',order_item_id,staff_ids[(i-1)%STAFF],created+timedelta(hours=1)))

    # Repeated demo checks model correction/review history for Rx orders; they
    # never represent a real or legally valid prescription.
    if rx_order_ids:
        for attempt in range(50):
            order_id, staff_id, created = rx_order_ids[attempt % len(rx_order_ids)]
            checked = created + timedelta(minutes=attempt+1)
            # Last check for each Rx order is approved; earlier entries model
            # a corrected/reviewed history without leaving completed orders rejected.
            is_last_for_order = attempt >= len(rx_order_ids) * 2
            status = 'APPROVED' if is_last_for_order or (attempt+1) % 3 == 0 else 'REJECTED'
            note = 'Coursework simulation only; no valid prescription was reviewed.'
            cur.execute('SELECT id FROM prescription_verifications WHERE order_id=%s AND checked_by_id=%s AND checked_at=%s', (order_id,staff_id,checked))
            if not cur.fetchone():
                insert_ignore(cur, 'prescription_verifications', ('order_id','checked_by_id','status','is_demo','checked_at','note'),
                              (order_id,staff_id,status,True,checked,note))

    # Delivery rules are configuration records, not orders. Add distinct,
    # non-overlapping temperature bands to reach 50 without deleting existing rules.
    cur.execute('SELECT COUNT(*) FROM delivery_rules'); delivery_count=cur.fetchone()[0]
    i = 0
    while delivery_count < 50 and i < 5000:
        method = ['PICKUP','COURIER','POSTAL'][i%3]
        low = (Decimal('1.0') + Decimal(i)*Decimal('0.1')).quantize(Decimal('0.01'))
        high = low + Decimal('4.00')
        values=(method,True,True,True,low,high)
        cur.execute('SELECT id FROM delivery_rules WHERE method=%s AND requires_cold_chain=%s AND cold_chain_supported=%s AND enabled=%s AND max_storage_min_c=%s AND min_storage_max_c=%s', values)
        if not cur.fetchone():
            insert_ignore(cur, 'delivery_rules', ('method','requires_cold_chain','cold_chain_supported','enabled','max_storage_min_c','min_storage_max_c'), values)
            delivery_count += 1
        i += 1
    if delivery_count < 50:
        raise RuntimeError('Could not add enough distinct delivery_rules to reach 50')

    return products


def main() -> int:
    print(
        'This legacy coursework dataset is disabled to prevent placeholder records '
        'from returning. Use db/scripts/seed_storefront_branches.py for the '
        'reviewed storefront dataset.'
    )
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
