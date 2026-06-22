import lancedb
import os

db_path = "/Users/bhsingh/Documents/Capstone5/mock_lancedb"

if not os.path.exists(db_path):
    print("LanceDB database not found yet. Run the fix_agent first!")
else:
    db = lancedb.connect(db_path)
    print(f"Tables in LanceDB: {db.table_names()}")
    
    table_name = "product_vectors"
    if table_name in db.table_names():
        table = db.open_table(table_name)
        
        print(f"\n--- Contents of table '{table_name}' ---")
        # Convert the LanceDB table to a Pandas DataFrame for beautiful printing
        df = table.to_pandas()
        print(df)
        print("\nTotal vectors stored:", len(df))
    else:
        print(f"Table '{table_name}' not found.")
