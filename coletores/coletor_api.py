import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta

url_base = "https://sas.anac.gov.br/sas/siros_api/api/voosPeriodo"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
}

periodos = pd.date_range(start='2015-01-01', end='2025-12-31', freq='MS')

session = requests.Session()

for data_inicio in periodos:
    data_fim = data_inicio + pd.offsets.MonthEnd(0)
    
    str_inicio = data_inicio.strftime('%d%m%Y')
    str_fim = data_fim.strftime('%d%m%Y')
    
    print(f"Baixando: {str_inicio} até {str_fim}...", end=" ")
    
    params = {
        'dataReferenciaInicio': str_inicio,
        'dataReferenciaFinal': str_fim
    }
    
    try:
        response = session.get(url_base, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200 and "data:image/png;base64" not in response.text:
            conteudo = response.text.strip()
            if conteudo.startswith('"'):
                conteudo = json.loads(conteudo)
            
            dados = json.loads(conteudo[0] if isinstance(conteudo, list) else conteudo)
            df_mes = pd.DataFrame(dados)
            
            nome_arq = f"voos_{data_inicio.strftime('%Y_%m')}.parquet"
            df_mes.to_parquet(nome_arq, index=False, compression='snappy')
            
            print(f"OK! ({len(df_mes)} voos)")
        else:
            print("BLOQUEIO ou ERRO. Aguardando 60s...")
            time.sleep(60)
            
    except Exception as e:
        print(f"Falhou: {e}")
    
    time.sleep(2) 

print("Processo concluído!")