#!/usr/bin/env python3
"""Replace placeholder public branch/catalog data with sourced storefront records.

The script never deletes rows. It preserves product, pharmacy, order, and inventory
identifiers, hides retired catalog rows, and appends missing branch stock. Run
without --apply to review the exact target summary first.
"""
from __future__ import annotations

import argparse
import json
import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from migrate import ROOT, connect, load_env_file

BRANCH_FILE = ROOT / "db" / "data" / "anc_branches.json"
STOCKED_PRODUCT_IDS = {
    *range(90, 115),  # 25 commercial package variants
    65, 67, 69, 70, 80,
}
OUT_OF_STOCK_PRODUCT_IDS = {66, 68, 87, 88, 89}
ACTIVE_PRODUCT_IDS = STOCKED_PRODUCT_IDS | OUT_OF_STOCK_PRODUCT_IDS
ARCHIVE_NAMES = {
    1: ("ARCHIVE-PRODUCT-001", "Архівний аптечний товар №1"),
    2: ("ARCHIVE-PRODUCT-002", "Архівний аптечний товар №2"),
    3: ("ARCHIVE-PRODUCT-003", "Архівний аптечний товар №3"),
}
PHOTO_OVERRIDES = {
    69: (
        "https://admin.darnytsia.ua/sites/default/files/2024-12/dibazol-darnitsa_tabs_20mg_no10_folga_out_1200x1200_0.jpg?itok=xK6WyWmG",
        "https://darnytsia.ua/catalog/dibazol-darnitsya",
    ),
    94: (
        "https://i.podorozhnyk.com/products/d46996b3-9720-4c7e-8676-ab2e151ddeb7.webp",
        "https://podorozhnyk.ua/nurofen-kold-flyu-tabl-p-pl-ob-200mg-5mg-12/",
    ),
    99: (
        "https://www.add.ua/media/catalog/product/cache/74c1057f7991b4edb2bc7bdaa94de933/n/o/no-spa_forte_10_03_png.webp",
        "https://www.add.ua/no-shpa-forte-tabletki-80-mg-10.html",
    ),
    102: (
        "https://www.add.ua/media/catalog/product/cache/74c1057f7991b4edb2bc7bdaa94de933/7/6/768.png",
        "https://www.add.ua/panadol-bebi-100ml.html",
    ),
    108: (
        "https://apteka911.ua/content/shop/products/41977/photos/174132-41977-big-1500x1500-e74e.jpg",
        "https://apteka911.ua/ua/shop/lineks-bebi-por-d-oral-susp-paket-1-5g-10-p41977",
    ),
    87: (
        "https://storage.googleapis.com/static-storage/products/images/v2z/61694_3.jpg",
        "https://anc.ua/ru/item/dioflan-tabletki-vkriti-plivkovoyu-obolonkoyu-500-mg-blister-60-61694",
    ),
    88: (
        "https://online-apteka.com.ua/assets/images/products/129257/doktor-mom-syrop-fl-150ml-1.jpg",
        "https://online-apteka.com.ua/doktor-mom-sirop-fl-150ml.html",
    ),
    89: (
        "https://storage.googleapis.com/static-storage/products/images/v2z/41202_2.jpg",
        "https://anc.ua/ru/item/dolgit-gel-tuba-100-g-41202",
    ),
}


