# Script único (fora do pipeline): consulta a API do IBGE para gerar o
# dicionário município -> regional de saúde usado em regionais_pr.py.
import csv
import json
import urllib.request
import unicodedata
import gzip
import io
from pathlib import Path

base_dir = Path(__file__).resolve().parent
project_dir = base_dir.parent.parent

# 1. API do IBGE
req = urllib.request.Request('https://servicodados.ibge.gov.br/api/v1/localidades/estados/41/municipios', headers={'User-Agent': 'Mozilla/5.0'})
res = urllib.request.urlopen(req)
if res.info().get('Content-Encoding') == 'gzip':
    data = gzip.GzipFile(fileobj=io.BytesIO(res.read())).read()
else:
    data = res.read()
municipios_ibge = json.loads(data.decode('utf-8'))
ibge_completos = {str(m['id'])[:6]: m['nome'] for m in municipios_ibge}

# 2. Abre o CSV
csv_path = project_dir / "base_filtrada" / "dados_filtro_pr.csv"
out_path = project_dir / "src" / "tecnicas" / "regionais_pr.py"

m = {}
with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        mun = row['CO_MUN_RES']
        reg = row['ID_RG_RESI']
        if mun and reg and mun.startswith('41'):
            if mun not in m:
                m[mun] = reg

def unaccent(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

missing = [k for k in ibge_completos if k not in m]

with open(out_path, 'w', encoding='utf-8') as f:
    f.write('# Mapeamento: Código IBGE (6 dígitos) -> Regional de Saúde (PR)\n\n')
    f.write('IBGE_TO_REGIONAL_PR = {\n')
    for k in sorted(m.keys()):
        val = m[k]
        if 'RS' in val:
            parts = val.split('RS', 1)
            num = ''.join(filter(str.isdigit, parts[0]))
            name = parts[1].strip().title()
            val_clean = f"{num.zfill(2)}° RS - {name}"
        else:
            val_clean = val
        f.write(f'    "{k}": "{val_clean}", # {unaccent(ibge_completos.get(k, k))}\n')
    
    # Adiciona manualmente o município faltante (Alto Paraíso e 12ª RS)
    if '412862' in missing:
        f.write('    "412862": "12° RS - Umuarama", # Alto Paraiso\n')

    f.write('}\n')

print(f"Arquivo gerado com sucesso, {len(m) + len(missing)} itens.")
