#include "evoker_client_c.h"
#include "../../cpp/include/evoker_client.hpp"
#include <cstring>
#include <cstdlib>

using namespace evoker;

extern "C" {

thread_local std::string g_last_error;

const char* evoker_last_error() {
    return g_last_error.empty() ? nullptr : g_last_error.c_str();
}

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
        } catch (const std::exception& e) {
            g_last_error = e.what();
            return nullptr;
        } catch (...) {
            g_last_error = "Unknown error in strategies parse";
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
        } catch (const std::exception& e) {
            g_last_error = e.what();
            return nullptr;
        } catch (...) {
            g_last_error = "Unknown error in injected_packages parse";
            return nullptr;
        }
    }
    
    try {
        PluginClient* client = new PluginClient(plugins_dir, strats, injected);
        g_last_error.clear();
        return reinterpret_cast<evoker_client_t*>(client);
    } catch (const std::exception& e) {
        g_last_error = e.what();
        return nullptr;
    } catch (...) {
        g_last_error = "Unknown error creating client";
        return nullptr;
    }
}

int evoker_client_start_worker(evoker_client_t* client, const char* python_exe, const char* worker_script) {
    if (!client || !python_exe || !worker_script) {
        g_last_error = "Invalid arguments";
        return 0;
    }
    PluginClient* c = reinterpret_cast<PluginClient*>(client);
    bool res = c->start_worker(python_exe, worker_script);
    if (!res) {
        g_last_error = "start_worker failed";
    } else {
        g_last_error.clear();
    }
    return res ? 1 : 0;
}

char* evoker_client_scan(evoker_client_t* client) {
    if (!client) {
        g_last_error = "Invalid client";
        return nullptr;
    }
    PluginClient* c = reinterpret_cast<PluginClient*>(client);
    
    try {
        nlohmann::json res = c->scan();
        std::string s = res.dump();
        char* out = (char*)malloc(s.length() + 1);
        if (!out) {
            g_last_error = "Out of memory";
            return nullptr;
        }
        std::strcpy(out, s.c_str());
        g_last_error.clear();
        return out;
    } catch (const std::exception& e) {
        g_last_error = e.what();
        return nullptr;
    } catch (...) {
        g_last_error = "Unknown error during scan";
        return nullptr;
    }
}

char* evoker_client_invoke(evoker_client_t* client, 
                           const char* plugin_name, 
                           const char* action_name, 
                           const char* kwargs_json) {
    if (!client || !plugin_name || !action_name || !kwargs_json) {
        g_last_error = "Invalid arguments";
        return nullptr;
    }
    PluginClient* c = reinterpret_cast<PluginClient*>(client);
    
    try {
        auto kwargs = nlohmann::json::parse(kwargs_json);
        nlohmann::json res = c->invoke(plugin_name, action_name, kwargs);
        std::string s = res.dump();
        char* out = (char*)malloc(s.length() + 1);
        if (!out) {
            g_last_error = "Out of memory";
            return nullptr;
        }
        std::strcpy(out, s.c_str());
        g_last_error.clear();
        return out;
    } catch (const std::exception& e) {
        g_last_error = e.what();
        return nullptr;
    } catch (...) {
        g_last_error = "Unknown error during invoke";
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
