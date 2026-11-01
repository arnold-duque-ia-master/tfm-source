"""Perfila conjuntos candidatos: metadatos, número de filas, rango temporal y muestra."""
import json, sys, re
from pathlib import Path
import soda3_probe as s

IDS = sys.argv[1:]
tok = s.load_token()
out = Path('out/catalogo'); (out / 'metadata').mkdir(parents=True, exist_ok=True)
res = []
for ds in IDS:
    m = s.get_metadata(ds)
    (out / 'metadata' / f'{ds}.json').write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding='utf8')
    cols = [c for c in m['columns'] if not c['fieldName'].startswith(':')]
    n = s.soql(ds, 'SELECT count(*) AS n', tok)
    rows = n['sample'][0]['n'] if n['status'] == 200 else f"ERR {n['status']}"
    dcol = next((c['fieldName'] for c in cols if c['dataTypeName'] in ('calendar_date',)), None)
    rng = ''
    if dcol:
        r = s.soql(ds, f'SELECT min({dcol}) AS a, max({dcol}) AS b', tok)
        if r['status'] == 200: rng = f"{dcol}: {r['sample'][0].get('a','')[:10]} → {r['sample'][0].get('b','')[:10]}"
    else:
        y = next((c['fieldName'] for c in cols if re.match(r'(a_o|ano|anio|vigencia|periodo|a_o_)', c['fieldName'])), None)
        if y:
            r = s.soql(ds, f'SELECT min({y}) AS a, max({y}) AS b', tok)
            if r['status'] == 200: rng = f"{y}: {r['sample'][0].get('a')} → {r['sample'][0].get('b')}"
    smp = s.soql(ds, 'SELECT *', tok, page=(1, 1))
    res.append(dict(id=ds, nombre=m['name'], entidad=m.get('attribution'), categoria=m.get('category'),
                    licencia=(m.get('license') or {}).get('name'), filas=rows, rango=rng,
                    columnas=[(c['fieldName'], c['dataTypeName']) for c in cols],
                    muestra=smp['sample'][0] if smp['status'] == 200 and smp['sample'] else None))
    print(ds, rows, rng, '|', m['name'][:70], flush=True)
json.dump(res, open(out / 'perfiles.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
