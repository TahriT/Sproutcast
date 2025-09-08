#pragma once

#include <string>

class MqttClient {
public:
    MqttClient(const std::string &host, int port);
    ~MqttClient();

    bool connect();
    bool publish(const std::string &topic, const std::string &payload, int qos = 0, bool retain = false);
    void disconnect();

private:
    std::string host_;
    int port_;
    int sock_;
};

