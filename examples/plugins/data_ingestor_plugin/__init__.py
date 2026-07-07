import pyarrow as pa
from plugin_host.arrow_ipc import write_table_to_mmap

def ingest_dataset(num_rows: int) -> str:
    print(f"[Data Ingestor] Generating fake dataset with {num_rows} rows...")
    
    data = [
        pa.array(range(num_rows)),
        pa.array([f"user_{i}" for i in range(num_rows)]),
        pa.array([float(i) * 1.5 for i in range(num_rows)])
    ]
    batch = pa.RecordBatch.from_arrays(data, names=['id', 'username', 'score'])
    table = pa.Table.from_batches([batch])
    
    print(f"[Data Ingestor] Serializing PyArrow Table to zero-copy Memory-Mapped file...")
    path = write_table_to_mmap(table)
    
    print(f"[Data Ingestor] Done! Returning lightweight handle: {path}")
    return path
