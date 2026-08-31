#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

typedef struct evoker_client_t evoker_client_t;

// Returns the last error message for the current thread, or NULL if no error occurred.
const char* evoker_last_error();

// Creates a new client. Returns NULL on failure.
// `strategies_json` and `injected_packages_json` can be NULL.
evoker_client_t* evoker_client_create(const char* plugins_dir, 
                                      const char* strategies_json, 
                                      const char* injected_packages_json);

// Starts the worker. Returns 1 on success, 0 on failure.
int evoker_client_start_worker(evoker_client_t* client, const char* python_exe, const char* worker_script);

// Scans for plugins. Returns a dynamically allocated JSON string on success, NULL on failure.
// Caller must free the returned string using evoker_client_free_string().
char* evoker_client_scan(evoker_client_t* client);

// Invokes a plugin action. kwargs_json must be a JSON object string.
// Returns a dynamically allocated JSON string on success, NULL on failure.
// Caller must free the returned string using evoker_client_free_string().
char* evoker_client_invoke(evoker_client_t* client, 
                           const char* plugin_name, 
                           const char* action_name, 
                           const char* kwargs_json);

// Destroys the client and cleans up resources.
void evoker_client_destroy(evoker_client_t* client);

// Frees a string allocated by the client.
void evoker_client_free_string(char* str);

#ifdef __cplusplus
}
#endif
