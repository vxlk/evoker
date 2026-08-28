#include "evoker_client_c.h"
#include "../../cpp/include/evoker_client.hpp"
#include <cstring>
#include <cstdlib>

using namespace evoker;

extern "C" {

evoker_client_t* evoker_client_create(const char* plugins_dir, 
                                      const char* strategies_json, 
                                      const char* injected_packages_json) {
    if (!plugins_dir) return nullptr;
    
    std::optional<std::vector<Strategy>> strats;
    if (strategies_json) {
        try {
            auto j = nlohmann::json::parse(strategies_json);
            std::vector<Strategy> v;
            for (const auto& item : j) {
                Strategy s;
                s.type = item.value("type", "");
                s.value = item.value("value", "");
                if (item.contains("args") && item["args"].is_array()) {
                    for (const auto& arg : item["args"]) {
                        s.args.push_back(arg.get<std::string>());
                    }
                }
                v.push_back(s);
            }
            strats = v;
        } catch (...) {
            return nullptr;
        }
    }
    
    std::optional<std::vector<std::string>> injected;
    if (injected_packages_json) {
        try {
            auto j = nlohmann::json::parse(injected_packages_json);
            std::vector<std::string> v;
            for (const auto& item : j) {
                v.push_back(item.get<std::string>());
            }
            injected = v;
        } catch (...) {
            return nullptr;
        }
    }
    
    try {
        PluginClient* client = new PluginClient(plugins_dir, strats, injected);
        return reinterpret_cast<evoker_client_t*>(client);
    } catch (...) {
        return nullptr;
    }
}

int evoker_client_start_worker(evoker_client_t* client, const char* python_exe, const char* worker_script) {
    if (!client || !python_exe || !worker_script) return 0;
    PluginClient* c = reinterpret_cast<PluginClient*>(client);
    return c->start_worker(python_exe, worker_script) ? 1 : 0;
}

char* evoker_client_scan(evoker_client_t* client) {
    if (!client) return nullptr;
    PluginClient* c = reinterpret_cast<PluginClient*>(client);
    
    try {
        nlohmann::json res = c->scan();
        std::string s = res.dump();
        char* out = (char*)malloc(s.length() + 1);
        std::strcpy(out, s.c_str());
        return out;
    } catch (...) {
        return nullptr;
    }
}

char* evoker_client_invoke(evoker_client_t* client, 
                           const char* plugin_name, 
                           const char* action_name, 
                           const char* kwargs_json) {
    if (!client || !plugin_name || !action_name || !kwargs_json) return nullptr;
    PluginClient* c = reinterpret_cast<PluginClient*>(client);
    
    try {
        auto kwargs = nlohmann::json::parse(kwargs_json);
        nlohmann::json res = c->invoke(plugin_name, action_name, kwargs);
        std::string s = res.dump();
        char* out = (char*)malloc(s.length() + 1);
        std::strcpy(out, s.c_str());
        return out;
    } catch (...) {
        return nullptr;
    }
}

void evoker_client_destroy(evoker_client_t* client) {
    if (client) {
        PluginClient* c = reinterpret_cast<PluginClient*>(client);
        delete c;
    }
}

void evoker_client_free_string(char* str) {
    if (str) {
        free(str);
    }
}

}
