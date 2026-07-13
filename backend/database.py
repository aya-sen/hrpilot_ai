from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# 1. On charge les variables secrètes (.env)
load_dotenv()

DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = os.getenv("DB_HOST")
DB_PORT     = os.getenv("DB_PORT")
DB_NAME     = os.getenv("DB_NAME")

# 2. On crée l'adresse de connexion
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 3. On crée le moteur (le tunnel vers MySQL)
engine = create_engine(DATABASE_URL,
    pool_size=20,  #garde jusqu'à 20 connexions ouvertes en permanence, prêtes à l'emploi
    max_overflow=10,  #si les 20 sont toutes occupées, autorise jusqu'à 10 connexions supplémentaires temporaires
    pool_timeout=30,    #une requête attend au maximum 30 secondes qu'une connexion se libère avant d'abandonner
    pool_recycle=1800)   #ferme et renouvelle les connexions inactives depuis 30 minutes (évite les connexions MySQL qui expirent silencieusement)

# 4. On crée l'usine qui fabrique les sessions de travail
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. On crée le moule de base pour nos futures tables
Base = declarative_base()

# 6. Fonction pour obtenir une connexion temporaire (utilisée par FastAPI)
def get_db():
    db = SessionLocal()
    try:
        yield db  # Donne l'accès à la base de données
    finally:
        db.close() # Ferme toujours la connexion après usage (très important !)