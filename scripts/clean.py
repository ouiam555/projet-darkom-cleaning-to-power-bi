import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
import matplotlib
matplotlib.use('Agg')
import seaborn as sns
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

load_dotenv()

engine = create_engine(f"postgresql+psycopg2://{os.getenv('db_user')}:{os.getenv('db_password')}@{os.getenv('db_host')}:{os.getenv('db_port')}/{os.getenv('db_name')}")

# ============ LECTURE DEPUIS STAGING ============
df = pd.read_sql("SELECT * FROM staging.annonces_raw", engine)
print(f" {len(df)} lignes lues depuis staging")
print(df.shape)
print(df.info())
print(df.describe())
print(df.head())
print(df.isnull().sum() / len(df) * 100)
print(df.duplicated().sum())

# ============ DOUBLONS ============
df = df.drop_duplicates()
df = df[df['transaction'] != '']
df = df[df['type_bien'] != '']
print(df.shape)

# ============ TYPES ============
df['date_publication'] = pd.to_datetime(df['date_publication'], errors='coerce')
df['prix'] = pd.to_numeric(df['prix'], errors='coerce')
df['surface'] = pd.to_numeric(df['surface'], errors='coerce')
df['nb_chambres'] = pd.to_numeric(df['nb_chambres'], errors='coerce').astype('Int64')
df['nb_salles_bain'] = pd.to_numeric(df['nb_salles_bain'], errors='coerce').astype('Int64')
df['etage'] = pd.to_numeric(df['etage'], errors='coerce').astype('Int64')
df['annee_construction'] = pd.to_numeric(df['annee_construction'], errors='coerce').astype('Int64')
print(df.info())

# ============ NAN ============
df['quartier'] = df['quartier'].replace(r'^\s*$', pd.NA, regex=True)
df['quartier'] = df['quartier'].fillna('Inconnu')
df['etage'] = df['etage'].fillna(0)
df['annee_construction'] = df['annee_construction'].fillna(int(df['annee_construction'].median()))
df['nb_chambres'] = df['nb_chambres'].fillna(int(df['nb_chambres'].median()))
df['nb_salles_bain'] = df['nb_salles_bain'].fillna(int(df['nb_salles_bain'].median()))
df['type_bien'] = df['type_bien'].fillna("inconnu")
df = df.dropna(subset=['date_publication', 'type_bien', 'transaction'])
print(df.isnull().sum())
print(df.shape)

# ============ ANOMALIES ============
colonnes = ['prix', 'surface', 'nb_chambres', 'nb_salles_bain']
for col in colonnes:
    skewness = df[col].skew()
    type_dist = "Symétrique" if abs(skewness) < 0.5 else "Asymétrique"
    plt.figure(figsize=(8, 4))
    sns.histplot(df[col], kde=True)
    plt.title(f'{col} | Skew: {skewness:.2f} | {type_dist}')
    plt.savefig(f'{col}.png')
    plt.close()
    print(f"{col}: skew = {skewness:.2f} → {type_dist}")

# IQR
for col in colonnes:
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    borne_inf = Q1 - 1.5 * IQR
    borne_sup = Q3 + 1.5 * IQR
    anomalies = df[(df[col] < borne_inf) | (df[col] > borne_sup)]
    print(f"{col}: {len(anomalies)} anomalies")

# OUTLIERS IMPOSSIBLES
df = df[df['prix'] > 0]
df = df[df['surface'] > 0]
df = df[df['nb_chambres'] >= 0]
df = df[df['nb_salles_bain'] >= 0]
print(f"Shape après nettoyage: {df.shape}")

# ============ FEATURE ENGINEERING ============
df['prix_m2'] = df['prix'] / df['surface']
df['age_bien'] = 2024 - df['annee_construction']

def categorie_prix(prix):
    if prix < 500000:
        return 'Économique'
    elif prix < 1500000:
        return 'Moyen'
    elif prix < 5000000:
        return 'Haut standing'
    else:
        return 'Luxe'

def categorie_surface(surface):
    if surface < 80:
        return 'Petit'
    elif surface <= 150:
        return 'Moyen'
    else:
        return 'Grand'

df['categorie_prix'] = df['prix'].apply(categorie_prix)
df['categorie_surface'] = df['surface'].apply(categorie_surface)
df['annee_pub'] = df['date_publication'].dt.year
df['mois_pub'] = df['date_publication'].dt.month
df['trimestre_pub'] = df['date_publication'].dt.quarter

# ============ STANDARDISATION ============
df['ville'] = df['ville'].str.strip().str.title()
df['type_bien'] = df['type_bien'].str.strip().str.title()
df['transaction'] = df['transaction'].str.strip().str.title()
df['quartier'] = df['quartier'].str.strip().str.title()

ville_mapping = {'Casa': 'Casablanca', 'Csa': 'Casablanca'}
df['ville'] = df['ville'].replace(ville_mapping)

print(df['ville'].unique())
print(df['type_bien'].unique())
print(df['transaction'].unique())

# ============ POSTGRESQL ============
def get_connection():
    return psycopg2.connect(
        host=os.getenv("db_host"),
        port=os.getenv("db_port"),
        dbname=os.getenv("db_name"),
        user=os.getenv("db_user"),
        password=os.getenv("db_password")
    )

def create_clean_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE SCHEMA IF NOT EXISTS clean;
        DROP TABLE IF EXISTS clean.annonces;
        CREATE TABLE clean.annonces (
            annonce_id          TEXT PRIMARY KEY,
            date_publication    DATE,
            titre               TEXT,
            ville               TEXT,
            quartier            TEXT,
            type_bien           TEXT,
            transaction         TEXT,
            prix                NUMERIC,
            surface             NUMERIC,
            nb_chambres         INTEGER,
            nb_salles_bain      INTEGER,
            etage               INTEGER,
            annee_construction  INTEGER,
            prix_m2             NUMERIC,
            age_bien            INTEGER,
            categorie_prix      TEXT,
            categorie_surface   TEXT,
            annee_pub           INTEGER,
            mois_pub            INTEGER,
            trimestre_pub       INTEGER
        );
    """)
    conn.commit()
    print(" Table clean créée")

def insert_clean_data(conn, df):
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO clean.annonces VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s
            )
        """, (
            row['annonce_id'], row['date_publication'], row['titre'],
            row['ville'], row['quartier'], row['type_bien'],
            row['transaction'], row['prix'], row['surface'],
            row['nb_chambres'], row['nb_salles_bain'], row['etage'],
            row['annee_construction'], row['prix_m2'], row['age_bien'],
            row['categorie_prix'], row['categorie_surface'],
            row['annee_pub'], row['mois_pub'], row['trimestre_pub']
        ))
    conn.commit()
    print(f" {len(df)} lignes insérées dans clean.annonces")

conn = get_connection()
if conn:
    create_clean_table(conn)
    insert_clean_data(conn, df)
    conn.close()