def rounded(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--apply", action="store_true", help="commit the reviewed updates")
    args = parser.parse_args()
    load_env_file(args.env_file)
    if os.getenv("MYSQL_DATABASE", "internet_pharmacy") != "internet_pharmacy":
        raise SystemExit("Refusing to target a database other than internet_pharmacy.")
    branches = json.loads(BRANCH_FILE.read_text(encoding="utf-8"))
    if len(branches) != 50 or len({b["code"] for b in branches}) != 50:
        raise SystemExit("Expected 50 distinct, source-attributed pharmacy branches.")
    if len(STOCKED_PRODUCT_IDS) != 30 or len(OUT_OF_STOCK_PRODUCT_IDS) != 5:
        raise SystemExit("The storefront must have exactly 30 stocked and 5 unavailable products.")

    conn = connect()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id,code,name,address,city FROM pharmacies ORDER BY id")
        pharmacies = cur.fetchall()
        cur.execute("SELECT id,sku,name,is_active FROM products ORDER BY id")
        products = cur.fetchall()
        if len(pharmacies) != 50:
            raise SystemExit(f"Expected 50 existing pharmacy rows, found {len(pharmacies)}.")
        found_ids = {int(p["id"]) for p in products}
        if not ACTIVE_PRODUCT_IDS <= found_ids:
            raise SystemExit(f"Missing required existing product IDs: {sorted(ACTIVE_PRODUCT_IDS - found_ids)}")
        if len({int(p["id"]) for p in pharmacies}) != 50:
            raise SystemExit("Pharmacy identifiers are not unique.")
        cur.execute("SELECT COUNT(*) AS count FROM orders")
        order_count = cur.fetchone()["count"]
        cur.execute("SELECT COUNT(*) AS count FROM pharmacy_inventory")
        before_inventory = cur.fetchone()["count"]
        print(f"Target database: {os.getenv('MYSQL_DATABASE', 'internet_pharmacy')}")
        print(f"Existing rows preserved: {len(pharmacies)} pharmacies, {len(products)} products, {order_count} orders, {before_inventory} inventory rows")
        print(f"Planned: source 50 real АНЦ branches; activate {len(ACTIVE_PRODUCT_IDS)} commercial medicines; stock {len(STOCKED_PRODUCT_IDS)} medicines in each branch; keep {len(OUT_OF_STOCK_PRODUCT_IDS)} visible but unavailable.")
        print("No order, customer, payment, or prescription rows are deleted or rewritten.")
        if not args.apply:
            print("Review only; no database changes made. Re-run with --apply to commit.")
            return 0

        conn.start_transaction()
        for pharmacy, branch in zip(pharmacies, branches, strict=True):
            cur.execute(
                "UPDATE pharmacies SET code=%s,name=%s,address=%s,city=%s,phone=%s WHERE id=%s",
                (branch["code"], branch["branch_name"], branch["address"], branch["city"], branch["phone"], pharmacy["id"]),
            )

        for product_id, (sku, name) in ARCHIVE_NAMES.items():
            cur.execute(
                "UPDATE products SET sku=%s,name=%s,description=%s,is_active=0,image_url=NULL,image_source_url=NULL WHERE id=%s",
                (sku, name, "Archived catalog record; unavailable for new reservations.", product_id),
            )
        cur.execute("UPDATE categories SET name='Безрецептурні препарати' WHERE name='Demo OTC'")
        cur.execute("UPDATE categories SET name='Рецептурні препарати' WHERE name='Demo Prescription'")
        cur.execute("UPDATE manufacturers SET name='Архівний виробник' WHERE name='Demo Manufacturer'")
        cur.execute("UPDATE promotions SET code='WELCOME10' WHERE code='DEMO-10'")

        cur.execute("UPDATE products SET is_active=0 WHERE id NOT IN (%s)" % ",".join(["%s"] * len(ACTIVE_PRODUCT_IDS)), tuple(sorted(ACTIVE_PRODUCT_IDS)))
        cur.execute("UPDATE products SET is_active=1 WHERE id IN (%s)" % ",".join(["%s"] * len(ACTIVE_PRODUCT_IDS)), tuple(sorted(ACTIVE_PRODUCT_IDS)))
        for product_id in ACTIVE_PRODUCT_IDS:
            cur.execute("SELECT image_url,image_source_url FROM products WHERE id=%s", (product_id,))
            existing = cur.fetchone()
            image, source = PHOTO_OVERRIDES.get(product_id, (existing["image_url"], existing["image_source_url"]))
            if not image or not source:
                raise RuntimeError(f"Product {product_id} does not have a source-attributed product image.")
            cur.execute("UPDATE products SET image_url=%s,image_source_url=%s WHERE id=%s", (image, source, product_id))
            cur.execute(
                "UPDATE products SET description=REPLACE(description,'Illustrative coursework price and stock; verify current offer with a pharmacy.','Ціни та залишки імітовані для навчального проєкту; актуальну пропозицію підтверджує аптека.') WHERE id=%s",
                (product_id,),
            )

        cur.execute("UPDATE pharmacy_inventory SET is_listed=0 WHERE product_id NOT IN (%s)" % ",".join(["%s"] * len(STOCKED_PRODUCT_IDS)), tuple(sorted(STOCKED_PRODUCT_IDS)))
        for product_id in OUT_OF_STOCK_PRODUCT_IDS:
            cur.execute("SELECT id,on_hand,reserved,is_listed FROM pharmacy_inventory WHERE product_id=%s", (product_id,))
            for row in cur.fetchall():
                old_hand, reserved = int(row["on_hand"]), int(row["reserved"])
                delta = reserved - old_hand
                if delta or row["is_listed"]:
                    cur.execute("UPDATE pharmacy_inventory SET on_hand=reserved,is_listed=0,updated_at=UTC_TIMESTAMP(6),version=version+1 WHERE id=%s", (row["id"],))
                if delta:
                    cur.execute(
                        "INSERT INTO inventory_movements(inventory_id,delta_on_hand,reason,reference_type,reference_id,performed_by_id,created_at) VALUES (%s,%s,'ADJUSTMENT','CATALOG_AVAILABILITY',%s,NULL,UTC_TIMESTAMP(6))",
                        (row["id"], delta, row["id"]),
                    )

        for pharmacy_index, pharmacy in enumerate(pharmacies, start=1):
            pharmacy_id = int(pharmacy["id"])
            for product_id in sorted(STOCKED_PRODUCT_IDS):
                base_price = Decimal(65 + ((product_id * 41) % 490))
                variation = Decimal(((pharmacy_index * 7 + product_id * 11) % 17) - 8) / Decimal(100)
                price = rounded(base_price * (Decimal(1) + variation))
                on_hand = 20 + ((pharmacy_index * 13 + product_id * 7) % 31)
                cur.execute("SELECT id,on_hand,reserved,unit_price,is_listed FROM pharmacy_inventory WHERE pharmacy_id=%s AND product_id=%s", (pharmacy_id, product_id))
                row = cur.fetchone()
                if row:
                    old_hand, reserved = int(row["on_hand"]), int(row["reserved"])
                    new_hand = max(old_hand, reserved + on_hand)
                    # Keep active reservations and their pre-existing price snapshots safe.
                    new_price = row["unit_price"] if reserved else price
                    if new_price != row["unit_price"] or new_hand != old_hand or not row["is_listed"]:
                        cur.execute("UPDATE pharmacy_inventory SET unit_price=%s,on_hand=%s,is_listed=1,updated_at=UTC_TIMESTAMP(6),version=version+1 WHERE id=%s", (new_price, new_hand, row["id"]))
                    if new_hand > old_hand:
                        cur.execute(
                            "INSERT INTO inventory_movements(inventory_id,delta_on_hand,reason,reference_type,reference_id,performed_by_id,created_at) VALUES (%s,%s,'RECEIPT','CATALOG_STOCKING',%s,NULL,UTC_TIMESTAMP(6))",
                            (row["id"], new_hand - old_hand, row["id"]),
                        )
                else:
                    cur.execute(
                        "INSERT INTO pharmacy_inventory(pharmacy_id,product_id,unit_price,on_hand,reserved,is_listed,updated_at,version) VALUES (%s,%s,%s,%s,0,1,UTC_TIMESTAMP(6),1)",
                        (pharmacy_id, product_id, price, on_hand),
                    )
                    inventory_id = cur.lastrowid
                    cur.execute(
                        "INSERT INTO inventory_movements(inventory_id,delta_on_hand,reason,reference_type,reference_id,performed_by_id,created_at) VALUES (%s,%s,'RECEIPT','CATALOG_STOCKING',%s,NULL,UTC_TIMESTAMP(6))",
                        (inventory_id, on_hand, inventory_id),
                    )

        conn.commit()
        cur.execute("SELECT COUNT(*) AS count FROM products WHERE is_active=1")
        print(f"Committed storefront catalog. Active products: {cur.fetchone()['count']}.")
        cur.execute("SELECT COUNT(*) AS branches FROM pharmacies")
        print(f"Pharmacy branches retained: {cur.fetchone()['branches']}.")
        cur.execute("SELECT COUNT(*) AS branches FROM (SELECT pharmacy_id,COUNT(*) AS products FROM pharmacy_inventory WHERE is_listed=1 AND on_hand>reserved GROUP BY pharmacy_id HAVING products=30) AS ready")
        print(f"Branches with exactly 30 available commercial products: {cur.fetchone()['branches']}.")
        cur.execute("SELECT COUNT(*) AS unavailable FROM products p WHERE p.is_active=1 AND p.id IN (%s) AND NOT EXISTS (SELECT 1 FROM pharmacy_inventory i WHERE i.product_id=p.id AND i.is_listed=1 AND i.on_hand>i.reserved)" % ",".join(["%s"] * len(OUT_OF_STOCK_PRODUCT_IDS)), tuple(sorted(OUT_OF_STOCK_PRODUCT_IDS)))
        print(f"Visible products unavailable at every branch: {cur.fetchone()['unavailable']}.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
