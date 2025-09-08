#include <opencv2/opencv.hpp>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <nlohmann/json.hpp>
#include <string>
#include <thread>

#include "leaf_area.hpp"
#include "mqtt_client.hpp"

using json = nlohmann::json;

static int getenv_int(const char* key, int def) {
    const char* v = std::getenv(key);
    return v ? std::atoi(v) : def;
}

static std::string getenv_str(const char* key, const char* def) {
    const char* v = std::getenv(key);
    return v ? std::string(v) : std::string(def);
}

int main() {
    int cameraId = getenv_int("CAMERA_ID", 0);
    int thresholdValue = getenv_int("THRESHOLD", 100);
    int intervalMs = getenv_int("PUBLISH_INTERVAL_MS", 1000);
    std::string mqttHost = getenv_str("MQTT_HOST", "localhost");
    int mqttPort = getenv_int("MQTT_PORT", 1883);
    std::string topic = getenv_str("MQTT_TOPIC", "plant/area");
    double scalePxPerCm = std::atof(getenv_str("SCALE_PX_PER_CM", "0").c_str());
    std::string inputMode = getenv_str("INPUT_MODE", "IMAGE"); // IMAGE or CAMERA
    std::string inputPath = getenv_str("INPUT_PATH", "/samples/plant.jpg");

    cv::VideoCapture cap;
    if (inputMode == "CAMERA") {
        cap.open(cameraId);
        if (!cap.isOpened()) {
            std::cerr << "Failed to open camera " << cameraId << ". Falling back to black frame.\n";
        }
    }

    MqttClient client(mqttHost, mqttPort);
    if (!client.connect()) {
        std::cerr << "Failed to connect to MQTT broker at " << mqttHost << ":" << mqttPort << "\n";
    }

    while (true) {
        cv::Mat frame;
        if (inputMode == "CAMERA" && cap.isOpened()) {
            cap >> frame;
        }
        if (frame.empty()) {
            if (inputMode == "IMAGE") {
                frame = cv::imread(inputPath);
            }
            if (frame.empty()) {
                frame = cv::Mat::zeros(480, 640, CV_8UC3);
            }
        }

        LeafAreaResult res = estimateLeafArea(frame, thresholdValue, scalePxPerCm);
        json payload = {
            {"area_pixels", res.areaPixels},
            {"area_cm2", res.areaCm2},
            {"contours", res.contourCount},
            {"scale_px_per_cm", res.scalePxPerCm},
            {"timestamp", std::chrono::duration_cast<std::chrono::milliseconds>(
                               std::chrono::system_clock::now().time_since_epoch()).count()}
        };

        client.publish(topic, payload.dump());

        std::this_thread::sleep_for(std::chrono::milliseconds(intervalMs));
    }

    client.disconnect();
    return 0;
}

