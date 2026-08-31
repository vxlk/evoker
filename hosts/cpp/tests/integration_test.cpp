#include <iostream>
#include <cstdlib>
#include <iostream>
#define ALWAYS_ASSERT(cond) do { if (!(cond)) { std::cerr << "Assertion failed: " << #cond << std::endl; std::abort(); } } while(0)
#include <filesystem>
#include "evoker_client.hpp"

int main() {
    // Current directory is likely build/hosts/cpp
    // We need to resolve path to test_assets
    std::filesystem::path current = std::filesystem::current_path();
    std::filesystem::path plugins_dir = current / ".." / ".." / "test_assets" / "plugins";
    std::filesystem::path src_dir = current / ".." / ".." / "python" / "src";
    std::string worker_script = "evoker.worker";

    if (!std::filesystem::exists(plugins_dir)) {
        if (std::filesystem::exists(current / "hosts" / "test_assets" / "plugins")) {
            plugins_dir = current / "hosts" / "test_assets" / "plugins";
            src_dir = current / "hosts" / "python" / "src";
        } else if (std::filesystem::exists(current / ".." / ".." / ".." / "test_assets" / "plugins")) {
            plugins_dir = current / ".." / ".." / ".." / "test_assets" / "plugins";
            src_dir = current / ".." / ".." / ".." / "python" / "src";
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
    ALWAYS_ASSERT(started && "Failed to start worker");

    auto manifest = client.scan();
    ALWAYS_ASSERT(manifest.contains("test_plugin") && "Scan did not return test_plugin");

    nlohmann::json kwargs = {{"name", "C++ Developer"}};
    auto result = client.invoke("test_plugin", "hello_world", kwargs);
    
    ALWAYS_ASSERT(result.is_string() && result.get<std::string>() == "Hello, C++ Developer!");

    std::cout << "Integration test passed successfully!" << std::endl;
    return 0;
}

