use serde::Serialize;
use std::collections::BTreeMap;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc;
use std::thread;
use xmlrpc::{Request, Value, Transport};

struct EvokerTransport(reqwest::blocking::RequestBuilder);

impl Transport for EvokerTransport {
    type Stream = Box<dyn std::io::Read + Send>;
    fn transmit(self, req: &Request) -> Result<Self::Stream, Box<dyn std::error::Error + Send + Sync>> {
        let mut buf = Vec::new();
        req.write_as_xml(&mut buf)?;
        
        let xml = String::from_utf8(buf)?;
        for c in xml.chars() {
            let code = c as u32;
            if code < 0x20 && code != 0x09 && code != 0x0A && code != 0x0D {
                return Err("Control characters are not allowed in XML-RPC strings".into());
            }
        }
        
        let xml = xml.replace("\r", "&#13;");
        
        let res = self.0.body(xml).header("Content-Type", "text/xml").send()?;
        if !res.status().is_success() {
            return Err(format!("HTTP error: {}", res.status()).into());
        }
        Ok(Box::new(res))
    }
}

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

fn ensure_evoker_installed(exe_path: &PathBuf) -> Result<(), String> {
    // Verify import succeeds and version matches
    let version = env!("CARGO_PKG_VERSION");
    let check_script = format!("import importlib.metadata; import sys; sys.exit(0 if importlib.metadata.version('evoker') == '{}' else 1)", version);
    let import_status = Command::new(exe_path)
        .args(&["-c", check_script])
        .status()
        .map_err(|e| e.to_string())?;
        
    if import_status.success() {
        return Ok(());
    }

    println!("Installing evoker runtime into bootstrapped python...");
    let mut repo_path = std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."));
    while !repo_path.join("evoker").join("pyproject.toml").exists() {
        if !repo_path.pop() {
            return Err("Could not find evoker package directory to install runtime".to_string());
        }
    }
    
    let evoker_package = repo_path.join("evoker");
    let pip_status = Command::new(exe_path)
        .args(&["-m", "pip", "install", evoker_package.to_str().unwrap()])
        .output()
        .map_err(|e| e.to_string())?;
        
    if !pip_status.status.success() {
        return Err(format!("Failed to install evoker runtime via pip: {}", String::from_utf8_lossy(&pip_status.stderr)));
    }
    
    let import_status_2 = Command::new(exe_path)
        .args(&["-c", "import evoker.worker"])
        .status()
        .map_err(|e| e.to_string())?;
        
    if !import_status_2.success() {
        return Err("Failed to import evoker.worker after installation".to_string());
    }
    
    Ok(())
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
        ensure_evoker_installed(&exe_path)?;
        return Ok(exe_path);
    }

    std::fs::create_dir_all(&target_dir).map_err(|e| e.to_string())?;

    println!("Bootstrapping Python for Evoker...");
    
    // Fetch latest release JSON
    let client = reqwest::blocking::Client::builder()
        .user_agent("evoker-host-bootstrap")
        .build()
        .map_err(|e| format!("Failed to build reqwest client: {}", e))?;
        
    let resp = client.get("https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest")
        .send()
        .map_err(|e| format!("Failed to fetch release info: {}", e))?;
        
    if !resp.status().is_success() {
        return Err(format!("Failed to fetch release info: HTTP {}", resp.status()));
    }
        
    let json_bytes = resp.bytes().map_err(|e| e.to_string())?;
    let json: serde_json::Value = serde_json::from_slice(&json_bytes).map_err(|e| e.to_string())?;
    
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
    
    let resp = client.get(&download_url)
        .send()
        .map_err(|e| format!("Failed to download python: {}", e))?;
        
    if !resp.status().is_success() {
        return Err(format!("Failed to download python: HTTP {}", resp.status()));
    }
    
    println!("Extracting python...");
    
    // Decompress the tar.gz stream directly into the target directory
    let tar = flate2::read::GzDecoder::new(resp);
    let mut archive = tar::Archive::new(tar);
    
    archive.unpack(&target_dir).map_err(|e| format!("Failed to extract python archive: {}", e))?;
    
    if exe_path.exists() {
        // Install the evoker runtime
        println!("Installing evoker runtime into bootstrapped python...");
        let mut repo_path = std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."));
        while !repo_path.join("evoker").join("pyproject.toml").exists() {
            if !repo_path.pop() {
                return Err("Could not find evoker package directory to install runtime".to_string());
            }
        }
        
        let evoker_package = repo_path.join("evoker");
        let pip_status = Command::new(&exe_path)
            .args(&["-m", "pip", "install", evoker_package.to_str().unwrap()])
            .output()
            .map_err(|e| e.to_string())?;
            
        if !pip_status.status.success() {
            return Err(format!("Failed to install evoker runtime via pip: {}", String::from_utf8_lossy(&pip_status.stderr)));
        }
        
        // Verify import succeeds
        let import_status = Command::new(&exe_path)
            .args(&["-c", "import evoker.worker"])
            .status()
            .map_err(|e| e.to_string())?;
            
        if !import_status.success() {
            return Err("Failed to import evoker.worker after installation".to_string());
        }
        
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
    token: String,
}

