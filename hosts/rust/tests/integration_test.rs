use std::collections::BTreeMap;
use std::env;
use std::path::PathBuf;
use evoker_host::PluginClient;
use xmlrpc::Value;

#[test]
fn test_plugin_client() {
    let mut manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    manifest_dir.pop(); // hosts
    manifest_dir.pop(); // root
    let plugins_dir = manifest_dir.join("hosts").join("test_assets").join("plugins");
    
    // Set PYTHONPATH so python can find evoker
    let src_dir = manifest_dir.join("hosts").join("python").join("src");
    unsafe {
        env::set_var("PYTHONPATH", src_dir);
    }
    
    // Check if python is available
    let worker_script = "evoker.worker";

    let mut client = PluginClient::new(&plugins_dir, None, None);
    
    // Start worker
    let result = client.start_worker(Some("python"), worker_script);
    assert!(result.is_ok(), "Failed to start worker: {:?}", result.err());

    // Test scan
    let scan_res = client.scan();
    assert!(scan_res.is_ok(), "Scan failed");
    let scan_value = scan_res.unwrap();
    
    if let Value::Struct(manifest) = scan_value {
        println!("Resolved plugins_dir: {:?}", plugins_dir);
        println!("Manifest: {:?}", manifest);
        assert!(manifest.contains_key("test_plugin"), "Manifest did not contain test_plugin");
    } else {
        panic!("Expected Struct from scan");
    }

    // Test invoke
    let mut kwargs = BTreeMap::new();
    kwargs.insert("name".to_string(), Value::String("World".to_string()));
    
    let invoke_res = client.invoke("test_plugin", "hello_world", kwargs);
    assert!(invoke_res.is_ok(), "Invoke failed");
    let invoke_value = invoke_res.unwrap();
    
    assert_eq!(invoke_value, Value::String("Hello, World!".to_string()));

    // Client drop will stop worker
}
