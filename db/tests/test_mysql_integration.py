"""Focused integration checks; these tests require a real MySQL 8 server."""
from __future__ import annotations

import json
import os
import threading
import unittest
import uuid
from datetime import datetime, timedelta

import mysql.connector
from mysql.connector import DatabaseError, IntegrityError


def connect():
    db = mysql.connector.connect(
        host=os.environ.get('MYSQL_HOST', '127.0.0.1'),
        port=int(os.environ.get('MYSQL_PORT', '3306')),
        user=os.environ.get('MYSQL_USER', 'internet_pharmacy'),
        password=os.environ.get('MYSQL_PASSWORD', ''),
        database=os.environ.get('MYSQL_DATABASE', 'internet_pharmacy'),
        connection_timeout=10,
        autocommit=False,
    )
    cur = db.cursor()
    cur.execute("SET time_zone = '+00:00'")
    cur.close()
    return db


class MySQLSchemaIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tag = uuid.uuid4().hex[:12]
        self.conn = connect()
        self.order_ids: list[int] = []
        cur = self.conn.cursor()
        now = datetime.utcnow()
        cur.execute('INSERT INTO users(username,email,password,role,is_active,is_staff,created_at) VALUES (%s,%s,%s,\'CUSTOMER\',1,0,%s)', (f'test_{self.tag}', f'{self.tag}@example.invalid', '!', now))
        self.user_id = cur.lastrowid
        cur.execute('INSERT INTO pharmacies(code,name,address,city,is_active) VALUES (%s,%s,%s,%s,1)', (f'TEST-{self.tag}', 'Test pharmacy', '1 Test Road', 'Test City'))
        self.pharmacy_id = cur.lastrowid
        cur.execute('INSERT INTO categories(name) VALUES (%s)', (f'Test category {self.tag}',))
        self.category_id = cur.lastrowid
        cur.execute('INSERT INTO manufacturers(name) VALUES (%s)', (f'Test maker {self.tag}',))
        self.manufacturer_id = cur.lastrowid
        cur.execute('INSERT INTO products(sku,name,category_id,manufacturer_id,prescription_required,is_active) VALUES (%s,%s,%s,%s,0,1)', (f'TEST-{self.tag}', 'Test item', self.category_id, self.manufacturer_id))
        self.product_id = cur.lastrowid
        cur.execute('INSERT INTO pharmacy_inventory(pharmacy_id,product_id,unit_price,on_hand,reserved,is_listed,updated_at) VALUES (%s,%s,10.00,5,0,1,%s)', (self.pharmacy_id, self.product_id, now))
        self.inventory_id = cur.lastrowid
        self.order_item_ids = [self._make_order_item(cur, now)]
        self.conn.commit()
        cur.close()

    def _make_order_item(self, cur, now):
        cur.execute('INSERT INTO orders(order_number,customer_id,pharmacy_id,status,fulfillment_method,payment_method,subtotal,discount_total,shipping_total,grand_total,currency,created_at,updated_at) VALUES (%s,%s,%s,\'PENDING_CONFIRMATION\',\'PICKUP\',\'DEMO_CARD\',10.00,0.00,0.00,10.00,\'UAH\',%s,%s)', (f'{self.tag}-{len(self.order_ids)+1}', self.user_id, self.pharmacy_id, now, now))
        order_id = cur.lastrowid
        self.order_ids.append(order_id)
        cur.execute('INSERT INTO order_items(order_id,product_id,product_name_snapshot,unit_price_snapshot,quantity,line_total) VALUES (%s,%s,%s,10.00,1,10.00)', (order_id, self.product_id, 'Test item snapshot'))
        return cur.lastrowid

    def tearDown(self):
        cur = self.conn.cursor()
        cur.execute('DELETE FROM reservations WHERE order_item_id IN (SELECT id FROM order_items WHERE order_id IN (%s))' % ','.join(['%s'] * len(self.order_ids)), tuple(self.order_ids))
        cur.execute('DELETE FROM outbox_events WHERE event_type=%s', (f'test.{self.tag}',))
        cur.execute('DELETE FROM order_items WHERE order_id IN (%s)' % ','.join(['%s'] * len(self.order_ids)), tuple(self.order_ids))
        cur.execute('DELETE FROM orders WHERE id IN (%s)' % ','.join(['%s'] * len(self.order_ids)), tuple(self.order_ids))
        cur.execute('DELETE FROM inventory_movements WHERE inventory_id=%s', (self.inventory_id,))
        cur.execute('DELETE FROM pharmacy_inventory WHERE id=%s', (self.inventory_id,))
        cur.execute('DELETE FROM products WHERE id=%s', (self.product_id,))
        cur.execute('DELETE FROM categories WHERE id=%s', (self.category_id,))
        cur.execute('DELETE FROM manufacturers WHERE id=%s', (self.manufacturer_id,))
        cur.execute('DELETE FROM pharmacies WHERE id=%s', (self.pharmacy_id,))
        cur.execute('DELETE FROM users WHERE id=%s', (self.user_id,))
        self.conn.commit()
        cur.close()
        self.conn.close()

    def test_tables_are_innodb_utf8mb4(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*), SUM(engine='InnoDB'), SUM(table_collation LIKE 'utf8mb4%') FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE' AND table_name <> 'schema_migrations'")
        count, innodb, utf8mb4 = cur.fetchone()
        self.assertEqual(count, 31)
        self.assertEqual(innodb, count)
        self.assertEqual(utf8mb4, count)
        cur.close()

    def test_foreign_key_and_unique_constraints(self):
        cur = self.conn.cursor()
        with self.assertRaises(IntegrityError):
            cur.execute('INSERT INTO pharmacy_inventory(pharmacy_id,product_id,unit_price,on_hand,reserved,is_listed,updated_at) VALUES (%s,999999999,1.00,1,0,1,UTC_TIMESTAMP(6))', (self.pharmacy_id,))
        self.conn.rollback()
        with self.assertRaises(IntegrityError):
            cur.execute('INSERT INTO pharmacy_inventory(pharmacy_id,product_id,unit_price,on_hand,reserved,is_listed,updated_at) VALUES (%s,%s,1.00,1,0,1,UTC_TIMESTAMP(6))', (self.pharmacy_id, self.product_id))
        self.conn.rollback()
        cur.close()

    def test_check_constraints_reject_invalid_rows(self):
        cur = self.conn.cursor()
        with self.assertRaises(DatabaseError):
            cur.execute('UPDATE pharmacy_inventory SET reserved=on_hand+1 WHERE id=%s', (self.inventory_id,))
        self.conn.rollback()
        with self.assertRaises(DatabaseError):
            cur.execute('UPDATE pharmacy_inventory SET unit_price=-1.00 WHERE id=%s', (self.inventory_id,))
        self.conn.rollback()
        cur.close()

    def test_commit_and_rollback(self):
        cur = self.conn.cursor()
        cur.execute('UPDATE pharmacy_inventory SET reserved=reserved+1 WHERE id=%s', (self.inventory_id,))
        self.conn.commit()
        cur.execute('SELECT reserved FROM pharmacy_inventory WHERE id=%s', (self.inventory_id,))
        self.assertEqual(cur.fetchone()[0], 1)
        cur.execute('UPDATE pharmacy_inventory SET reserved=reserved+2 WHERE id=%s', (self.inventory_id,))
        self.conn.rollback()
        cur.execute('SELECT reserved FROM pharmacy_inventory WHERE id=%s', (self.inventory_id,))
        self.assertEqual(cur.fetchone()[0], 1)
        cur.close()

    def test_outbox_row_persists(self):
        event_id = str(uuid.uuid4())
        cur = self.conn.cursor()
        cur.execute('INSERT INTO outbox_events(event_id,event_type,payload,status,attempts,available_at,created_at) VALUES (%s,%s,%s,\'PENDING\',0,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))', (event_id, f'test.{self.tag}', json.dumps({'synthetic': True})))
        self.conn.commit()
        cur.execute('SELECT status,payload FROM outbox_events WHERE event_id=%s', (event_id,))
        row = cur.fetchone()
        self.assertEqual(row[0], 'PENDING')
        self.assertTrue(json.loads(row[1])['synthetic'])
        cur.close()

    def test_concurrent_reservations_do_not_oversell(self):
        setup = self.conn.cursor()
        second_item_id = self._make_order_item(setup, datetime.utcnow())
        self.order_item_ids.append(second_item_id)
        self.conn.commit()
        setup.close()
        barrier = threading.Barrier(2)
        outcomes: list[bool] = []
        errors: list[Exception] = []

        def reserve(item_id: int):
            db = connect()
            try:
                cur = db.cursor()
                barrier.wait(timeout=10)
                cur.execute('UPDATE pharmacy_inventory SET reserved=reserved+4, version=version+1, updated_at=UTC_TIMESTAMP(6) WHERE id=%s AND is_listed=1 AND on_hand-reserved >= 4', (self.inventory_id,))
                if cur.rowcount != 1:
                    db.rollback()
                    outcomes.append(False)
                    return
                cur.execute('INSERT INTO reservations(order_item_id,inventory_id,quantity,status,expires_at,created_at) VALUES (%s,%s,4,\'ACTIVE\',%s,%s)', (item_id, self.inventory_id, datetime.utcnow()+timedelta(minutes=10), datetime.utcnow()))
                db.commit()
                outcomes.append(True)
            except Exception as exc:  # surfaced after both workers join
                db.rollback()
                errors.append(exc)
            finally:
                db.close()

        workers = [threading.Thread(target=reserve, args=(item_id,)) for item_id in self.order_item_ids]
        for worker in workers: worker.start()
        for worker in workers: worker.join(timeout=20)
        self.assertFalse(any(worker.is_alive() for worker in workers), 'reservation worker timed out')
        self.assertEqual(errors, [])
        self.assertCountEqual(outcomes, [True, False])
        cur = self.conn.cursor()
        cur.execute('SELECT reserved FROM pharmacy_inventory WHERE id=%s', (self.inventory_id,))
        self.assertEqual(cur.fetchone()[0], 4)
        cur.execute('SELECT COUNT(*) FROM reservations WHERE inventory_id=%s AND status=\'ACTIVE\'', (self.inventory_id,))
        self.assertEqual(cur.fetchone()[0], 1)
        cur.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
