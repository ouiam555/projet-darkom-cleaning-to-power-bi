import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

user = os.getenv("db_user")
port = os.getenv("db_port")
host = os.getenv("db_host")
password = os.getenv("db_password")
name = os.getenv("db_name")

engine = create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}")

# create tables
with engine.begin() as conn:
    with open(r"C:\Users\HP\Desktop\projet darkom\warehouse\warehouse.sql", "r") as fich:
        conn.exec_driver_sql(fich.read())
print(" Tables créées")

# read data from clean
df = pd.read_sql("SELECT * FROM clean.annonces", engine)
print(f" {len(df)} lignes lues depuis clean")

# ===== dim_temps =====
dim_temps = df[['date_publication', 'annee_pub', 'mois_pub', 'trimestre_pub']].drop_duplicates()
dim_temps.to_sql('dim_temps', engine, schema='bi_schema', if_exists='append', index=False)
print(f" dim_temps: {len(dim_temps)} lignes")

# ===== dim_localisation =====
dim_localisation = df[['ville', 'quartier']].drop_duplicates()
dim_localisation.to_sql('dim_localisation', engine, schema='bi_schema', if_exists='append', index=False)
print(f" dim_localisation: {len(dim_localisation)} lignes")

# ===== dim_bien =====
dim_bien = df[['type_bien', 'categorie_surface', 'nb_chambres', 'nb_salles_bain', 'etage']].drop_duplicates()
dim_bien.to_sql('dim_bien', engine, schema='bi_schema', if_exists='append', index=False)
print(f" dim_bien: {len(dim_bien)} lignes")

# ===== dim_transaction =====
dim_transaction = df[['transaction']].drop_duplicates()
dim_transaction.to_sql('dim_transaction', engine, schema='bi_schema', if_exists='append', index=False)
print(f" dim_transaction: {len(dim_transaction)} lignes")

# ===== dim_categorie_prix =====
dim_categorie_prix = df[['categorie_prix']].drop_duplicates()
dim_categorie_prix.to_sql('dim_categorie_prix', engine, schema='bi_schema', if_exists='append', index=False)
print(f" dim_categorie_prix: {len(dim_categorie_prix)} lignes")

# ===== read ids =====
dim_temps_db = pd.read_sql("SELECT * FROM bi_schema.dim_temps", engine)
dim_loc_db = pd.read_sql("SELECT * FROM bi_schema.dim_localisation", engine)
dim_bien_db = pd.read_sql("SELECT * FROM bi_schema.dim_bien", engine)
dim_trans_db = pd.read_sql("SELECT * FROM bi_schema.dim_transaction", engine)
dim_cat_db = pd.read_sql("SELECT * FROM bi_schema.dim_categorie_prix", engine)

# ===== liee ids =====
df = df.merge(dim_temps_db, on=['date_publication', 'annee_pub', 'mois_pub', 'trimestre_pub'], how='left')
df = df.merge(dim_loc_db, on=['ville', 'quartier'], how='left')
df = df.merge(dim_bien_db, on=['type_bien', 'categorie_surface', 'nb_chambres', 'nb_salles_bain', 'etage'], how='left')
df = df.merge(dim_trans_db, on=['transaction'], how='left')
df = df.merge(dim_cat_db, on=['categorie_prix'], how='left')

# ===== loadfact =====
fact = df[['annonce_id', 'date_id', 'localisation_id', 'bien_id',
           'transaction_id', 'categorie_prix_id',
           'prix', 'surface', 'prix_m2', 'age_bien']]

fact.to_sql('fact_annonces', engine, schema='bi_schema', if_exists='append', index=False)
print(f" fact_annonces: {len(fact)} lignes")