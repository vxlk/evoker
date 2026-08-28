use serde::Serialize;
use std::collections::BTreeMap;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc;
use std::thread;
use xmlrpc::{Request, Value};

#[derive(Debug, Serialize)]
pub struct PrefixStrategy {
    pub r#type: String,
    pub value: String,
}

#[derive(Debug, Serialize)]
pub struct ExactMatchStrategy {
    pub r#type: String,
    pub value: String,
    pub args: Vec<String>,
}

pub fn bootstrap_python() -> Result<PathBuf, String> {
    let home = std::env::var("USERPROFILE").or_else(|_| std::env::var("HOME")).unwrap_or_else(|_| ".".to_string());
    let evoker_dir = PathBuf::from(home).join(".evoker").join("python");
    
    let triple = if cfg!(target_os = "windows") {
        "x86_64-pc-windows-msvc"
    } else if cfg!(target_os = "macos") {
        if cfg!(target_arch = "aarch64") { "aarch64-apple-darwin" } else { "x86_64-apple-darwin" }
    } else {
        if cfg!(target_arch = "aarch64") { "aarch64-unknown-linux-gnu" } else { "x86_64-unknown-linux-gnu" }
    };

    let target_dir = evoker_dir.join(format!("python-3.13-{}", triple));
    let exe_name = if cfg!(target_os = "windows") { "python.exe" } else { "python3" };
    let exe_path = if cfg!(target_os = "windows") {
        target_dir.join("python").join(exe_name)
    } else {
        target_dir.join("python").join("bin").join(exe_name)
    };

    if exe_path.exists() {
        return Ok(exe_path);
    }

    std::fs::create_dir_all(&target_dir).map_err(|e| e.to_string())?;

    println!("Bootstrapping Python for Evoker...");
    
    // Fetch latest release JSON
    let output = Command::new("curl")
        .args(&["-sL", "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"])
        .output()
        .map_err(|e| format!("Failed to run curl: {}", e))?;
        
    let json: serde_json::Value = serde_json::from_slice(&output.stdout).map_err(|e| e.to_string())?;
    
    let mut download_url = String::new();
    if let Some(assets) = json.get("assets").and_then(|a| a.as_array()) {
        for asset in assets {
            if let Some(name) = asset.get("name").and_then(|n| n.as_str()) {
                if name.starts_with("cpython-3.13") 
                    && name.contains(triple) 
                    && name.contains("install_only.tar.gz")
                    && !name.contains("freethreaded") 
                    && !name.contains("stripped") {
                    
                    download_url = asset.get("browser_download_url").unwrap().as_str().unwrap().to_string();
                    break;
                }
            }
        }
    }

    if download_url.is_empty() {
        return Err("Could not find suitable python-build-standalone asset".to_string());
    }

    println!("Downloading {} ...", download_url);
    let archive_path = evoker_dir.join("python.tar.gz");
    
    let status = Command::new("curl")
        .args(&["-sL", &download_url, "-o", archive_path.to_str().unwrap()])
        .status()
        .map_err(|e| e.to_string())?;
        
    if !status.success() {
        return Err("Failed to download python".to_string());
    }
    
    println!("Extracting python...");
    let tar_status = Command::new("tar")
        .args(&["-xf", archive_path.to_str().unwrap(), "-C", target_dir.to_str().unwrap()])
        .status()
        .map_err(|e| e.to_string())?;
        
    if !tar_status.success() {
        return Err("Failed to extract python archive".to_string());
    }
    
    let _ = std::fs::remove_file(archive_path);
    
    if exe_path.exists() {
        println!("Installing evoker package...");
        let _ = Command::new(&exe_path)
            .args(&["-m", "pip", "install", "evoker"])
            .status();
        Ok(exe_path)
    } else {
        Err(format!("Python executable not found after extraction at {:?}", exe_path))
    }
}

#[derive(Debug)]
pub enum Strategy {
    Prefix(PrefixStrategy),
    ExactMatch(ExactMatchStrategy),
}

impl Serialize for Strategy {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        match self {
            Strategy::Prefix(p) => p.serialize(serializer),
            Strategy::ExactMatch(e) => e.serialize(serializer),
        }
    }
}

pub struct PluginClient {
    pub plugins_dir: PathBuf,
    pub strategies: Option<Vec<Strategy>>,
    pub injected_packages: Option<Vec<PathBuf>>,
    worker_process: Option<Child>,
    port: Option<u16>,
}

