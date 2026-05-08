import pandas as pd
from sqlalchemy import create_engine, text
import numpy as np

# ── Connection ────────────────────────────────────────────────────────────────
engine = create_engine(
    "mysql+pymysql://root:YOUR_PASSWORD_HERE@localhost:3306/hrpilot_db"
)

# ── File paths — update these ─────────────────────────────────────────────────
LEAVE_PATH    = r"C:\Users\user\Desktop\PFE project\DB\leave_requests.csv"
DOC_PATH      = r"C:\Users\user\Desktop\PFE project\DB\document_requests.csv"
CHAT_PATH     = r"C:\Users\user\Desktop\PFE project\DB\chat_history.csv"

# ── Helper function ───────────────────────────────────────────────────────────
def import_table(df, table_name, conn):
    df = df.replace({np.nan: None})
    df.to_sql(table_name, con=conn, if_exists='append', index=False)
    print(f"✅ {table_name}: {len(df)} rows imported")

# ── Read all 3 files ──────────────────────────────────────────────────────────
df_leave = pd.read_csv(LEAVE_PATH, sep=';')
df_doc   = pd.read_csv(DOC_PATH,   sep=';', encoding='latin-1')
df_chat  = pd.read_csv(CHAT_PATH,  sep=';', encoding='latin-1')

print(f"leave_requests:    {len(df_leave)} rows")
print(f"document_requests: {len(df_doc)} rows")
print(f"chat_history:      {len(df_chat)} rows")
print()

# ── Import all 3 ─────────────────────────────────────────────────────────────
with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

    import_table(df_leave, 'leave_request',    conn)
    import_table(df_doc,   'document_request', conn)
    import_table(df_chat,  'chat_history',     conn)

    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    conn.commit()

# ── Verify ────────────────────────────────────────────────────────────────────
print()
with engine.connect() as conn:
    for table in ['leave_request', 'document_request', 'chat_history']:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()[0]
        print(f"✅ MySQL confirms: {table} → {count} rows")