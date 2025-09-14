#include <opencv2/opencv.hpp>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <nlohmann/json.hpp>
#include <fstream>
#include <string>
#include <thread>

#include "mqtt_client.hpp"
// #include "config_manager.hpp"
#include "leaf_area.hpp"

using json = nlohmann::json;

// Base64 encoding function
std::string base64_encode(const unsigned char* data, size_t length) {
    const char* chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string result;
    int val = 0, valb = -6;
    for (size_t i = 0; i < length; ++i) {
        val = (val << 8) + data[i];
        valb += 8;
        while (valb >= 0) {
            result.push_back(chars[(val >> valb) & 0x3F]);
            valb -= 6;
        }
    }
    if (valb > -6) result.push_back(chars[((val << 8) >> (valb + 8)) & 0x3F]);
    while (result.size() % 4) result.push_back('=');
    return result;
}

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

static nlohmann::json load_json_if_exists(const std::string &path) {
    try {
        std::ifstream f(path);
        if (f) { nlohmann::json j; f >> j; return j; }
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

// Function declarations
int runLegacyMode(const nlohmann::json& cfg, int cameraId, int thresholdValue, int intervalMs,
                 const std::string& mqttHost, int mqttPort, double scalePxPerCm,
                 const std::string& inputMode, const std::string& inputPath, 
                 const std::string& inputUrl, const std::string& topic);

// int runWithConfigManager(const CameraConfig& cameraConfig, const ProcessingConfig& processingConfig, const MQTTConfig& mqttConfig);

int main() {
    // Initialize configuration manager
    std::string config_path = getenv_str("CONFIG_PATH", "/app/data/config.json");
    
    // Force legacy mode for testing
    // if (!g_config_manager->loadConfig(config_path)) {
        std::cout << "Using legacy configuration..." << std::endl;
        
        // Fall back to legacy configuration loading
        auto cfg = load_config_json(config_path);
        
        int cameraId = getenv_int("CAMERA_ID", json_get_or<int>(cfg, "camera_id", 0));
        int thresholdValue = getenv_int("THRESHOLD", json_get_nested_or<int>(cfg, "processing", "threshold", 100));
        int intervalMs = getenv_int("PUBLISH_INTERVAL_MS", json_get_nested_or<int>(cfg, "processing", "publish_interval_ms", 1000));
        std::string mqttHost = getenv_str("MQTT_HOST", json_get_nested_or<std::string>(cfg, "mqtt", "host", std::string("localhost")).c_str());
        int mqttPort = getenv_int("MQTT_PORT", json_get_nested_or<int>(cfg, "mqtt", "port", 1883));
        double scalePxPerCm = std::atof(getenv_str("SCALE_PX_PER_CM", std::to_string(json_get_nested_or<double>(cfg, "processing", "scale_px_per_cm", 0.0)).c_str()).c_str());
        std::string inputMode = getenv_str("INPUT_MODE", json_get_nested_or<std::string>(cfg, "processing", "input_mode", std::string("IMAGE")).c_str());
        std::string inputPath = getenv_str("INPUT_PATH", json_get_nested_or<std::string>(cfg, "processing", "input_path", std::string("/samples/plant.jpg")).c_str());
        std::string inputUrl = getenv_str("INPUT_URL", json_get_nested_or<std::string>(cfg, "processing", "input_url", std::string("")).c_str());

        // Legacy camera configuration override
        int activeIdx = json_get_or<int>(cfg, "active_camera_index", 0);
        if (cfg.contains("cameras") && cfg["cameras"].is_array()) {
            const auto &cams = cfg["cameras"];
            if (activeIdx >= 0 && activeIdx < static_cast<int>(cams.size())) {
                const auto &cam = cams[activeIdx];
                cameraId = json_get_or<int>(cam, "camera_id", cameraId);
                inputMode = json_get_or<std::string>(cam, "input_mode", inputMode);
                inputPath = json_get_or<std::string>(cam, "input_path", inputPath);
                inputUrl = json_get_or<std::string>(cam, "input_url", inputUrl);
            }
        }

        std::string topicEnv = getenv_str("MQTT_TOPIC", "");
        std::string topic;
        if (!topicEnv.empty()) {
            topic = topicEnv;
        } else {
            std::string room = json_get_nested_or<std::string>(cfg, "uns", "room", std::string("room-1"));
            std::string area = json_get_nested_or<std::string>(cfg, "uns", "area", std::string("area-1"));
            std::string camIdStr = json_get_nested_or<std::string>(cfg, "uns", "camera_id", std::string("0"));
            std::string plant = json_get_nested_or<std::string>(cfg, "uns", "plant_id", std::string("plant-1"));
            if (cfg.contains("cameras") && cfg["cameras"].is_array()) {
                const auto &cams = cfg["cameras"];
                if (activeIdx >= 0 && activeIdx < static_cast<int>(cams.size())) {
                    const auto &cam = cams[activeIdx];
                    room = json_get_or<std::string>(cam, "room", room);
                    area = json_get_or<std::string>(cam, "area", area);
                    camIdStr = json_get_or<std::string>(cam, "camera_id", camIdStr);
                    plant = json_get_or<std::string>(cam, "plant_id", plant);
                }
            }
            topic = std::string("sproutcast/") + room + "/" + area + "/" + camIdStr + "/" + plant + "/telemetry";
        }
        
        return runLegacyMode(cfg, cameraId, thresholdValue, intervalMs, mqttHost, mqttPort, 
                           scalePxPerCm, inputMode, inputPath, inputUrl, topic);
    // }
    
    /*
    // Validate new configuration
    if (!g_config_manager->validateConfig()) {
        std::cerr << "Configuration validation failed:" << std::endl;
        for (const auto& error : g_config_manager->getValidationErrors()) {
            std::cerr << "  - " << error << std::endl;
        }
        return -1;
    }
    
    std::cout << "Configuration loaded successfully!" << std::endl;
    if (g_config_manager->isDebugMode()) {
        std::cout << "Debug mode enabled" << std::endl;
    }
    
    // Get configuration
    const auto& processingConfig = g_config_manager->getProcessingConfig();
    const auto& mqttConfig = g_config_manager->getMQTTConfig();
    int activeCameraIndex = g_config_manager->getActiveCameraIndex();
    const auto* cameraConfig = g_config_manager->getCameraConfig(activeCameraIndex);
    
    if (!cameraConfig) {
        std::cerr << "No camera configuration found for index: " << activeCameraIndex << std::endl;
        return -1;
    }
    
    std::cout << "Using camera: " << cameraConfig->name << " (ID: " << cameraConfig->id << ")" << std::endl;
    
    return runWithConfigManager(*cameraConfig, processingConfig, mqttConfig);
    */
}

// Legacy mode function for backward compatibility
int runLegacyMode(const nlohmann::json& cfg, int cameraId, int thresholdValue, int intervalMs,
                 const std::string& mqttHost, int mqttPort, double scalePxPerCm,
                 const std::string& inputMode, const std::string& inputPath, 
                 const std::string& inputUrl, const std::string& topic) {

    cv::VideoCapture cap;
    if (inputMode == "CAMERA") {
        cap.open(cameraId);
        if (!cap.isOpened()) {
            std::cerr << "Failed to open camera " << cameraId << ". Falling back to black frame.\n";
        }
    } else if (inputMode == "NETWORK") {
        if (!inputUrl.empty()) {
            cap.open(inputUrl);
            if (!cap.isOpened()) {
                std::cerr << "Failed to open network stream at URL: " << inputUrl << "\n";
            }
        } else {
            std::cerr << "INPUT_MODE=NETWORK but INPUT_URL is empty.\n";
        }
    }

    MqttClient client(mqttHost, mqttPort);
    if (!client.connect()) {
        std::cerr << "Failed to connect to MQTT broker at " << mqttHost << ":" << mqttPort << "\n";
    }

    while (true) {
        cv::Mat frame;
        if ((inputMode == "CAMERA" || inputMode == "NETWORK") && cap.isOpened()) {
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

        // Use new plant analysis system
        PlantAnalysisResult analysisResult = analyzePlants(frame, thresholdValue, scalePxPerCm);
        
        // Save annotated frame
        try {
            cv::imwrite("/app/data/frame_raw.jpg", frame);
            cv::imwrite("/app/data/frame_annotated.jpg", analysisResult.annotatedFrame);
        } catch (...) {}

        // Load manual class overrides
        auto overrides = load_json_if_exists("/app/data/classes_overrides.json");

        // Build payload with per-plant/sprout data
        json plants = json::array();
        json sprouts = json::array();
        
        for (size_t i = 0; i < analysisResult.instances.size(); ++i) {
            const auto &instance = analysisResult.instances[i];
            const auto &bb = instance.boundingBox;
            
            // Encode crop image as base64
            std::string base64Image = "";
            if (!instance.cropImage.empty()) {
                std::vector<uchar> buffer;
                cv::imencode(".jpg", instance.cropImage, buffer);
                base64Image = base64_encode(buffer.data(), buffer.size());
            }
            
            std::string label = "unknown";
            try {
                if (overrides.contains(std::to_string(i)) && overrides[std::to_string(i)].contains("label")) {
                    label = overrides[std::to_string(i)]["label"].get<std::string>();
                }
            } catch (...) {}
            
            json instanceData = {
                {"id", static_cast<int>(i)},
                {"type", instance.type == PlantType::SPROUT ? "sprout" : "plant"},
                {"classification", instance.classification},
                {"bbox", {bb.x, bb.y, bb.width, bb.height}},
                {"area_pixels", instance.areaPixels},
                {"area_cm2", instance.areaCm2},
                {"height_cm", instance.heightCm},
                {"width_cm", instance.widthCm},
                {"label", label},
                {"mean_bgr", {instance.meanColor[0], instance.meanColor[1], instance.meanColor[2]}},
                {"leaf_count", instance.leafCount},
                {"petal_count", instance.petalCount},
                {"bud_count", instance.budCount},
                {"fruit_count", instance.fruitCount},
                {"health_score", instance.healthScore},
                {"growth_stage", static_cast<int>(instance.stage)},
                {"raw_image_base64", base64Image},
                {"image_format", "jpg"},
                {"timestamp", std::chrono::duration_cast<std::chrono::milliseconds>(
                               std::chrono::system_clock::now().time_since_epoch()).count()}
            };
            
            // Add to appropriate array
            if (instance.type == PlantType::SPROUT) {
                sprouts.push_back(instanceData);
            } else {
                plants.push_back(instanceData);
            }
        }

        // Main telemetry payload
        json payload = {
            {"timestamp", std::chrono::duration_cast<std::chrono::milliseconds>(
                               std::chrono::system_clock::now().time_since_epoch()).count()},
            {"total_instances", analysisResult.totalInstanceCount},
            {"sprout_count", analysisResult.sproutCount},
            {"plant_count", analysisResult.plantCount},
            {"total_area_pixels", analysisResult.totalAreaPixels},
            {"total_area_cm2", analysisResult.totalAreaCm2},
            {"scale_px_per_cm", analysisResult.scalePxPerCm},
            {"sprouts", sprouts},
            {"plants", plants}
        };

        // Create organized directory structure
        std::system("mkdir -p /app/data/sprouts");
        std::system("mkdir -p /app/data/plants");
        
        // Save per-instance data and publish per-instance topics
        for (size_t i = 0; i < analysisResult.instances.size(); ++i) {
            const auto &instance = analysisResult.instances[i];
            const auto &bb = instance.boundingBox;
            cv::Rect roi = bb & cv::Rect(0, 0, frame.cols, frame.rows);
            
            std::string instanceId = std::to_string(i);
            instanceId = std::string(3 - instanceId.length(), '0') + instanceId;
            
            std::string baseDir = (instance.type == PlantType::SPROUT) ? "/app/data/sprouts" : "/app/data/plants";
            std::string instanceDir = baseDir + "/" + instance.classification + "_" + instanceId;
            std::system(("mkdir -p " + instanceDir).c_str());
            
            if (roi.width > 0 && roi.height > 0) {
                try {
                    // Save crop image
                    cv::imwrite(instanceDir + "/crop.jpg", instance.cropImage);
                    
                    // Create highlight image
                    cv::Mat highlight = analysisResult.annotatedFrame.clone();
                    cv::Mat overlay = highlight.clone();
                    cv::Mat dark(highlight.size(), highlight.type(), cv::Scalar(0,0,0));
                    double alpha = 0.6;
                    cv::addWeighted(overlay, alpha, dark, 1.0 - alpha, 0.0, overlay);
                    instance.cropImage.copyTo(overlay(roi));
                    
                    // Save highlight image
                    cv::imwrite(instanceDir + "/highlight.jpg", overlay);
                    
                    // Save instance JSON data
                    json instanceJson = (instance.type == PlantType::SPROUT) ? 
                                      sprouts.at(std::count_if(analysisResult.instances.begin(), 
                                                             analysisResult.instances.begin() + i + 1,
                                                             [](const PlantInstance& inst) { return inst.type == PlantType::SPROUT; }) - 1) :
                                      plants.at(std::count_if(analysisResult.instances.begin(), 
                                                            analysisResult.instances.begin() + i + 1,
                                                            [](const PlantInstance& inst) { return inst.type == PlantType::PLANT; }) - 1);
                    
                    instanceJson["instance_directory"] = instanceDir;
                    
                    std::ofstream instanceFile(instanceDir + "/data.json");
                    instanceFile << instanceJson.dump(2);
                    instanceFile.close();
                    
                    // Legacy compatibility - save to old structure
                    std::ofstream legacyFile("/app/data/plant_" + std::to_string(i) + ".json");
                    legacyFile << instanceJson.dump();
                    legacyFile.close();
                    
                } catch (...) {}
            }

            // Per-instance MQTT topics
            std::string instanceTopic = topic;
            if (!instanceTopic.empty()) {
                if (instance.type == PlantType::SPROUT) {
                    instanceTopic += "/sprouts/" + std::to_string(i) + "/telemetry";
                } else {
                    instanceTopic += "/plants/" + std::to_string(i) + "/telemetry";
                }
                
                json instancePayload = (instance.type == PlantType::SPROUT) ? 
                                     sprouts.at(std::count_if(analysisResult.instances.begin(), 
                                                            analysisResult.instances.begin() + i + 1,
                                                            [](const PlantInstance& inst) { return inst.type == PlantType::SPROUT; }) - 1) :
                                     plants.at(std::count_if(analysisResult.instances.begin(), 
                                                           analysisResult.instances.begin() + i + 1,
                                                           [](const PlantInstance& inst) { return inst.type == PlantType::PLANT; }) - 1);
                
                client.publish(instanceTopic, instancePayload.dump());
            }
        }

        client.publish(topic, payload.dump());

        std::this_thread::sleep_for(std::chrono::milliseconds(intervalMs));
    }

    client.disconnect();
    return 0;
}

/*
// New configuration-based processing function
int runWithConfigManager(const CameraConfig& cameraConfig, const ProcessingConfig& processingConfig, const MQTTConfig& mqttConfig) {
    cv::VideoCapture cap;
    cv::Mat frame;
    
    // Initialize camera based on input mode
    if (cameraConfig.input.mode == CameraConfig::Input::CAMERA) {
        cap.open(cameraConfig.input.device_id);
        if (!cap.isOpened()) {
            std::cerr << "Failed to open camera " << cameraConfig.input.device_id << std::endl;
            return -1;
        }
    }
    
    // Initialize MQTT client
    MqttClient client(mqttConfig.broker.host, mqttConfig.broker.port);
    if (!client.connect()) {
        std::cerr << "Failed to connect to MQTT broker. Continuing without MQTT." << std::endl;
    }
    
    std::cout << "Starting processing loop with new configuration system..." << std::endl;
    
    while (true) {
        bool frameValid = false;
        
        // Acquire frame based on input mode
        if (cameraConfig.input.mode == CameraConfig::Input::IMAGE) {
            frame = cv::imread(cameraConfig.input.path);
            frameValid = !frame.empty();
        } else if (cameraConfig.input.mode == CameraConfig::Input::CAMERA && cap.isOpened()) {
            frameValid = cap.read(frame);
        }
        
        if (!frameValid) {
            std::cerr << "Failed to acquire frame, using fallback" << std::endl;
            frame = cv::Mat::zeros(480, 640, CV_8UC3);
        }
        
        // Apply camera-specific processing overrides
        int threshold = cameraConfig.processing_overrides.threshold;
        double scale = cameraConfig.processing_overrides.scale_px_per_cm;
        
        // Process frame with new classification system
        PlantAnalysisResult analysisResult = analyzePlants(frame, threshold, scale);
        
        auto now = std::chrono::system_clock::now();
        std::time_t timestamp = std::chrono::system_clock::to_time_t(now);
        
        // Generate MQTT topics using configuration manager
        std::string systemTopic = g_config_manager->generateMQTTTopic("system_status", cameraConfig);
        std::string analysisTopic = g_config_manager->generateMQTTTopic("analysis_telemetry", cameraConfig);
        
        // Create system status payload
        json systemPayload = {
            {"timestamp", timestamp},
            {"camera_id", cameraConfig.id},
            {"camera_name", cameraConfig.name},
            {"processing_mode", "enhanced"},
            {"total_instances", analysisResult.instances.size()},
            {"sprouts_count", analysisResult.sproutCount},
            {"plants_count", analysisResult.plantCount}
        };
        
        // Publish system status
        client.publish(systemTopic, systemPayload.dump());
        
        // Create analysis telemetry
        json analysisPayload = {
            {"timestamp", timestamp},
            {"analysis", {
                {"total_instances", analysisResult.instances.size()},
                {"sprouts", analysisResult.sproutCount},
                {"plants", analysisResult.plantCount},
                {"average_health", analysisResult.averageHealth},
                {"processing_time_ms", analysisResult.processingTimeMs}
            }}
        };
        
        // Publish analysis telemetry
        client.publish(analysisTopic, analysisPayload.dump());
        
        // Save frame images if enabled
        if (cameraConfig.output.save_images) {
            cv::imwrite("/app/data/frame_raw.jpg", frame, {cv::IMWRITE_JPEG_QUALITY, cameraConfig.output.image_quality});
            cv::imwrite("/app/data/frame_annotated.jpg", analysisResult.annotatedFrame, {cv::IMWRITE_JPEG_QUALITY, cameraConfig.output.image_quality});
        }
        
        // Create organized directory structure
        std::system("mkdir -p /app/data/sprouts");
        std::system("mkdir -p /app/data/plants");
        
        // Process individual instances with per-instance MQTT topics
        for (size_t i = 0; i < analysisResult.instances.size(); ++i) {
            const auto& instance = analysisResult.instances[i];
            
            std::string instanceId = std::to_string(i);
            instanceId = std::string(3 - instanceId.length(), '0') + instanceId;
            
            // Create instance-specific directory
            std::string baseDir = (instance.type == PlantType::SPROUT) ? "/app/data/sprouts" : "/app/data/plants";
            std::string instanceDir = baseDir + "/" + instance.classification + "_" + instanceId;
            std::system(("mkdir -p " + instanceDir).c_str());
            
            // Save instance images
            if (cameraConfig.output.save_images) {
                cv::imwrite(instanceDir + "/crop.jpg", instance.cropImage, {cv::IMWRITE_JPEG_QUALITY, cameraConfig.output.image_quality});
            }
            
            // Create instance data payload
            json instancePayload = {
                {"timestamp", timestamp},
                {"instance_id", instanceId},
                {"type", (instance.type == PlantType::SPROUT) ? "sprout" : "plant"},
                {"classification", instance.classification},
                {"area_pixels", instance.areaPixels},
                {"height_cm", instance.heightCm},
                {"health_score", instance.healthScore},
                {"bounding_box", {
                    {"x", instance.boundingBox.x},
                    {"y", instance.boundingBox.y},
                    {"width", instance.boundingBox.width},
                    {"height", instance.boundingBox.height}
                }}
            };
            
            // Save instance data file
            std::ofstream instanceFile(instanceDir + "/data.json");
            instanceFile << instancePayload.dump(2);
            instanceFile.close();
            
            // Generate and publish per-instance MQTT topic
            std::string instanceTopic;
            if (instance.type == PlantType::SPROUT) {
                instanceTopic = g_config_manager->generateMQTTTopic("sprout_telemetry", cameraConfig, instanceId);
            } else {
                instanceTopic = g_config_manager->generateMQTTTopic("plant_telemetry", cameraConfig, instanceId);
            }
            
            client.publish(instanceTopic, instancePayload.dump());
        }
        
        // Sleep based on configuration
        std::this_thread::sleep_for(std::chrono::milliseconds(processingConfig.publish_interval_ms));
    }
    
    client.disconnect();
    return 0;
}
*/

