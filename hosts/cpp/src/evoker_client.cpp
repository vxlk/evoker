#include "evoker_client.hpp"
#include <iostream>
#include <thread>
#include <chrono>
#include <tinyxml2.h>
#include <sstream>
#include <httplib.h>
#include <reproc++/reproc.hpp>
#include <reproc++/drain.hpp>

namespace evoker {

static std::string xmlrpc_escape(const std::string& str) {
    std::string res;
    for (char c : str) {
        if (c == '<') res += "&lt;";
        else if (c == '>') res += "&gt;";
        else if (c == '&') res += "&amp;";
        else res += c;
    }
    return res;
}

static std::string json_to_xmlrpc(const nlohmann::json& j) {
    if (j.is_string()) {
        return "<value><string>" + xmlrpc_escape(j.get<std::string>()) + "</string></value>";
    } else if (j.is_number_integer()) {
        return "<value><int>" + std::to_string(j.get<int>()) + "</int></value>";
    } else if (j.is_number_float()) {
        return "<value><double>" + std::to_string(j.get<double>()) + "</double></value>";
    } else if (j.is_boolean()) {
        return "<value><boolean>" + std::string(j.get<bool>() ? "1" : "0") + "</boolean></value>";
    } else if (j.is_array()) {
        std::string xml = "<value><array><data>";
        for (const auto& item : j) {
            xml += json_to_xmlrpc(item);
        }
        xml += "</data></array></value>";
        return xml;
    } else if (j.is_object()) {
        std::string xml = "<value><struct>";
        for (auto it = j.begin(); it != j.end(); ++it) {
            xml += "<member><name>" + xmlrpc_escape(it.key()) + "</name>";
            xml += json_to_xmlrpc(it.value());
            xml += "</member>";
        }
        xml += "</struct></value>";
        return xml;
    } else if (j.is_null()) {
        return "<value><nil/></value>";
    }
    return "<value><string></string></value>"; // fallback
}

PluginClient::PluginClient(const std::string& plugins_dir, 
                           std::optional<std::vector<Strategy>> strategies,
                           std::optional<std::vector<std::string>> injected_packages)
    : m_plugins_dir(plugins_dir), 
      m_strategies(std::move(strategies)), 
      m_injected_packages(std::move(injected_packages)),
      m_port(0),
      m_running(false) {
}

PluginClient::~PluginClient() {
    stop_worker();
}

static std::string bootstrap_python() {
#ifdef _WIN32
    std::string home = getenv("USERPROFILE") ? getenv("USERPROFILE") : ".";
    std::string triple = "x86_64-pc-windows-msvc";
    std::string exe_name = "python.exe";
#elif defined(__APPLE__)
    std::string home = getenv("HOME") ? getenv("HOME") : ".";
    #if defined(__aarch64__) || defined(_M_ARM64)
    std::string triple = "aarch64-apple-darwin";
    #else
    std::string triple = "x86_64-apple-darwin";
    #endif
    std::string exe_name = "bin/python3";
#else
    std::string home = getenv("HOME") ? getenv("HOME") : ".";
    #if defined(__aarch64__) || defined(_M_ARM64)
    std::string triple = "aarch64-unknown-linux-gnu";
    #else
    std::string triple = "x86_64-unknown-linux-gnu";
    #endif
    std::string exe_name = "bin/python3";
#endif

    std::filesystem::path evoker_dir = std::filesystem::path(home) / ".evoker" / "python";
    std::filesystem::path target_dir = evoker_dir / ("python-3.13-" + triple);
    std::filesystem::path exe_path = target_dir / "python" / exe_name;

    if (std::filesystem::exists(exe_path)) {
        return exe_path.string();
    }

    std::filesystem::create_directories(target_dir);
    std::cout << "Bootstrapping Python for Evoker..." << std::endl;

    // Use a hardcoded known URL for reliability in C++ to avoid needing a JSON parser for the github API here
    std::string download_url = "https://github.com/astral-sh/python-build-standalone/releases/download/20260825/cpython-3.13.15%2B20260825-" + triple + "-install_only.tar.gz";
    std::filesystem::path archive_path = evoker_dir / "python.tar.gz";

    std::cout << "Downloading " << download_url << " ..." << std::endl;
    reproc::process curl;
    std::vector<std::string> curl_args = {"curl", "-sL", download_url, "-o", archive_path.string()};
    if (curl.start(curl_args) || curl.wait(reproc::infinite).first != 0) {
        std::cerr << "Failed to download python" << std::endl;
        return "";
    }

    std::cout << "Extracting python..." << std::endl;
    reproc::process tar;
    std::vector<std::string> tar_args = {"tar", "-xf", archive_path.string(), "-C", target_dir.string()};
    if (tar.start(tar_args) || tar.wait(reproc::infinite).first != 0) {
        std::cerr << "Failed to extract python" << std::endl;
        return "";
    }

    std::filesystem::remove(archive_path);

    if (std::filesystem::exists(exe_path)) {
        std::cout << "Installing evoker package..." << std::endl;
        reproc::process pip;
        std::vector<std::string> pip_args = {exe_path.string(), "-m", "pip", "install", "evoker"};
        pip.start(pip_args);
        pip.wait(reproc::infinite);
        return exe_path.string();
    }

    return "";
}

bool PluginClient::start_worker(const std::string& python_exe, const std::string& worker_script) {
    std::string actual_python = python_exe;
    if (actual_python.empty() || actual_python == "bootstrap") {
        actual_python = bootstrap_python();
        if (actual_python.empty()) {
            std::cerr << "Failed to bootstrap python" << std::endl;
            return false;
        }
    }

    reproc::options options;
    options.redirect.err.type = reproc::redirect::pipe;
    options.redirect.out.type = reproc::redirect::pipe;
    
    std::vector<std::string> args = {actual_python, "-u"};
    if (worker_script.size() >= 3 && worker_script.substr(worker_script.size() - 3) == ".py") {
        args.push_back(worker_script);
    } else {
        args.push_back("-m");
        args.push_back(worker_script);
    }
    args.push_back(m_plugins_dir);
    
    // Set environment variables
    std::map<std::string, std::string> env;
    if (m_strategies) {
        nlohmann::json j = nlohmann::json::array();
        for (const auto& s : *m_strategies) j.push_back(s.to_json());
        env["EVOKER_STRATEGIES"] = j.dump();
    }
    if (m_injected_packages) {
        nlohmann::json j = *m_injected_packages;
        env["EVOKER_INJECTED_PACKAGES"] = j.dump();
    }
    if (!env.empty()) {
        options.env.extra = reproc::env(env);
    }

    m_process = std::make_unique<reproc::process>();
    std::error_code ec = m_process->start(args, options);
    if (ec) {
        std::cerr << "Failed to start process: " << ec.message() << std::endl;
        return false;
    }

    m_running = true;

    // Read stdout line by line looking for RPC_PORT
    std::string stdout_buffer;
    bool found_port = false;
    
    // Simple reader lambda
    auto read_line = [&]() -> std::string {
        std::string line;
        uint8_t buffer[1];
        while (true) {
            auto [bytes, ec] = m_process->read(reproc::stream::out, buffer, 1);
            if (ec || bytes == 0) break;
            char c = static_cast<char>(buffer[0]);
            if (c == '\n') break;
            if (c != '\r') line += c;
        }
        return line;
    };

    for (int i = 0; i < 50; ++i) {
        std::string line = read_line();
        if (line.empty()) {
            break;
        }
        
        if (line.rfind("RPC_PORT:", 0) == 0) { // starts_with
            try {
                m_port = std::stoi(line.substr(9));
                found_port = true;
                break;
            } catch (...) {}
        }
    }

    if (!found_port) {
        stop_worker();
        return false;
    }

    // Launch a background thread to sink the rest of stdout/stderr
    std::thread([this]() {
        reproc::drain(*m_process, reproc::sink::ostream(std::cout), reproc::sink::ostream(std::cerr));
    }).detach();

    return true;
}

void PluginClient::stop_worker() {
    if (m_running && m_process) {
        m_process->terminate();
        m_process->wait(reproc::milliseconds(2000));
        m_process->kill();
        m_running = false;
    }
}

std::string PluginClient::build_xmlrpc_request(const std::string& method_name, const std::vector<nlohmann::json>& params) {
    std::string xml = "<?xml version=\"1.0\"?><methodCall><methodName>" + xmlrpc_escape(method_name) + "</methodName><params>";
    for (const auto& p : params) {
        xml += "<param>" + json_to_xmlrpc(p) + "</param>";
    }
    xml += "</params></methodCall>";
    return xml;
}

nlohmann::json PluginClient::parse_xmlrpc_value(const void* xml_node_ptr) {
    const tinyxml2::XMLElement* value_elem = static_cast<const tinyxml2::XMLElement*>(xml_node_ptr);
    if (!value_elem) return nlohmann::json();
    
    const tinyxml2::XMLElement* child = value_elem->FirstChildElement();
    if (!child) {
        // Just text inside value? Or empty string.
        const char* text = value_elem->GetText();
        return text ? nlohmann::json(std::string(text)) : nlohmann::json("");
    }
    
    std::string type = child->Name();
    if (type == "string") {
        const char* text = child->GetText();
        return nlohmann::json(text ? text : "");
    } else if (type == "int" || type == "i4") {
        const char* text = child->GetText();
        return nlohmann::json(text ? std::stoi(text) : 0);
    } else if (type == "double") {
        const char* text = child->GetText();
        return nlohmann::json(text ? std::stod(text) : 0.0);
    } else if (type == "boolean") {
        const char* text = child->GetText();
        return nlohmann::json(text && std::string(text) == "1");
    } else if (type == "array") {
        nlohmann::json arr = nlohmann::json::array();
        const tinyxml2::XMLElement* data = child->FirstChildElement("data");
        if (data) {
            for (const tinyxml2::XMLElement* v = data->FirstChildElement("value"); v; v = v->NextSiblingElement("value")) {
                arr.push_back(parse_xmlrpc_value(v));
            }
        }
        return arr;
    } else if (type == "struct") {
        nlohmann::json obj = nlohmann::json::object();
        for (const tinyxml2::XMLElement* member = child->FirstChildElement("member"); member; member = member->NextSiblingElement("member")) {
            const tinyxml2::XMLElement* name_elem = member->FirstChildElement("name");
            const tinyxml2::XMLElement* value_elem = member->FirstChildElement("value");
            if (name_elem && value_elem) {
                const char* name_text = name_elem->GetText();
                if (name_text) {
                    obj[name_text] = parse_xmlrpc_value(value_elem);
                }
            }
        }
        return obj;
    }
    return nlohmann::json();
}

nlohmann::json PluginClient::parse_xmlrpc_response(const std::string& xml_content) {
    tinyxml2::XMLDocument doc;
    if (doc.Parse(xml_content.c_str()) != tinyxml2::XML_SUCCESS) {
        throw std::runtime_error("Failed to parse XML-RPC response");
    }
    
    const tinyxml2::XMLElement* method_response = doc.FirstChildElement("methodResponse");
    if (!method_response) throw std::runtime_error("Invalid XML-RPC response");
    
    const tinyxml2::XMLElement* fault = method_response->FirstChildElement("fault");
    if (fault) {
        const tinyxml2::XMLElement* value = fault->FirstChildElement("value");
        nlohmann::json fault_json = parse_xmlrpc_value(value);
        throw std::runtime_error("RPC Fault: " + fault_json.dump());
    }
    
    const tinyxml2::XMLElement* params = method_response->FirstChildElement("params");
    if (params) {
        const tinyxml2::XMLElement* param = params->FirstChildElement("param");
        if (param) {
            const tinyxml2::XMLElement* value = param->FirstChildElement("value");
            return parse_xmlrpc_value(value);
        }
    }
    return nlohmann::json();
}

nlohmann::json PluginClient::scan() {
    std::string req = build_xmlrpc_request("scan", {});
    httplib::Client cli("localhost", m_port);
    auto res = cli.Post("/", req, "text/xml");
    if (res && res->status == 200) {
        return parse_xmlrpc_response(res->body);
    }
    throw std::runtime_error("HTTP error or connection failed");
}

nlohmann::json PluginClient::invoke(const std::string& plugin_name, 
                                    const std::string& action_name, 
                                    const nlohmann::json& kwargs) {
    std::string req = build_xmlrpc_request("invoke", {plugin_name, action_name, kwargs});
    httplib::Client cli("localhost", m_port);
    auto res = cli.Post("/", req, "text/xml");
    if (res && res->status == 200) {
        return parse_xmlrpc_response(res->body);
    }
    throw std::runtime_error("HTTP error or connection failed");
}

} // namespace evoker
