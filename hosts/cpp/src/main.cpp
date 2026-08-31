#include "evoker_client.hpp"
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    if (argc < 4) {
        std::cerr << "Usage: evoker_cpp_host <plugins_dir> <plugin_name> <action_name> [json_args]" << std::endl;
        return 1;
    }
    
    std::string plugins_dir = argv[1];
    std::string plugin_name = argv[2];
    std::string action = argv[3];
    nlohmann::json args = nlohmann::json::object();
    if (argc >= 5) {
        args = nlohmann::json::parse(argv[4]);
    }

    evoker::PluginClient client(plugins_dir);
    if (!client.start_worker("python", "plugin_host.worker")) {
        std::cerr << "Failed to start worker" << std::endl;
        return 1;
    }
    
    try {
        nlohmann::json res = client.invoke(plugin_name, action, args);
        std::cout << res.dump(4) << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}
