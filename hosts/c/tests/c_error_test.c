#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "evoker_client_c.h"

int main() {
    const char* plugins_dir = "../../test_assets/plugins";
    const char* src_dir = "../../python/src";
    const char* test_assets = "../../test_assets";

    FILE* f = fopen("../../test_assets/plugins/test_plugin/manifest.json", "r");
    if (!f) {
        f = fopen("hosts/test_assets/plugins/test_plugin/manifest.json", "r");
        if (f) {
            plugins_dir = "hosts/test_assets/plugins";
            src_dir = "hosts/python/src";
            test_assets = "hosts/test_assets";
            fclose(f);
        } else {
            plugins_dir = "../test_assets/plugins";
            src_dir = "../python/src";
            test_assets = "../test_assets";
        }
    } else {
        fclose(f);
    }

#ifdef _WIN32
    _putenv_s("PYTHONPATH", src_dir);
#else
    setenv("PYTHONPATH", src_dir, 1);
#endif

    // Test 1: Worker crash / immediate exit
    {
        char dummy_script[512];
        snprintf(dummy_script, sizeof(dummy_script), "%s/crashing_worker.py", test_assets);
        
        FILE* s = fopen(dummy_script, "w");
        if (s) {
            fprintf(s, "import sys\nsys.exit(1)\n");
            fclose(s);
        }

        evoker_client_t* client = evoker_client_create(plugins_dir, NULL, NULL);
        assert(client != NULL);
        
        int started = evoker_client_start_worker(client, "python", dummy_script);
        assert(started == 0 && "Should fail to start if worker crashes immediately");
        
        evoker_client_destroy(client);
        remove(dummy_script);
    }

    // Test 2: Stdout flooding without RPC_PORT
    {
        char dummy_script[512];
        snprintf(dummy_script, sizeof(dummy_script), "%s/flooding_worker.py", test_assets);
        
        FILE* s = fopen(dummy_script, "w");
        if (s) {
            fprintf(s, "import sys, time\n");
            fprintf(s, "for i in range(100):\n");
            fprintf(s, "    print('JUNK LOG LINE', i)\n");
            fprintf(s, "sys.exit(1)\n");
            fclose(s);
        }

        evoker_client_t* client = evoker_client_create(plugins_dir, NULL, NULL);
        
        int started = evoker_client_start_worker(client, "python", dummy_script);
        assert(started == 0 && "Should fail to start if port is never printed despite flooding");
        
        evoker_client_destroy(client);
        remove(dummy_script);
    }

    // Test 3: Invalid executable
    {
        evoker_client_t* client = evoker_client_create(plugins_dir, NULL, NULL);
        int started = evoker_client_start_worker(client, "this_executable_does_not_exist_123", "dummy");
        assert(started == 0 && "Should fail when given a bad executable");
        evoker_client_destroy(client);
    }

    printf("C Error recovery tests passed!\n");
    return 0;
}
