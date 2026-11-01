"""Filtra el catálogo de datos.gov.co (out/catalogo/catalogo.json) según los criterios del paso 2."""
import json, re, collections, sys
a = json.load(open('out/catalogo/catalogo.json', encoding='utf8'))
PERS = re.compile(r'(nombre(?!.*(entidad|municipio|departamento|programa|sede|establecimiento|ips|instituci|proyecto|producto|empresa|centro|curso|vereda|especie|cultivo|indicador|estaci|rio|corregimiento|zona|sector|banco|prestador|operador|eps|colegio))|apellido|c[eé]dula|documento|identificaci|direcci[oó]n|tel[eé]fono|celular|correo|e-?mail|predio|paciente|v[ií]ctima|edad|sexo|g[eé]nero|placa|matr[ií]cula inmobiliaria|representante|beneficiario|estudiante|docente|funcionario|contratista)', re.I)
EXCL_CAT = {'Seguridad y Defensa', 'Justicia y Derecho', 'Resultados Electorales', 'Organismos de Control', '-'}
DATE = {'calendar date', 'date', 'floating timestamp'}
NUM = {'number', 'money', 'percent'}
TEMP = re.compile(r'^(a[ñn]o|anio|vigencia|periodo|mes|fecha)', re.I)
out = []
for r in a:
    R = r['resource']; cat = r['classification'].get('domain_category') or '-'
    if R.get('type') != 'dataset' or R.get('lens_view_type') not in (None, 'tabular') : continue
    if cat in EXCL_CAT: continue
    lic = r.get('metadata', {}).get('license', '')
    if 'Creative Commons Attribution' not in lic and lic != 'Public Domain': continue
    if 'NoDerivatives' in lic: continue
    names = R.get('columns_name') or []; fields = [f for f in (R.get('columns_field_name') or []) if not f.startswith(':')]
    types = [x.lower() for x in (R.get('columns_datatype') or [])]
    if not (6 <= len(fields) <= 35): continue
    t = collections.Counter(types)
    nt = t['text']; nn = sum(t[x] for x in NUM); nd = sum(t[x] for x in DATE)
    ntemp = sum(1 for n in names if TEMP.search(n or ''))
    if nt < 2 or nn < 2 or (nd + ntemp) < 1: continue
    pers = [n for n in names if PERS.search(n or '')]
    if pers: continue
    upd = (R.get('data_updated_at') or '')[:10]
    if upd < '2025-01-01': continue
    out.append(dict(id=R['id'], nombre=R['name'], cat=cat, entidad=R.get('attribution'), lic=lic, upd=upd,
                    vistas=R['page_views']['page_views_total'], ncols=len(fields), text=nt, num=nn, date=nd, temporal=ntemp,
                    otros=sorted(set(types) - {'text'} - NUM - DATE),
                    freq=next((m['value'] for m in r['classification'].get('domain_metadata', []) if 'Frecuencia' in m['key']), '')))
json.dump(out, open('out/catalogo/filtrados.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print(len(out), 'candidatos')
print(collections.Counter(x['cat'] for x in out).most_common())
for x in out[:80]: print(x['id'], x['cat'][:18], x['vistas'], x['upd'], x['ncols'], f"{x['text']}/{x['num']}/{x['date']}/{x['temporal']}", x['otros'], '|', x['nombre'][:80])
