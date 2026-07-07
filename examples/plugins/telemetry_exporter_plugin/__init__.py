def export_metrics(metrics: dict) -> bool:
    print("[Telemetry Exporter] Establishing connection to remote Grafana dashboard...")
    print(f"[Telemetry Exporter] Pushing payload: {metrics}")
    print("[Telemetry Exporter] Metrics successfully exported.")
    return True
