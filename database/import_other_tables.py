import pandas as pd
from sqlalchemy import create_engine, text
import numpy as np

# ── Connection ────────────────────────────────────────────────────────────────
engine = create_engine(
    "mysql+pymysql://root:1234@localhost:3306/hrpilot_db"
)

# ── File paths ────────────────────────────────────────────────────────────────
LEAVE_PATH    = r"C:\Users\user\Desktop\PFE project\DB\leave_request.csv"
DOC_PATH      = r"C:\Users\user\Desktop\PFE project\DB\document_request.csv"

# ── Helper function ───────────────────────────────────────────────────────────
def import_table(df, table_name, conn):
    df = df.replace({np.nan: None})
    df.to_sql(table_name, con=conn, if_exists='append', index=False)
    print(f"✅ {table_name}: {len(df)} rows imported")

# ── Read the 2 required files with semicolon separator ────────────────────────
df_leave = pd.read_csv(LEAVE_PATH, sep=',')
df_doc   = pd.read_csv(DOC_PATH,   sep=',', encoding='latin-1')

print(f"leave_requests (CSV):    {len(df_leave)} rows")
print(f"document_requests (CSV): {len(df_doc)} rows")
print("chat_history:            Will be left empty as requested")
print()

# ── Clean tables (Truncate / Delete) ──────────────────────────────────────────
with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    conn.execute(text("DELETE FROM leave_request;"))
    conn.execute(text("DELETE FROM document_request;"))
    conn.execute(text("TRUNCATE TABLE chat_history;"))  # On s'assure qu'elle est bien vide
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    conn.commit()
    print("✅ Tables secondaires vidées proprement")

# ── Import only the 2 required tables ─────────────────────────────────────────
with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

    import_table(df_leave, 'leave_request',    conn)
    import_table(df_doc,   'document_request', conn)
    # L'import de chat_history a été retiré ici pour laisser la table vide

    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    conn.commit()

# ── Verify directly in MySQL ──────────────────────────────────────────────────
print()
with engine.connect() as conn:
    for table in ['leave_request', 'document_request', 'chat_history']:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()[0]
        print(f"✅ MySQL confirms: {table} → {count} rows")