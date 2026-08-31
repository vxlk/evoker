#include "evoker_client.hpp"
#include <tinyxml2.h>
#include <cstdlib>
#include <iostream>
#define ALWAYS_ASSERT(cond) do { if (!(cond)) { std::cerr << "Assertion failed: " << #cond << std::endl; std::abort(); } } while(0)
#include <iostream>

void test_json_to_xmlrpc() {
    using nlohmann::json;
    evoker::PluginClient dummy("");
    
    json j_str = "hello <world>&";
    std::string xml_str = dummy.build_xmlrpc_request("test", {j_str});
    ALWAYS_ASSERT(xml_str.find("<value><string>hello &lt;world&gt;&amp;</string></value>") != std::string::npos);

    json j_int = 42;
    std::string xml_int = dummy.build_xmlrpc_request("test", {j_int});
    ALWAYS_ASSERT(xml_int.find("<value><int>42</int></value>") != std::string::npos);

    json j_bool = true;
    std::string xml_bool = dummy.build_xmlrpc_request("test", {j_bool});
    ALWAYS_ASSERT(xml_bool.find("<value><boolean>1</boolean></value>") != std::string::npos);

    json j_arr = json::array({1, "two"});
    std::string xml_arr = dummy.build_xmlrpc_request("test", {j_arr});
    ALWAYS_ASSERT(xml_arr.find("<value><array><data><value><int>1</int></value><value><string>two</string></value></data></array></value>") != std::string::npos);

    json j_obj = {{"key", "value"}};
    std::string xml_obj = dummy.build_xmlrpc_request("test", {j_obj});
    ALWAYS_ASSERT(xml_obj.find("<value><struct><member><name>key</name><value><string>value</string></value></member></struct></value>") != std::string::npos);
}

void test_parse_xmlrpc_value() {
    evoker::PluginClient dummy("");
    
    std::string xml = R"(
    <value>
        <struct>
            <member>
                <name>name</name>
                <value><string>John Doe</string></value>
            </member>
            <member>
                <name>age</name>
                <value><int>30</int></value>
            </member>
            <member>
                <name>scores</name>
                <value>
                    <array>
                        <data>
                            <value><double>95.5</double></value>
                            <value><boolean>1</boolean></value>
                        </data>
                    </array>
                </value>
            </member>
        </struct>
    </value>
    )";

    tinyxml2::XMLDocument doc;
    doc.Parse(xml.c_str());
    
    nlohmann::json j = dummy.parse_xmlrpc_value(doc.FirstChildElement("value"));
    
    ALWAYS_ASSERT(j.is_object());
    ALWAYS_ASSERT(j["name"] == "John Doe");
    ALWAYS_ASSERT(j["age"] == 30);
    ALWAYS_ASSERT(j["scores"].is_array());
    ALWAYS_ASSERT(j["scores"][0] == 95.5);
    ALWAYS_ASSERT(j["scores"][1] == true);
}

int main() {
    test_json_to_xmlrpc();
    test_parse_xmlrpc_value();
    std::cout << "Unit tests passed!" << std::endl;
    return 0;
}

