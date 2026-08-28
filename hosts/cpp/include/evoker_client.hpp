#pragma once

#include <string>
#include <vector>
#include <map>
#include <memory>
#include <optional>
#include <nlohmann/json.hpp>

namespace reproc { class process; }

namespace evoker {

struct Strategy {
    std::string type;
    std::string value;
    std::vector<std::string> args;
    
    nlohmann::json to_json() const {
        nlohmann::json j;
        j["type"] = type;
        j["value"] = value;
        if (!args.empty()) {
            j["args"] = args;
        }
        return j;
    }
};

class PluginClient {
public:
    PluginClient(const std::string& plugins_dir, 
                 std::optional<std::vector<Strategy>> strategies = std::nullopt,
                 std::optional<std::vector<std::string>> injected_packages = std::nullopt);
                 
    ~PluginClient();

    bool start_worker(const std::string& python_exe, const std::string& worker_script);
    void stop_worker();
    
    // Returns JSON representation of the manifest
    nlohmann::json scan();
    
    // Invokes a plugin. Arguments and return value are JSON values
    nlohmann::json invoke(const std::string& plugin_name, 
                          const std::string& action_name, 
                          const nlohmann::json& kwargs);

#ifdef EVOKER_CLIENT_TESTING
public:
#else
private:
#endif
    std::string build_xmlrpc_request(const std::string& method_name, const std::vector<nlohmann::json>& params);
    nlohmann::json parse_xmlrpc_response(const std::string& xml_content);
    nlohmann::json parse_xmlrpc_value(const void* xml_node); // opaque pointer to tinyxml2 element

    std::string m_plugins_dir;
    std::optional<std::vector<Strategy>> m_strategies;
    std::optional<std::vector<std::string>> m_injected_packages;
    
    std::unique_ptr<reproc::process> m_process;
    uint16_t m_port;
    bool m_running;
};

} // namespace evoker