impl PluginClient {
    pub fn new<P: AsRef<Path>>(
        plugins_dir: P,
        strategies: Option<Vec<Strategy>>,
        injected_packages: Option<Vec<PathBuf>>,
    ) -> Self {
        Self {
            plugins_dir: plugins_dir.as_ref().to_path_buf(),
            strategies,
            injected_packages,
            worker_process: None,
            port: None,
        }
    }

    pub fn start_worker(&mut self, python_exe: Option<&str>, worker_target: &str) -> Result<(), String> {
        let actual_python = match python_exe {
            Some(p) => PathBuf::from(p),
            None => bootstrap_python()?
        };

        let mut cmd = Command::new(actual_python);
        cmd.arg("-u"); // unbuffered
        
        if worker_target.ends_with(".py") {
            cmd.arg(worker_target);
        } else {
            cmd.arg("-m").arg(worker_target);
        }
        
        cmd.arg(self.plugins_dir.to_str().unwrap());

        if let Some(ref strats) = self.strategies {
            if let Ok(json) = serde_json::to_string(strats) {
                cmd.env("EVOKER_STRATEGIES", json);
            }
        }

        if let Some(ref pkgs) = self.injected_packages {
            let pkg_strs: Vec<String> = pkgs
                .iter()
                .filter_map(|p| p.to_str().map(|s| s.to_string()))
                .collect();
            if let Ok(json) = serde_json::to_string(&pkg_strs) {
                cmd.env("EVOKER_INJECTED_PACKAGES", json);
            }
        }

        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());

        let mut child = cmd
            .spawn()
            .map_err(|e| format!("Failed to start worker process: {}", e))?;

        let stdout = child.stdout.take().expect("Failed to open stdout");
        let mut reader = BufReader::new(stdout);
        let mut line = String::new();

        let (tx, rx) = mpsc::channel();

        // Start a thread to read the port line
        thread::spawn(move || {
            let mut found_port = None;
            for _ in 0..50 {
                // read up to 50 lines looking for port
                line.clear();
                match reader.read_line(&mut line) {
                    Ok(0) => break,
                    Ok(_) => {
                        let trimmed = line.trim();
                        if trimmed.starts_with("RPC_PORT:") {
                            if let Ok(p) = trimmed[9..].parse::<u16>() {
                                found_port = Some(p);
                                break;
                            }
                        }
                    }
                    Err(_) => break,
                }
            }
            let _ = tx.send((found_port, reader));
        });

        match rx.recv_timeout(std::time::Duration::from_secs(5)) {
            Ok((Some(port), mut reader)) => {
                self.port = Some(port);
                self.worker_process = Some(child);

                // Thread to forward remaining stdout
                thread::spawn(move || {
                    let mut l = String::new();
                    while let Ok(bytes) = reader.read_line(&mut l) {
                        if bytes == 0 {
                            break;
                        }
                        print!("{}", l);
                        l.clear();
                    }
                });
                Ok(())
            }
            _ => {
                let _ = child.kill();
                Err("Failed to start worker or read port within timeout".to_string())
            }
        }
    }

    pub fn stop_worker(&mut self) {
        if let Some(mut child) = self.worker_process.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        self.port = None;
    }

    pub fn get_url(&self) -> String {
        format!("http://localhost:{}", self.port.unwrap_or(0))
    }

    pub fn scan(&self) -> Result<Value, String> {
        let req = Request::new("scan");
        req.call_url(&self.get_url())
            .map_err(|e| format!("RPC error: {}", e))
    }

    pub fn invoke(
        &self,
        plugin_name: &str,
        action_name: &str,
        kwargs: BTreeMap<String, Value>,
    ) -> Result<Value, String> {
        let req = Request::new("invoke")
            .arg(plugin_name)
            .arg(action_name)
            .arg(Value::Struct(kwargs));
            
        req.call_url(&self.get_url())
            .map_err(|e| format!("RPC error: {}", e))
    }
}

impl Drop for PluginClient {
    fn drop(&mut self) {
        self.stop_worker();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_strategy_serialization() {
        let prefix = Strategy::Prefix(PrefixStrategy {
            r#type: "prefix".to_string(),
            value: "test_".to_string(),
        });
        
        let json = serde_json::to_string(&prefix).unwrap();
        assert_eq!(json, r#"{"type":"prefix","value":"test_"}"#);
        
        let exact = Strategy::ExactMatch(ExactMatchStrategy {
            r#type: "exact".to_string(),
            value: "on_start".to_string(),
            args: vec!["app_context".to_string()],
        });
        
        let json2 = serde_json::to_string(&exact).unwrap();
        assert_eq!(json2, r#"{"type":"exact","value":"on_start","args":["app_context"]}"#);
    }
}
