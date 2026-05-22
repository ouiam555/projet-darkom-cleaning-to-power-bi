import psycopg2
import csv
import logging
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    filename='staging.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

def get_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("db_host"),
            port=os.getenv("db_port"),
            dbname=os.getenv("db_name"),
            user=os.getenv("db_user"),
            password=os.getenv("db_password")
        )
        print(" Connexion réussie")
        return conn
    except Exception as e:
        print(f" Erreur de connexion : {e}")
        return None

def create_staging_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE SCHEMA IF NOT EXISTS staging;
        DROP TABLE IF EXISTS staging.annonces_raw;
        CREATE TABLE staging.annonces_raw (
            annonce_id         TEXT,
            date_publication   TEXT,
            titre              TEXT,
            ville              TEXT,
            quartier           TEXT,
            type_bien          TEXT,
            transaction        TEXT,
            prix               TEXT,
            surface            TEXT,
            nb_chambres        TEXT,
            nb_salles_bain     TEXT,
            etage              TEXT,
            annee_construction TEXT,
            loaded_at          TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    print(" Schema et table staging créés")

def load_csv(conn, csv_path):
    cursor = conn.cursor()
    inserted = 0
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO staging.annonces_raw (
                    annonce_id, date_publication, titre, ville, quartier,
                    type_bien, transaction, prix, surface, nb_chambres,
                    nb_salles_bain, etage, annee_construction
                ) VALUES (
                    %(annonce_id)s, %(date_publication)s, %(titre)s, %(ville)s, %(quartier)s,
                    %(type_bien)s, %(transaction)s, %(prix)s, %(surface)s, %(nb_chambres)s,
                    %(nb_salles_bain)s, %(etage)s, %(annee_construction)s
                )
            """, row)
            inserted += 1
    conn.commit()
    print(f" {inserted} lignes insérées dans staging")
    logging.info(f"{inserted} lignes chargées")

def validate(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM staging.annonces_raw")
    count = cursor.fetchone()[0]
    print(f" Validation: {count} lignes dans staging")

if __name__ == "__main__":
    conn = get_connection()
    if conn:
        create_staging_table(conn)
        load_csv(conn, r"C:\Users\HP\Desktop\projet darkom\data\darkom.csv")
        validate(conn)
        conn.close()