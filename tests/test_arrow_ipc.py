import pytest
import pyarrow as pa
from plugin_host.arrow_ipc import write_table_to_mmap, read_table_from_mmap, cleanup_mmap

def test_arrow_ipc_roundtrip():
    # Create a large-ish table
    data = [
        pa.array([1, 2, 3, 4, 5] * 1000),
        pa.array(["a", "b", "c", "d", "e"] * 1000),
        pa.array([1.1, 2.2, 3.3, 4.4, 5.5] * 1000)
    ]
    batch = pa.RecordBatch.from_arrays(data, names=['f1', 'f2', 'f3'])
    table = pa.Table.from_batches([batch])
    
    # Simulate sender
    path = write_table_to_mmap(table)
    assert path.endswith(".arrow")
    
    # Simulate receiver
    try:
        received_table = read_table_from_mmap(path)
        
        # Verify schema and data
        assert received_table.schema == table.schema
        assert received_table.num_rows == 5000
        assert received_table.column('f1')[0].as_py() == 1
        assert received_table.column('f2')[4].as_py() == "e"
    finally:
        cleanup_mmap(path)
