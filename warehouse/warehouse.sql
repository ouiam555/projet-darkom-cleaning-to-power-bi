DROP SCHEMA IF EXISTS bi_schema CASCADE;
CREATE SCHEMA IF NOT EXISTS bi_schema;

DROP TABLE IF EXISTS bi_schema.dim_temps CASCADE;
CREATE TABLE bi_schema.dim_temps (
    date_id          SERIAL PRIMARY KEY,
    date_publication DATE,
    annee_pub        INTEGER,
    mois_pub         INTEGER,
    trimestre_pub    INTEGER
);

DROP TABLE IF EXISTS bi_schema.dim_localisation CASCADE;
CREATE TABLE bi_schema.dim_localisation (
    localisation_id SERIAL PRIMARY KEY,
    ville           TEXT,
    quartier        TEXT
);

DROP TABLE IF EXISTS bi_schema.dim_bien CASCADE;
CREATE TABLE bi_schema.dim_bien (
    bien_id           SERIAL PRIMARY KEY,
    type_bien         TEXT,
    categorie_surface TEXT,
    nb_chambres       INTEGER,
    nb_salles_bain    INTEGER,
    etage             INTEGER
);

DROP TABLE IF EXISTS bi_schema.dim_transaction CASCADE;
CREATE TABLE bi_schema.dim_transaction (
    transaction_id SERIAL PRIMARY KEY,
    transaction    TEXT
);
DROP TABLE IF EXISTS bi_schema.dim_categorie_prix CASCADE;
CREATE TABLE bi_schema.dim_categorie_prix (
    categorie_prix_id SERIAL PRIMARY KEY,
    categorie_prix    TEXT
);
DROP TABLE IF EXISTS bi_schema.fact_annonces CASCADE;
CREATE TABLE bi_schema.fact_annonces (
    annonce_id        TEXT PRIMARY KEY,
    date_id           INTEGER REFERENCES bi_schema.dim_temps(date_id),
    localisation_id   INTEGER REFERENCES bi_schema.dim_localisation(localisation_id),
    bien_id           INTEGER REFERENCES bi_schema.dim_bien(bien_id),
    transaction_id    INTEGER REFERENCES bi_schema.dim_transaction(transaction_id),
    categorie_prix_id INTEGER REFERENCES bi_schema.dim_categorie_prix(categorie_prix_id),
    prix              NUMERIC,
    surface           NUMERIC,
    prix_m2           NUMERIC,
    age_bien          INTEGER
);