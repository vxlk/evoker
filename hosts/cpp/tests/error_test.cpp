#include <iostream>
#include <cstdlib>
#include <iostream>
#define ALWAYS_ASSERT(cond) do { if (!(cond)) { std::cerr << "Assertion failed: " << #cond << std::endl; std::abort(); } } while(0)
#include <filesystem>
#include <fstream>
#include "evoker_client.hpp"

int main() {
    std::filesystem::path current = std::filesystem::current_path();
    std::filesystem::path plugins_dir = current / ".." / ".." / "test_assets" / "plugins";
    std::filesystem::path src_dir = current / ".." / ".." / "python" / "src";
    std::filesystem::path test_assets = current / ".." / ".." / "test_assets";

    if (!std::filesystem::exists(plugins_dir)) {
        if (std::filesystem::exists(current / "hosts" / "test_assets" / "plugins")) {
            plugins_dir = current / "hosts" / "test_assets" / "plugins";
            src_dir = current / "hosts" / "python" / "src";
            test_assets = current / "hosts" / "test_assets";
        } else {
            plugins_dir = current / ".." / "test_assets" / "plugins";
            src_dir = current / ".." / "python" / "src";
            test_assets = current / ".." / "test_assets";
        }
    }

#ifdef _WIN32
    _putenv_s("PYTHONPATH", src_dir.string().c_str());
#else
    setenv("PYTHONPATH", src_dir.string().c_str(), 1);
#endif

    // Test 1: Worker crash / immediate exit
    {
        std::filesystem::path dummy_script = test_assets / "crashing_worker.py";
        std::ofstream ofs(dummy_script);
        ofs << "import sys\nsys.exit(1)\n";
        ofs.close();

        evoker::PluginClient client(plugins_dir.string());
        bool started = client.start_worker("python", dummy_script.string());
        ALWAYS_ASSERT(!started && "Should fail to start if worker crashes immediately");
        
        std::filesystem::remove(dummy_script);
    }

    // Test 2: Stdout flooding without RPC_PORT
    {
        std::filesystem::path dummy_script = test_assets / "flooding_worker.py";
        std::ofstream ofs(dummy_script);
        ofs << "import sys, time\n";
        ofs << "for i in range(100):\n";
        ofs << "    print('JUNK LOG LINE', i)\n";
        ofs << "sys.exit(1)\n";
        ofs.close();

        evoker::PluginClient client(plugins_dir.string());
        bool started = client.start_worker("python", dummy_script.string());
        ALWAYS_ASSERT(!started && "Should fail to start if port is never printed despite flooding");
        
        std::filesystem::remove(dummy_script);
    }

    // Test 3: Invalid executable
    {
        evoker::PluginClient client(plugins_dir.string());
        bool started = client.start_worker("this_executable_does_not_exist_123", "dummy");
        ALWAYS_ASSERT(!started && "Should fail when given a bad executable");
    }

    std::cout << "Error recovery tests passed!" << std::endl;
    return 0;
}

