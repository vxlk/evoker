use std::env;
use std::path::PathBuf;
use evoker_host::PluginClient;

#[test]
fn test_invalid_python_exe() {
    let mut manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    manifest_dir.pop(); // hosts
    manifest_dir.pop(); // root
    let plugins_dir = manifest_dir.join("hosts").join("test_assets").join("plugins");
    
    let mut client = PluginClient::new(&plugins_dir, None, None);
    
    // Pass a non-existent executable
    let result = client.start_worker(Some("this_python_does_not_exist_12345"), "evoker.worker");
    assert!(result.is_err(), "Expected an error when using invalid python exe");
}

#[test]
fn test_worker_crash_handling() {
    let mut manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    manifest_dir.pop(); // hosts
    manifest_dir.pop(); // root
    let plugins_dir = manifest_dir.join("hosts").join("test_assets").join("plugins");
    
    // Create a dummy script that just exits immediately without printing RPC_PORT
    let dummy_script = manifest_dir.join("hosts").join("test_assets").join("crashing_worker.py");
    std::fs::write(&dummy_script, "import sys\nsys.exit(1)\n").unwrap();
    
    let mut client = PluginClient::new(&plugins_dir, None, None);
    
    // Should fail cleanly after a timeout or process exit detection
    let result = client.start_worker(Some("python"), dummy_script.to_str().unwrap());
    assert!(result.is_err(), "Expected start_worker to fail when worker crashes");
    
    // Clean up
    let _ = std::fs::remove_file(dummy_script);
}
