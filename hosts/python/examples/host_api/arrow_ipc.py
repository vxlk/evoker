import pyarrow as pa
import pyarrow.ipc
import tempfile
import os
from pathlib import Path

def write_table_to_mmap(table: pa.Table) -> str:
    """Writes a PyArrow table to a temporary file via IPC stream.
    Returns the absolute file path as a string.
    """
    fd, path = tempfile.mkstemp(suffix=".arrow")
    os.close(fd)
    
    with pa.OSFile(path, 'wb') as sink:
        with pa.RecordBatchFileWriter(sink, table.schema) as writer:
            writer.write_table(table)
            
    return path

def read_table_from_mmap(path: str) -> pa.Table:
    """Reads a PyArrow table from a memory-mapped file (zero-copy)."""
    # Important: pa.memory_map ensures we don't copy the underlying buffer into Python space
    source = pa.memory_map(path, 'r')
    reader = pa.RecordBatchFileReader(source)
    return reader.read_all()

def cleanup_mmap(path: str):
    """Deletes the temporary IPC file."""
    try:
        os.remove(path)
    except OSError:
        pass
