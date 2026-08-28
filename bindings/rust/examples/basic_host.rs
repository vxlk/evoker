use std::collections::BTreeMap;
use std::env;
use std::path::PathBuf;
use evoker_host::PluginClient;
use xmlrpc::Value;

fn main() {
    let cwd = env::current_dir().unwrap();
    let plugins_dir = cwd.join("..").join("test_assets").join("plugins");
    
    let src_dir = cwd.join("..").join("python").join("src");
    unsafe {
        env::set_var("PYTHONPATH", src_dir);
    }
    let worker_script = "plugin_host.worker";

    let mut client = PluginClient::new(&plugins_dir, None, None);
    
    println!("Starting worker...");
    if let Err(e) = client.start_worker(Some("python"), worker_script) {
        eprintln!("Failed to start worker: {}", e);
        return;
    }
    
    println!("Worker started! Scanning plugins...");
    match client.scan() {
        Ok(manifest) => println!("Plugins Manifest: {:?}", manifest),
        Err(e) => eprintln!("Scan error: {}", e),
    }

    println!("Invoking test_plugin.hello_world...");
    let mut kwargs = BTreeMap::new();
    kwargs.insert("name".to_string(), Value::String("Rust Developer".to_string()));
    
    match client.invoke("test_plugin", "hello_world", kwargs) {
        Ok(res) => println!("Result: {:?}", res),
        Err(e) => eprintln!("Invoke error: {}", e),
    }
}
