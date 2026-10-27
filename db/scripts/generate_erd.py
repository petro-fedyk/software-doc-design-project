#!/usr/bin/env python3
"""Generate an editable multi-page draw.io ERD from the canonical SQL DDL."""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL_PATH = ROOT / 'db/migrations/0001_initial.sql'
OUT_PATH = ROOT / 'docs/diagrams/database/Internet_Pharmacy_MySQL_ERD.drawio'
GROUPS = [
    ('Foundation — Identity, Catalog & Inventory', ['users','employee_assignments','customer_profiles','pharmacies','categories','manufacturers','products','pharmacy_inventory','inventory_movements']),
    ('Commerce — Cart, Orders & Delivery', ['carts','cart_items','orders','order_items','reservations','deliveries','delivery_rules']),
    ('Payments & Prescriptions', ['payments','refunds','prescription_records','prescription_verifications']),
    ('Loyalty & Promotions', ['loyalty_tiers','loyalty_accounts','loyalty_transactions','promotions','promotion_products']),
    ('Notifications, Audit & Outbox', ['notifications','availability_subscriptions','reminders','notification_preferences','outbox_events','audit_entries','schema_migrations']),
]


def split_statements(text: str) -> list[str]:
    text = re.sub(r'^\s*--.*$', '', text, flags=re.MULTILINE)
    return [s.strip() for s in text.split(';') if s.strip()]


def parse_schema() -> dict[str, dict]:
    tables: dict[str, dict] = {}
    for statement in split_statements(SQL_PATH.read_text()):
        match = re.match(r'CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*)\)\s*ENGINE=', statement, re.S)
        if not match:
            continue
        name, body = match.groups()
        table = {'columns': [], 'pk': set(), 'unique': set(), 'indexes': set(), 'fks': [], 'checks': []}
        for line in body.splitlines():
            line = line.strip().rstrip(',')
            if not line:
                continue
            if line.startswith('PRIMARY KEY'):
                table['pk'].update(re.findall(r'\w+', line[line.find('(')+1:line.rfind(')')]))
            elif line.startswith('UNIQUE KEY'):
                fields = line[line.find('(')+1:line.rfind(')')]
                table['unique'].update(re.findall(r'\w+', fields))
            elif line.startswith('KEY '):
                fields = line[line.find('(')+1:line.rfind(')')]
                table['indexes'].update(re.findall(r'\w+', fields))
            elif line.startswith('CONSTRAINT') and ' FOREIGN KEY ' in line:
                fk = re.search(r'FOREIGN KEY \((\w+)\) REFERENCES (\w+)\((\w+)\)', line)
                if fk:
                    table['fks'].append(fk.groups())
            elif line.startswith('CONSTRAINT') and ' CHECK ' in line:
                ck = re.search(r'CONSTRAINT (\w+) CHECK \((.*)\)$', line)
                if ck:
                    table['checks'].append((ck.group(1), ck.group(2)))
            elif not line.startswith(('CONSTRAINT ', 'PRIMARY KEY', 'UNIQUE KEY', 'KEY ')):
                col = re.match(r'(\w+)\s+(.+)', line)
                if col:
                    table['columns'].append((col.group(1), col.group(2)))
        tables[name] = table
    tables['schema_migrations'] = {
        'columns': [('version','VARCHAR(120) NOT NULL'), ('checksum','CHAR(64) NOT NULL'), ('applied_at','DATETIME(6) NOT NULL')],
        'pk': {'version'}, 'unique': set(), 'indexes': set(), 'fks': [], 'checks': [],
    }
    return tables


def add_vertex(parent, cell_id, value, x, y, w, h, style):
    cell = ET.SubElement(parent, 'mxCell', {'id':cell_id, 'value':value, 'style':style, 'vertex':'1', 'parent':'1'})
    ET.SubElement(cell, 'mxGeometry', {'x':str(x),'y':str(y),'width':str(w),'height':str(h),'as':'geometry'})
    return cell