impl PluginClient {
    pub fn new<P: AsRef<Path>>(
        plugins_dir: P,
        strategies: Option<Vec<Strategy>>,
        injected_packages: Option<Vec<PathBuf>>,
    ) -> Self {
        use std::time::{SystemTime, UNIX_EPOCH};
        let token = format!("{:x}", SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos());
        Self {
            plugins_dir: plugins_dir.as_ref().to_path_buf(),
            strategies,
            injected_packages,
            worker_process: None,
            port: None,
            token,
        }
    }

    pub fn start_worker(&mut self, python_exe: Option<&str>, worker_target: &str) -> Result<(), String> {
        let actual_python = match python_exe {
            Some(p) => PathBuf::from(p),
            None => bootstrap_python()?
        };

        let mut actual_worker_target = worker_target.to_string();
        if !actual_worker_target.ends_with(".py") {
            let out = Command::new(&actual_python)
                .args(&["-c", &format!("import importlib.util, sys; spec = importlib.util.find_spec('{}'); sys.stdout.write(spec.origin if spec else '')", worker_target)])
                .output()
                .map_err(|e| format!("Failed to resolve module path: {}", e))?;
                
            if out.status.success() {
                let resolved = String::from_utf8_lossy(&out.stdout).trim().to_string();
                if !resolved.is_empty() {
                    actual_worker_target = resolved;
                }
            }
        }

        let mut cmd = Command::new(&actual_python);
        cmd.arg("-u"); // unbuffered
        cmd.arg(&actual_worker_target);
        cmd.env("EVOKER_AUTH_TOKEN", &self.token);
        
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
            loop {
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
                        } else {
                            print!("{}", line);
                        }
                    }
                    Err(_) => break,
                }
            }
            let _ = tx.send((found_port, reader));
        });

        match rx.recv_timeout(std::time::Duration::from_secs(120)) {
            Ok((Some(port), mut reader)) => {
                let stderr = child.stderr.take().expect("Failed to open stderr");
                thread::spawn(move || {
                    let mut err_reader = BufReader::new(stderr);
                    let mut l = String::new();
                    while let Ok(bytes) = err_reader.read_line(&mut l) {
                        if bytes == 0 { break; }
                        eprint!("{}", l);
                        l.clear();
                    }
                });

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
                let mut stderr_out = String::new();
                if let Some(mut stderr) = child.stderr.take() {
                    use std::io::Read;
                    let _ = stderr.read_to_string(&mut stderr_out);
                }
                Err(format!("Worker failed to start or output port in time. Stderr:\n{}", stderr_out))
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

    fn client(&self) -> reqwest::blocking::Client {
        use reqwest::header::{HeaderMap, HeaderValue};
        let mut headers = HeaderMap::new();
        if let Ok(val) = HeaderValue::from_str(&self.token) {
            headers.insert("X-Evoker-Auth", val);
        }
        reqwest::blocking::Client::builder()
            .default_headers(headers)
            .build()
            .unwrap()
    }

    pub fn get_url(&self) -> String {
        format!("http://127.0.0.1:{}", self.port.unwrap_or(0))
    }

    pub fn scan(&self) -> Result<Value, String> {
        let req = Request::new("scan");
        req.call(EvokerTransport(self.client().post(&self.get_url())))
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
            
        req.call(EvokerTransport(self.client().post(&self.get_url())))
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

pub fn json_to_xmlrpc(val: serde_json::Value) -> Result<xmlrpc::Value, String> {
    match val {
        serde_json::Value::Null => Ok(xmlrpc::Value::Nil),
        serde_json::Value::Bool(b) => Ok(xmlrpc::Value::Bool(b)),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                if i > 2147483647 || i < -2147483648 {
                    Err(format!("Integer {} exceeds XML-RPC limits", i))
                } else {
                    Ok(xmlrpc::Value::Int(i as i32))
                }
            } else if let Some(f) = n.as_f64() {
                Ok(xmlrpc::Value::Double(f))
            } else {
                Ok(xmlrpc::Value::Nil)
            }
        },
        serde_json::Value::String(s) => Ok(xmlrpc::Value::String(s)),
        serde_json::Value::Array(arr) => {
            let mut xml_arr = Vec::new();
            for item in arr {
                xml_arr.push(json_to_xmlrpc(item)?);
            }
            Ok(xmlrpc::Value::Array(xml_arr))
        },
        serde_json::Value::Object(obj) => {
            let mut xml_obj = std::collections::BTreeMap::new();
            for (k, v) in obj {
                xml_obj.insert(k, json_to_xmlrpc(v)?);
            }
            Ok(xmlrpc::Value::Struct(xml_obj))
        },
    }
}
