#!/usr/bin/env python3
"""Replace business rows with synthetic fixtures and registered Ukrainian medicines."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from migrate import ROOT, connect, load_env_file

N = 25
NOW = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

CITIES = [
    'Kyiv', 'Lviv', 'Odesa', 'Dnipro', 'Kharkiv', 'Vinnytsia', 'Poltava',
    'Cherkasy', 'Zhytomyr', 'Rivne', 'Ternopil', 'Lutsk', 'Uzhhorod',
    'Ivano-Frankivsk', 'Chernivtsi', 'Kropyvnytskyi', 'Sumy', 'Chernihiv',
    'Mykolaiv', 'Zaporizhzhia', 'Khmelnytskyi', 'Bila Tserkva', 'Brovary',
    'Kremenchuk', 'Kamianets-Podilskyi',
]
STREET_NAMES = ['Shevchenka Avenue', 'Central Street', 'Soborna Street', 'Parkova Street', 'Myrna Street']
FIRST_NAMES = [
    'Olena', 'Andrii', 'Iryna', 'Maksym', 'Natalia', 'Dmytro', 'Sofiia', 'Bohdan',
    'Kateryna', 'Roman', 'Yuliia', 'Taras', 'Oksana', 'Mykhailo', 'Viktoriia',
    'Oleh', 'Anastasiia', 'Denys', 'Mariia', 'Ivan', 'Tetiana', 'Pavlo', 'Alina',
    'Serhii', 'Larysa',
]
LAST_NAMES = [
    'Kovalenko', 'Melnyk', 'Shevchenko', 'Bondarenko', 'Tkachenko', 'Koval',
    'Moroz', 'Boyko', 'Kravchenko', 'Oliinyk', 'Lysenko', 'Rudenko', 'Polishchuk',
    'Savchenko', 'Marchenko', 'Klymenko', 'Pavlenko', 'Hrytsenko', 'Tkachuk',
    'Kozak', 'Danyliuk', 'Romanenko', 'Kushnir', 'Bilyk', 'Ponomarenko',
]
CATEGORY_NAMES = [
    'Anti-infectives', 'Cardiovascular care', 'Endocrine care', 'Respiratory care',
    'Digestive health', 'Allergy care', 'Pain management', 'Dermatology',
    'Neurology', 'Ophthalmology', 'Urology', 'Women’s health', 'Men’s health',
    'Vitamins and minerals', 'Immunology', 'Rheumatology', 'Hematology',
    'Oncology support', 'ENT care', 'Diabetes care', 'Wound care', 'Anesthesia',
    'Vaccines', 'Renal care', 'Pediatric care',
]
# Manufacturer names and registered product names are transcribed from Ukraine's
# State Register of Medicinal Products. Product packages/prices/stock remain fixtures.
MANUFACTURERS = [
    'КУСУМ ХЕЛТХКЕР ПВТ ЛТД', 'Лабораторії Серв\'є Індастрі',
    'ПрАТ "Фармацевтична фірма "Дарниця"', 'Салютас Фарма ГмбХ',
    'ПрАТ Фармацевтична фабрика "Віола"',
    'ТОВ "КОРПОРАЦІЯ "ЗДОРОВ’Я"', 'Меркле ГмбХ', 'АТ "Лубнифарм"',
    'ПАТ "Галичфарм"', 'Сперко Україна', 'МЕДЛЕВ', 'Ментолатум Компані Лімітед',
    'Фарева Амбуаз', 'Фармацевтична компанія "Здоров’я"', 'АТ "ВІТАМІНИ"',
    'АТ "Фармак"', 'Мепро Фармасьютикалс Пріват Лімітед',
    'ПАТ "Київмедпрепарат"', 'Юнік Фармасьютикал Лабораторіз',
    'Дж. Б. Кемікалз енд Фармасьютикалз Лтд.',
    'БАВ ІНСТИТУТ гігієни та забезпечення якості ГмбХ', 'АТ "Стома"',
    'Абботт Біолоджікалз Б.В.', 'ТОВ "Тернофарм"', 'Наброс Фарма Пвт Лтд.',
]
PRODUCTS = [
    ('ДЕРМАЗОЛ®', 'Кетоконазол', False, None, None, 'UA/6725/01/01', 0),
    ('ДЕРМАЗОЛ® ПЛЮС', 'Піритіон цинк; кетоконазол', False, None, None, 'UA/7632/01/01', 0),
    ('ДЕТРАЛЕКС®', 'Мікронізована очищена флавонова фракція', False, None, None, 'UA/4329/01/01', 1),
    ('ДЕТРАЛЕКС® 1000 МГ', 'Мікронізована очищена флавонова фракція', False, None, None, 'UA/4329/01/02', 1),
    ('ДИБАЗОЛ-ДАРНИЦЯ', 'Бендазолу гідрохлорид', False, None, None, 'UA/4780/02/01', 2),
    ('ДИКЛАК® ЛІПОГЕЛЬ', 'Диклофенак натрій', False, None, None, 'UA/0981/02/01', 3),
    ('ДИКЛОФЕНАК-ВІОЛА', 'Диклофенак натрій', False, None, None, 'UA/7167/01/01', 4),
    ("ДИКЛОФЕНАК-ЗДОРОВ'Я", 'Диклофенак натрій', False, None, None, 'UA/1539/01/01', 5),
    ('ДИКЛОФЕНАК-ЗДОРОВ’Я УЛЬТРА', 'Диклофенак натрій', False, None, None, 'UA/1539/01/03', 5),
    ("ДИКЛОФЕНАК-ЗДОРОВ'Я ФОРТЕ", 'Диклофенак натрій', False, None, None, 'UA/1539/01/02', 5),
    ('ДИКЛОФЕНАК-ТЕВА ФОРТЕ 2 %', 'Диклофенак натрій', False, None, None, 'UA/19275/01/01', 6),
    ('ДИМЕКСИД', 'Диметилу сульфоксид', False, None, None, 'UA/9117/01/01', 7),
    ('ДИМЕКСИД® АРТЕРІУМ', 'Диметилу сульфоксид', False, None, None, 'UA/4522/01/01', 8),
    ('ДИМЕКСИД-ЛУБНИФАРМ', 'Диметилу сульфоксид', False, None, None, 'UA/19735/01/01', 7),
    ('ДИП ХІТ', 'Терпентинова олія; евкаліптова олія; метилсаліцилат; ментол', False, None, None, 'UA/1453/01/01', 11),
    ('ДИФЛЮКАН®', 'Флуконазол', True, None, None, 'UA/5970/02/03', 12),
    ("ДІАГНОСТИН-ЗДОРОВ'Я", 'Макрогол 3350; електроліти', False, None, None, 'UA/15448/01/01', 13),
    ('ДІАЗОЛІН-ДАРНИЦЯ', 'Мебгідролін', False, None, None, 'UA/0278/01/01', 2),
    ('ДІАЗОЛІН-СБ-ФАРМА', 'Мебгідролін', False, None, None, 'UA/20097/01/02', 14),
    ('ДІАЗОЛІН®', 'Мебгідролін', False, None, None, 'UA/0270/02/01', 15),
    ('ДІАРЕМІКС', 'Bacillus coagulans; дицикловерин; лопераміду гідрохлорид', False, None, None, 'UA/8224/01/01', 16),
    ("ДІОСМЕКТИТ-ЗДОРОВ'Я", 'Діосмектит', False, None, None, 'UA/17181/01/01', 5),
    ('ДІОФЛАН®', 'Гесперидин; діосмін', False, None, None, 'UA/10773/01/01', 17),
    ('ДОКТОР МОМ®', 'Ментол; олії; камфора; тимол', False, None, None, 'UA/7868/01/01', 18),
    ('ДОЛГІТ® ГЕЛЬ', 'Ібупрофен', False, None, None, 'UA/4117/02/01', 20),
]
# Product category indexes refer to CATEGORY_NAMES above and group all 25
# catalog items according to their principal therapeutic use.
CATEGORY_INDEX_BY_PRODUCT = [7, 7, 1, 1, 1, 6, 6, 6, 6, 6, 6, 7, 7, 7, 6, 0, 4, 5, 5, 5, 4, 4, 1, 3, 6]
PROMOTION_CODES = [
    'WELCOME10', 'HEALTH5', 'FAMILY12', 'CARE15', 'AUTUMN8', 'WELLNESS10',
    'LOYALTY7', 'DELIVERY5', 'VITAMIN10', 'RESPIRATORY8', 'CARDIOCARE6',
    'DIABETES12', 'ALLERGY7', 'SKINCARE9', 'DIGESTIVE5', 'SPRING10',
    'MEMBER8', 'PHARMACY12', 'PREVENTION6', 'HEALTHY15', 'WEEKEND5',
    'REFILL10', 'CAREPLUS7', 'COMMUNITY9', 'EVERYDAY6',
]
PAYMENT_PROVIDERS = ['CARD_PROCESSOR', 'BANK_TRANSFER', 'CASH_ON_DELIVERY', 'PAYMENT_GATEWAY']
PAYMENT_METHODS = ['CARD', 'BANK_TRANSFER', 'CASH_ON_DELIVERY', 'ONLINE_GATEWAY']
FULFILLMENT_METHODS = ['PICKUP', 'COURIER', 'POSTAL']


def ins(cur, table: str, columns: tuple[str, ...], values: tuple):
    marks = ','.join(['%s'] * len(columns))
    cur.execute(f"INSERT INTO `{table}` ({','.join(f'`{x}`' for x in columns)}) VALUES ({marks})", values)
    return cur.lastrowid


def insert_rows(cur, table: str, columns: tuple[str, ...], rows: list[tuple]):
    return [ins(cur, table, columns, row) for row in rows]


def clear_learning_tables(cur) -> None:
    # Child-first deletion; schema_migrations is intentionally preserved.
    order = [
        'audit_entries', 'outbox_events', 'notifications', 'availability_subscriptions',
        'reminders', 'notification_preferences', 'loyalty_transactions', 'refunds',
        'payments', 'deliveries', 'prescription_verifications', 'prescription_records',
        'reservations', 'order_items', 'cart_items', 'inventory_movements',
        'loyalty_accounts', 'carts', 'orders', 'employee_assignments', 'customer_profiles',
        'pharmacy_inventory', 'promotion_products', 'products', 'promotions',
        'delivery_rules', 'categories', 'manufacturers', 'loyalty_tiers', 'pharmacies', 'users',
    ]
    for table in order:
        cur.execute(f'DELETE FROM `{table}`')


def populate(cur) -> dict[str, int]:
    counts: dict[str, int] = {}
    pharmacies = insert_rows(cur, 'pharmacies',
        ('code','name','address','city','phone','is_active'), [
            (f'PH-UA-{i+1:03d}', f'Health Point Pharmacy {i+1:02d}',
             f'{STREET_NAMES[i % len(STREET_NAMES)]}, {10+i}', CITIES[i],
             f'+38000001{i+1:04d}', True) for i in range(N)])
    counts['pharmacies'] = len(pharmacies)

    categories = insert_rows(cur, 'categories', ('name',), [(n,) for n in CATEGORY_NAMES])
    manufacturers = insert_rows(cur, 'manufacturers', ('name',), [(n,) for n in MANUFACTURERS])
    counts['categories'] = len(categories); counts['manufacturers'] = len(manufacturers)

    tiers = insert_rows(cur, 'loyalty_tiers', ('code','bonus_rate','discount_rate'), [
        ('STANDARD', Decimal('0.0100'), Decimal('0.0000')),
        ('SOCIAL', Decimal('0.0250'), Decimal('0.0300')),
        ('PREMIUM', Decimal('0.0500'), Decimal('0.0700')),
    ])
    counts['loyalty_tiers'] = len(tiers)

    users = []
    customers = []
    staff = []
    cart_ids = []
    account_ids = []
    for i in range(N):
        name = f'{FIRST_NAMES[i]} {LAST_NAMES[i]}'
        uid = ins(cur, 'users', ('username','email','password','role','is_active','is_staff','created_at'),
                  (f'customer{i+1:03d}', f'customer{i+1:03d}@example.test', '!', 'CUSTOMER', True, False, NOW-timedelta(days=90-i)))
        users.append(uid); customers.append(uid)
        ins(cur, 'customer_profiles', ('user_id','phone','full_name','preferred_pharmacy_id'),
            (uid, f'+38000002{i+1:04d}', name, pharmacies[i]))
        ins(cur, 'carts', ('customer_id','updated_at'), (uid, NOW-timedelta(days=i%12)))
        cart_ids.append(cur.lastrowid)
        ins(cur, 'notification_preferences', ('user_id','promotions_enabled','reminders_enabled'), (uid, i%2==0, True))
        account_ids.append(ins(cur, 'loyalty_accounts', ('customer_id','tier_id','balance'), (uid, tiers[i % len(tiers)], 120+i*15)))

    for i in range(N):
        name = f'{FIRST_NAMES[(i+7)%N]} {LAST_NAMES[(i+11)%N]}'
        uid = ins(cur, 'users', ('username','email','password','role','is_active','is_staff','created_at'),
                  (f'pharmacist{i+1:03d}', f'pharmacist{i+1:03d}@example.test', '!', 'STAFF', True, True, NOW-timedelta(days=180-i)))
        users.append(uid); staff.append(uid)
        ins(cur, 'employee_assignments', ('user_id','pharmacy_id','is_active','created_at'), (uid, pharmacies[i], True, NOW-timedelta(days=120-i)))
    counts['users'] = len(users)

    product_ids = []
    product_names = []
    for i,(name,ingredient,requires_rx,min_c,max_c,registration_no,manufacturer_index) in enumerate(PRODUCTS):
        pid = ins(cur, 'products', ('sku','name','description','category_id','manufacturer_id','prescription_required','storage_min_c','storage_max_c','is_active'),
            (registration_no.replace('/', '-'), name, f'Active ingredient(s): {ingredient}. Ukrainian State Register registration: {registration_no}. Package details are not represented in this learning fixture.', categories[CATEGORY_INDEX_BY_PRODUCT[i]], manufacturers[manufacturer_index], requires_rx, min_c, max_c, True))
        product_ids.append(pid); product_names.append(name)
    counts['products'] = len(product_ids)

    # All three checkout methods have rules; additional rows represent supported temperature bands.
    for i in range(N):
        method = FULFILLMENT_METHODS[i % len(FULFILLMENT_METHODS)]
        cold = (i % 2 == 0)
        supported = not (cold and i % 5 == 0)
        enabled = supported or not cold
        lo = Decimal(1 + (i % 4)) if cold and supported else None
        hi = Decimal(8) if cold and supported else None
        ins(cur, 'delivery_rules', ('method','requires_cold_chain','cold_chain_supported','enabled','max_storage_min_c','min_storage_max_c'),
            (method, cold, supported, enabled, lo, hi))
    counts['delivery_rules'] = N

    for i in range(N):
        rate = Decimal(5 + (i % 11)) / Decimal(100)
        promo_id = ins(cur, 'promotions', ('code','description','discount_rate','starts_at','ends_at','is_active'),
            (PROMOTION_CODES[i], f'{PROMOTION_CODES[i].replace("_", " ").title()} pharmacy offer', rate, NOW-timedelta(days=30), NOW+timedelta(days=335+i), True))
        ins(cur, 'promotion_products', ('promotion_id','product_id'), (promo_id, product_ids[i]))
    counts['promotions'] = N; counts['promotion_products'] = N

    inventory_ids = []
    prices = []
    for i in range(N):
        price = Decimal('85.00') + Decimal(i*17) + Decimal('0.50')
        qty = 1 + (i % 3)
        on_hand = 45 + i
        inventory_id = ins(cur, 'pharmacy_inventory', ('pharmacy_id','product_id','unit_price','on_hand','reserved','is_listed','updated_at','version'),
            (pharmacies[i], product_ids[i], price, on_hand, 0, True, NOW, 1))
        inventory_ids.append(inventory_id); prices.append(price)
        ins(cur, 'inventory_movements', ('inventory_id','delta_on_hand','reason','reference_type','reference_id','performed_by_id','created_at'),
            (inventory_id, on_hand, 'RECEIPT', 'OPENING_STOCK', None, staff[i], NOW-timedelta(days=45-i)))
        ins(cur, 'cart_items', ('cart_id','product_id','quantity'), (cart_ids[i], product_ids[i], qty))
    counts['pharmacy_inventory'] = N; counts['inventory_movements'] = N; counts['cart_items'] = N

    order_ids = []; item_ids = []; payment_ids = []; verified_prescription_orders = 0
    for i in range(N):
        qty = 1 + (i % 3)
        subtotal = prices[i] * qty
        discount = (subtotal * (Decimal(5 + i%11) / Decimal(100))).quantize(Decimal('0.01'))
        method = FULFILLMENT_METHODS[i % 3]
        shipping = Decimal('0.00') if method == 'PICKUP' else (Decimal('55.00') if method == 'COURIER' else Decimal('75.00'))
        total = subtotal - discount + shipping
        created = NOW-timedelta(days=25-i, hours=i%12)
        order_id = ins(cur, 'orders', ('order_number','customer_id','pharmacy_id','status','fulfillment_method','payment_method','subtotal','discount_total','shipping_total','grand_total','currency','created_at','updated_at'),
            (f'IP-{NOW.year}-{i+1:05d}', customers[i], pharmacies[i], 'COMPLETED', method, PAYMENT_METHODS[i%4], subtotal, discount, shipping, total, 'UAH', created, created+timedelta(hours=2)))
        order_ids.append(order_id)
        item_id = ins(cur, 'order_items', ('order_id','product_id','product_name_snapshot','unit_price_snapshot','quantity','line_total'),
            (order_id, product_ids[i], product_names[i], prices[i], qty, subtotal))
        item_ids.append(item_id)
        ins(cur, 'reservations', ('order_item_id','inventory_id','quantity','status','expires_at','created_at'),
            (item_id, inventory_ids[i], qty, 'FULFILLED', created+timedelta(minutes=15), created))
        provider = PAYMENT_PROVIDERS[i % len(PAYMENT_PROVIDERS)]
        payment_status = 'REFUNDED' if i < 8 else 'SUCCEEDED'
        payment_id = ins(cur, 'payments', ('order_id','provider','status','amount','currency','idempotency_key','provider_reference','failure_code','created_at','updated_at'),
            (order_id, provider, payment_status, total, 'UAH', f'learn-charge-{i+1:05d}', f'PAY-REF-{NOW.year}-{i+1:05d}', None, created+timedelta(minutes=1), created+timedelta(minutes=2)))
        payment_ids.append(payment_id)
        refund_status = 'SUCCEEDED' if i < 8 else ('PENDING' if i < 17 else 'FAILED')
        refund_amount = total if i < 8 else (total*Decimal('0.10')).quantize(Decimal('0.01'))
        ins(cur, 'refunds', ('payment_id','amount','status','reason','created_at'),
            (payment_id, refund_amount, refund_status, 'Customer return request' if i<8 else 'Price adjustment review', created+timedelta(days=2)))
        delivery_status = 'PICKED_UP' if method == 'PICKUP' else 'DELIVERED'
        ins(cur, 'deliveries', ('order_id','method','recipient_name','recipient_phone','destination','provider','status','tracking_reference','created_at'),
            (order_id, method, f'{FIRST_NAMES[i]} {LAST_NAMES[i]}', f'+38000002{i+1:04d}', f'{CITIES[i]}, {STREET_NAMES[i%5]} {10+i}', 'LOCAL_COURIER' if method=='COURIER' else ('NATIONAL_POST' if method=='POSTAL' else 'PHARMACY_COUNTER'), delivery_status, f'TRACK-{NOW.year}-{i+1:05d}' if method!='PICKUP' else None, created+timedelta(hours=1)))
        # Only product fixtures flagged as prescription-required get a verification row.
        if PRODUCTS[i][2]:
            ins(cur, 'prescription_verifications', ('order_id','checked_by_id','status','is_demo','checked_at','note'),
                (order_id, staff[i], 'APPROVED', True, created+timedelta(minutes=20), 'Synthetic learning record; not a valid prescription'))
            verified_prescription_orders += 1
        ins(cur, 'loyalty_transactions', ('account_id','order_id','points_delta','type','event_key','created_at'),
            (account_ids[i], order_id, max(1, int(total//100)), 'EARN', f'learn-points-{i+1:05d}', created+timedelta(hours=2)))
        event_type = 'order.completed'
        payload = json.dumps({'order_id': order_id, 'order_number': f'IP-{NOW.year}-{i+1:05d}', 'status': 'COMPLETED'}, separators=(',', ':'))
        cur.execute('INSERT INTO outbox_events (event_id,event_type,payload,status,attempts,available_at,locked_until,last_error,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (f'00000000-0000-4000-8000-{i+1:012d}', event_type, payload, 'DONE', 1, created, None, None, created))
        cur.execute('INSERT INTO audit_entries (actor_id,action,target_type,target_id,occurred_at,details) VALUES (%s,%s,%s,%s,%s,%s)',
            (staff[i], 'ORDER_COMPLETED', 'order', order_id, created+timedelta(hours=2), json.dumps({'order_number':f'IP-{NOW.year}-{i+1:05d}'}, separators=(',',':'))))
        ins(cur, 'notifications', ('user_id','type','title','body','read_at','created_at'),
            (customers[i], 'ORDER', 'Order completed', f'Order IP-{NOW.year}-{i+1:05d} has been completed.', created+timedelta(days=1) if i%2==0 else None, created+timedelta(hours=2)))
        ins(cur, 'reminders', ('customer_id','product_id','next_run_at','interval_days','is_active'),
            (customers[i], product_ids[i], created+timedelta(days=30), 30, True))
        ins(cur, 'availability_subscriptions', ('customer_id','product_id','pharmacy_id','is_active'),
            (customers[i], product_ids[(i+1)%N], pharmacies[i], True))
        ins(cur, 'prescription_records', ('customer_id','display_label','masked_reference','is_demo','created_at'),
            (customers[i], 'Electronic prescription reference', f'RX-EDU-{i+1:05d}', True, created-timedelta(days=3)))

    counts.update({'orders': N,'order_items': N,'reservations': N,'payments': N,'refunds': N,'deliveries': N,
                   'prescription_verifications': verified_prescription_orders,'loyalty_transactions': N,'outbox_events': N,'audit_entries': N,
                   'notifications': N,'reminders': N,'availability_subscriptions': N,'prescription_records': N,
                   'customer_profiles': N,'employee_assignments': N,'carts': N,'notification_preferences': N})
    return counts


def main() -> int:
    load_env_file(ROOT / '.env')
    conn = connect()
    cur = conn.cursor()
    try:
        conn.start_transaction()
        clear_learning_tables(cur)
        counts = populate(cur)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close(); conn.close()
    for table in sorted(counts):
        print(f'{table}: {counts[table]}')
    print('Learning dataset committed. All personal and prescription references are fictional; seeded accounts have unusable passwords.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
