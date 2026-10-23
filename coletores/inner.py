#%%
import pandas as pd
import os

#%%
arquivos = os.listdir('dados_api')

#%%
dfs = []

for arquivo in arquivos:
    df = pd.read_parquet(f'dados_api/{arquivo}')
    df['dt_referencia'] = pd.to_datetime(
    df['dt_referencia'],
    dayfirst=True,
    format='mixed',
    errors='coerce')

    df['dt_partida_prevista_utc'] = pd.to_datetime(
        df['dt_partida_prevista_utc'],
        dayfirst=True,
        format='mixed',
        errors='coerce')

    df['dt_chegada_prevista_utc'] = pd.to_datetime(
        df['dt_chegada_prevista_utc'],
        dayfirst=True,
        format='mixed',
        errors='coerce')
    dfs.append(df)

df_final = pd.concat(dfs, ignore_index=True)

df_final.to_parquet('data_voo/dados_completos.parquet', index=False)

#%%
df_final.head()


#%%
df_final.shape