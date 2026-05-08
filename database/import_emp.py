import pandas as pd
from sqlalchemy import create_engine, text

# ── Connection ────────────────────────────────────────────────────────────────
engine = create_engine(
    "mysql+pymysql://root:YOUR_PASSWORD_HERE@localhost:3306/hrpilot_db"
)

# ── Step 1: Clear any partial data from previous attempts ─────────────────────
with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    conn.execute(text("DELETE FROM employees;"))
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    conn.commit()
    print("✅ Cleared old data")

# ── Step 2: Read the CSV ──────────────────────────────────────────────────────
df = pd.read_csv(r"C:\Users\user\Desktop\PFE project\DB\employee_data.csv")

print(f"Rows to import: {len(df)}")
print(f"Columns: {list(df.columns)}")

# ── Step 3: Import into MySQL ─────────────────────────────────────────────────
with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
    df.to_sql('employees', con=conn, if_exists='append', index=False)
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    conn.commit()

print(f"✅ Done! {len(df)} employees imported")

# ── Step 4: Verify ────────────────────────────────────────────────────────────
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM employees"))
    count = result.fetchone()[0]
    print(f"✅ MySQL confirms: {count} rows in employees table")