def main() -> None:
    tables = parse_schema()
    root = ET.Element('mxfile', {'host':'app.diagrams.net','modified':'2026-10-27T00:00:00.000Z','agent':'db-erd-generator','version':'32.6.1','type':'device'})
    style = 'rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=8;fontSize=12;strokeColor=#52677D;fillColor=#FFFFFF;'
    page_for: dict[str,str] = {}
    for page_name, names in GROUPS:
        diagram_id = re.sub(r'[^a-z0-9]+','-',page_name.lower()).strip('-')
        diagram = ET.SubElement(root, 'diagram', {'id':diagram_id,'name':page_name})
        model = ET.SubElement(diagram, 'mxGraphModel', {'dx':'1500','dy':'1000','grid':'1','gridSize':'10','guides':'1','tooltips':'1','connect':'1','arrows':'1','fold':'1','page':'1','pageScale':'1','pageWidth':'1800','pageHeight':'1600','math':'0','shadow':'0'})
        cells = ET.SubElement(model,'root')
        ET.SubElement(cells,'mxCell',{'id':'0'})
        ET.SubElement(cells,'mxCell',{'id':'1','parent':'0'})
        for name in names:
            page_for[name] = diagram_id
        positions = {}
        table_values = {}
        for i, name in enumerate(names):
            table = tables[name]
            col = i % 3
            row = i // 3
            x, y = 30 + col*570, 90 + row*450
            w = 520
            lines = [f'<div style="font-family:Arial;font-size:14px"><b>{html.escape(name)}</b></div><hr style="margin:4px 0"/>']
            for col_name, definition in table['columns']:
                marks=[]
                if col_name in table['pk']: marks.append('PK')
                fk_targets=[f'{fk[1]}.{fk[2]}' for fk in table['fks'] if fk[0]==col_name]
                if fk_targets: marks.append('FK→'+','.join(fk_targets))
                if col_name in table['unique']: marks.append('UQ')
                if col_name in table['indexes']: marks.append('IDX')
                dtype=re.sub(r'\s+AUTO_INCREMENT','',definition)
                prefix=('['+'/'.join(marks)+'] ') if marks else ''
                lines.append(f'<div style="font-family:Arial;font-size:11px">{html.escape(prefix+col_name+" : "+dtype)}</div>')
            if table['checks']:
                lines.append('<hr style="margin:4px 0"/><div style="font-family:Arial;font-size:10px"><b>CHECKS</b></div>')
                for check_name, expr in table['checks']:
                    lines.append(f'<div style="font-family:Arial;font-size:10px">{html.escape(check_name)}: {html.escape(expr)}</div>')
            height=max(145, 40 + len(table['columns'])*21 + len(table['checks'])*28)
            positions[name]=(x,y,w,height)
            table_values[name]=''.join(lines)
        # Draw every FK whose referenced table is on this page. Cross-page keys remain marked in both table cells and notes.
        edge_idx=0
        for child_name in names:
            for field, target_name, target_field in tables[child_name]['fks']:
                if target_name not in names:
                    continue
                unique = field in tables[child_name]['unique']
                edge_style='edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#52677D;endArrow=ERone;endFill=0;'
                edge_style += 'startArrow=ERzeroToOne;startFill=0;' if unique else 'startArrow=ERmany;startFill=0;'
                edge=ET.SubElement(cells,'mxCell',{'id':f'fk-{diagram_id}-{edge_idx}','value':'','style':edge_style,'edge':'1','parent':'1','source':'tbl-'+child_name,'target':'tbl-'+target_name})
                ET.SubElement(edge,'mxGeometry',{'relative':'1','as':'geometry'})
                edge_idx += 1
        # Add table vertices after edges so boxes hide connector segments instead of obscuring labels.
        for name in names:
            x,y,w,h=positions[name]
            add_vertex(cells, 'tbl-'+name, table_values[name], x,y,w,h,style)
        external=[]
        for child_name in names:
            for field,target_name,target_field in tables[child_name]['fks']:
                if target_name not in names:
                    external.append(f'{child_name}.{field} → {target_name}.{target_field}')
        note_text='The SQL migration is canonical. PK/FK/UQ/IDX markers identify columns; CHECK constraints are listed on each table. FK column labels name the referenced table and key. All values are synthetic schema metadata.'
        if external:
            note_text += '<br/><b>Foreign keys to other pages:</b> '+ '; '.join(html.escape(x) for x in external)
        if 'schema_migrations' in names:
            note_text += '<br/><b>schema_migrations</b> is a technical migration ledger created by the runner, not a domain table.'
        add_vertex(cells,'note-'+diagram_id, f'<div style="font-family:Arial;font-size:12px">{note_text}</div>', 30, 1400, 1690, 150, 'rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;spacing=10;strokeColor=#8295A8;fillColor=#F2F6FA;fontSize=12;')
    ET.indent(root, space='  ')
    OUT_PATH.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(root).write(OUT_PATH, encoding='utf-8', xml_declaration=True)
    print(f'Wrote {OUT_PATH.relative_to(ROOT)} with {sum(len(GROUPS[i][1]) for i in range(len(GROUPS)))} schema tables including migration ledger across {len(GROUPS)} pages')

if __name__ == '__main__':
    main()
