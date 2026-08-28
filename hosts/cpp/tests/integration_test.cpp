#include <iostream>
#include <cassert>
#include <filesystem>
#include "evoker_client.hpp"

int main() {
    // Current directory is likely build/hosts/cpp
    // We need to resolve path to test_assets
    std::filesystem::path current = std::filesystem::current_path();
    std::filesystem::path plugins_dir = current / ".." / ".." / "test_assets" / "plugins";
    std::filesystem::path src_dir = current / ".." / ".." / "python" / "src";
    std::string worker_script = "plugin_host.worker";

    if (!std::filesystem::exists(plugins_dir)) {
        if (std::filesystem::exists(current / "hosts" / "test_assets" / "plugins")) {
            plugins_dir = current / "hosts" / "test_assets" / "plugins";
            src_dir = current / "hosts" / "python" / "src";
        } else {
            plugins_dir = current / ".." / "test_assets" / "plugins";
            src_dir = current / ".." / "python" / "src";
        }
    }

#ifdef _WIN32
    _putenv_s("PYTHONPATH", src_dir.string().c_str());
#else
    setenv("PYTHONPATH", src_dir.string().c_str(), 1);
#endif

    evoker::PluginClient client(plugins_dir.string());
    
    std::cout << "Starting C++ integration test..." << std::endl;
    bool started = client.start_worker("python", worker_script);
    assert(started && "Failed to start worker");

    auto manifest = client.scan();
    assert(manifest.contains("test_plugin") && "Scan did not return test_plugin");

    nlohmann::json kwargs = {{"name", "C++ Developer"}};
    auto result = client.invoke("test_plugin", "hello_world", kwargs);
    
    assert(result.is_string() && result.get<std::string>() == "Hello, C++ Developer!");

    std::cout << "Integration test passed successfully!" << std::endl;
    return 0;
}
