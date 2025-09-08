#include <opencv2/opencv.hpp>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <nlohmann/json.hpp>
#include <fstream>
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

static nlohmann::json load_config_json(const std::string &path) {
    try {
        std::ifstream f(path);
        if (f) {
            nlohmann::json j; f >> j; return j;
        }
    } catch (...) {}
    return nlohmann::json();
}

template <typename T>
static T json_get_or(const nlohmann::json &j, const char *key, const T &def) {
    try {
        if (!j.is_object()) return def;
        auto it = j.find(key);
        if (it == j.end() || it->is_null()) return def;
        return it->get<T>();
    } catch (...) {
        return def;
    }
}

template <typename T>
static T json_get_nested_or(const nlohmann::json &j, const char *obj, const char *key, const T &def) {
    try {
        if (!j.is_object()) return def;
        auto it = j.find(obj);
        if (it == j.end() || !it->is_object()) return def;
        return json_get_or<T>(*it, key, def);
    } catch (...) {
        return def;
    }
}

int main() {
    auto cfg = load_config_json("/app/data/config.json");

    int cameraId = getenv_int("CAMERA_ID", json_get_or<int>(cfg, "camera_id", 0));
    int thresholdValue = getenv_int("THRESHOLD", json_get_nested_or<int>(cfg, "processing", "threshold", 100));
    int intervalMs = getenv_int("PUBLISH_INTERVAL_MS", json_get_nested_or<int>(cfg, "processing", "publish_interval_ms", 1000));
    std::string mqttHost = getenv_str("MQTT_HOST", json_get_nested_or<std::string>(cfg, "mqtt", "host", std::string("localhost")).c_str());
    int mqttPort = getenv_int("MQTT_PORT", json_get_nested_or<int>(cfg, "mqtt", "port", 1883));
    double scalePxPerCm = std::atof(getenv_str("SCALE_PX_PER_CM", std::to_string(json_get_nested_or<double>(cfg, "processing", "scale_px_per_cm", 0.0)).c_str()).c_str());
    std::string inputMode = getenv_str("INPUT_MODE", json_get_nested_or<std::string>(cfg, "processing", "input_mode", std::string("IMAGE")).c_str()); // IMAGE or CAMERA
    std::string inputPath = getenv_str("INPUT_PATH", json_get_nested_or<std::string>(cfg, "processing", "input_path", std::string("/samples/plant.jpg")).c_str());

    std::string topicEnv = getenv_str("MQTT_TOPIC", "");
    std::string topic;
    if (!topicEnv.empty()) {
        topic = topicEnv;
    } else {
        std::string room = json_get_nested_or<std::string>(cfg, "uns", "room", std::string("room-1"));
        std::string area = json_get_nested_or<std::string>(cfg, "uns", "area", std::string("area-1"));
        std::string cam = json_get_nested_or<std::string>(cfg, "uns", "camera_id", std::string("0"));
        std::string plant = json_get_nested_or<std::string>(cfg, "uns", "plant_id", std::string("plant-1"));
        topic = std::string("plantvision/") + room + "/" + area + "/" + cam + "/" + plant + "/telemetry";
    }

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

        // Annotate frame
        cv::Mat annotated = frame.clone();
        for (size_t i = 0; i < res.contours.size(); ++i) {
            cv::drawContours(annotated, res.contours, static_cast<int>(i), cv::Scalar(0, 255, 0), 2);
            cv::rectangle(annotated, res.perContourBBox[i], cv::Scalar(0, 0, 255), 2);
        }

        // Save frames to shared volume if available
        try {
            cv::imwrite("/app/data/frame_raw.jpg", frame);
            cv::imwrite("/app/data/frame_annotated.jpg", annotated);
        } catch (...) {}

        // Build payload with per-plant data
        json plants = json::array();
        for (size_t i = 0; i < res.perContourAreaPx.size(); ++i) {
            const auto &bb = res.perContourBBox[i];
            double area_px = res.perContourAreaPx[i];
            double area_cm2 = (scalePxPerCm > 0.0) ? (area_px / (scalePxPerCm * scalePxPerCm)) : 0.0;
            plants.push_back({
                {"id", static_cast<int>(i)},
                {"bbox", {bb.x, bb.y, bb.width, bb.height}},
                {"area_pixels", area_px},
                {"area_cm2", area_cm2}
            });
        }

        json payload = {
            {"timestamp", std::chrono::duration_cast<std::chrono::milliseconds>(
                               std::chrono::system_clock::now().time_since_epoch()).count()},
            {"num_plants", res.contourCount},
            {"total_area_pixels", res.areaPixels},
            {"total_area_cm2", res.areaCm2},
            {"scale_px_per_cm", res.scalePxPerCm},
            {"plants", plants}
        };

        client.publish(topic, payload.dump());

        std::this_thread::sleep_for(std::chrono::milliseconds(intervalMs));
    }

    client.disconnect();
    return 0;
}

