#include "mqtt_client.hpp"

#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cstring>
#include <iostream>

namespace {
// Minimal MQTT 3.1.1 client (connect and publish) without external deps

bool write_all(int fd, const void* data, size_t len) {
    const uint8_t* ptr = static_cast<const uint8_t*>(data);
    size_t total = 0;
    while (total < len) {
        ssize_t n = ::send(fd, ptr + total, len - total, 0);
        if (n <= 0) return false;
        total += static_cast<size_t>(n);
    }
    return true;
}

std::string encode_varint(uint32_t value) {
    std::string out;
    do {
        uint8_t encoded_byte = value % 128;
        value /= 128;
        if (value > 0) encoded_byte |= 128;
        out.push_back(static_cast<char>(encoded_byte));
    } while (value > 0);
    return out;
}

void append_utf8_string(std::string &buf, const std::string &s) {
    uint16_t len = htons(static_cast<uint16_t>(s.size()));
    buf.append(reinterpret_cast<const char*>(&len), 2);
    buf.append(s);
}
}

MqttClient::MqttClient(const std::string &host, int port)
    : host_(host), port_(port), sock_(-1) {}

MqttClient::~MqttClient() { disconnect(); }

bool MqttClient::connect() {
    struct addrinfo hints{}; hints.ai_family = AF_UNSPEC; hints.ai_socktype = SOCK_STREAM; hints.ai_protocol = IPPROTO_TCP;
    struct addrinfo* res = nullptr;
    std::string port_str = std::to_string(port_);
    if (::getaddrinfo(host_.c_str(), port_str.c_str(), &hints, &res) != 0) {
        return false;
    }

    int fd = -1;
    for (auto p = res; p != nullptr; p = p->ai_next) {
        fd = ::socket(p->ai_family, p->ai_socktype, p->ai_protocol);
        if (fd == -1) continue;
        if (::connect(fd, p->ai_addr, p->ai_addrlen) == 0) break;
        ::close(fd);
        fd = -1;
    }
    ::freeaddrinfo(res);
    if (fd == -1) return false;
    sock_ = fd;

    // Build CONNECT packet
    std::string payload;
    append_utf8_string(payload, "MQTT"); // Protocol Name
    payload.push_back(0x04); // Protocol Level 4

    uint8_t connect_flags = 0x02; // Clean Session
    payload.push_back(static_cast<char>(connect_flags));

    uint16_t keepalive = htons(60);
    payload.append(reinterpret_cast<const char*>(&keepalive), 2);

    append_utf8_string(payload, "plantvision-client");

    std::string remaining_length = encode_varint(static_cast<uint32_t>(payload.size()));
    std::string packet;
    packet.push_back(0x10); // CONNECT
    packet += remaining_length;
    packet += payload;

    if (!write_all(sock_, packet.data(), packet.size())) {
        disconnect();
        return false;
    }

    // Read CONNACK (minimal)
    uint8_t header[4];
    ssize_t n = ::recv(sock_, header, sizeof(header), 0);
    if (n < 4 || header[0] != 0x20 || header[1] < 2 || header[3] != 0x00) {
        disconnect();
        return false;
    }
    return true;
}

bool MqttClient::publish(const std::string &topic, const std::string &payload, int qos, bool retain) {
    if (sock_ == -1) return false;
    (void)qos; // Only QoS 0 in this minimal client

    std::string var_header;
    append_utf8_string(var_header, topic);

    std::string remaining = var_header + payload;
    std::string rl = encode_varint(static_cast<uint32_t>(remaining.size()));

    uint8_t header = 0x30; // PUBLISH QoS0
    if (retain) header |= 0x01;

    std::string packet;
    packet.push_back(static_cast<char>(header));
    packet += rl;
    packet += remaining;

    return write_all(sock_, packet.data(), packet.size());
}

void MqttClient::disconnect() {
    if (sock_ != -1) {
        uint8_t pkt[2] = {0xE0, 0x00};
        (void)write_all(sock_, pkt, 2);
        ::close(sock_);
        sock_ = -1;
    }
}

