from plugin_host.arrow_ipc import read_table_from_mmap, cleanup_mmap

def analyze_sentiment(mmap_path: str) -> dict:
    print(f"[NLP Analyzer] Opening memory-mapped PyArrow table from: {mmap_path}")
    
    # Read table with zero-copy overhead
    table = read_table_from_mmap(mmap_path)
    print(f"[NLP Analyzer] Loaded table with {table.num_rows} rows instantly.")
    
    # Simulate some analysis
    print(f"[NLP Analyzer] Running HuggingFace transformers (simulated) on {table.num_rows} rows...")
    
    avg_score = 0.0
    if table.num_rows > 0:
        scores = table.column('score')
        avg_score = sum(score.as_py() for score in scores) / table.num_rows
    
    # Cleanup IPC file
    cleanup_mmap(mmap_path)
    print(f"[NLP Analyzer] Analysis complete. Cleaned up IPC handles.")
    
    return {
        "status": "success",
        "rows_processed": table.num_rows,
        "average_sentiment_score": avg_score
    }
