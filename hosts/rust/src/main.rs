use std::env;
use evoker_host::PluginClient;
use serde_json::Value;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 4 {
        eprintln!("Usage: evoker-host <plugins_dir> <plugin_name> <action_name> [json_args]");
        std::process::exit(1);
    }

    let plugins_dir = &args[1];
    let plugin_name = &args[2];
    let action = &args[3];
    
    let mut kwargs_json: std::collections::BTreeMap<String, Value> = std::collections::BTreeMap::new();
    if args.len() >= 5 {
        kwargs_json = serde_json::from_str(&args[4])?;
    }
    let mut kwargs = std::collections::BTreeMap::new();
    for (k, v) in kwargs_json {
        let xmlrpc_v = match v {
            Value::Null => xmlrpc::Value::Nil,
            Value::Bool(b) => xmlrpc::Value::Bool(b),
            Value::Number(n) => if let Some(i) = n.as_i64() { xmlrpc::Value::Int(i as i32) } else if let Some(f) = n.as_f64() { xmlrpc::Value::Double(f) } else { xmlrpc::Value::Nil },
            Value::String(s) => xmlrpc::Value::String(s),
            _ => xmlrpc::Value::Nil, // Simplified for CLI
        };
        kwargs.insert(k, xmlrpc_v);
    }

    let mut client = PluginClient::new(plugins_dir, None, None);
    
    if let Err(e) = client.start_worker(Some("python"), "plugin_host.worker") {
        eprintln!("Failed to start worker: {}", e);
        std::process::exit(1);
    }
    
    match client.invoke(plugin_name, action, kwargs) {
        Ok(res) => println!("{:?}", res),
        Err(e) => {
            eprintln!("Error: {}", e);
            std::process::exit(1);
        }
    }
    
    Ok(())
}
