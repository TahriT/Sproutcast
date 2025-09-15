#include "config_manager.hpp"
#include <iostream>
#include <fstream>
#include <filesystem>
#include <algorithm>

// Global configuration instance
std::unique_ptr<ConfigManager> g_config_manager = std::make_unique<ConfigManager>();

ConfigManager::ConfigManager() : is_loaded(false) {}

ConfigManager::~ConfigManager() {}

bool ConfigManager::loadConfig(const std::string& config_path) {
    config_file_path = config_path;
    
    try {
        std::ifstream config_file(config_path);
        if (!config_file.is_open()) {
            std::cerr << "Failed to open config file: " << config_path << std::endl;
            return false;
        }
        
        config_file >> config_json;
        config_file.close();
        
        parseConfig();
        is_loaded = true;
        
        std::cout << "Configuration loaded successfully from: " << config_path << std::endl;
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "Error loading configuration: " << e.what() << std::endl;
        return false;
    }
}

bool ConfigManager::reloadConfig() {
    if (config_file_path.empty()) {
        std::cerr << "No config file path set for reload" << std::endl;
        return false;
    }
    return loadConfig(config_file_path);
}

void ConfigManager::parseConfig() {
    parsePlantTypes();
    parseProcessingConfig();
    parseCameras();
    parseMQTTConfig();
}

void ConfigManager::parsePlantTypes() {
    plant_types.clear();
    
    if (config_json.contains("plant_types") && config_json["plant_types"].contains("definitions")) {
        for (const auto& [type_name, type_data] : config_json["plant_types"]["definitions"].items()) {
            PlantTypeDefinition definition;
            
            // Parse sprout characteristics
            if (type_data.contains("sprout_characteristics")) {
                const auto& sprout = type_data["sprout_characteristics"];
                definition.sprout_characteristics.max_area_pixels = sprout.value("max_area_pixels", 5000.0);
                definition.sprout_characteristics.max_height_cm = sprout.value("max_height_cm", 8.0);
                definition.sprout_characteristics.leaf_shape = sprout.value("leaf_shape", "oval");
                definition.sprout_characteristics.saturation_min = sprout.value("saturation_min", 40.0);
                
                if (sprout.contains("color_profile") && sprout["color_profile"].contains("hue_range")) {
                    auto hue_range = sprout["color_profile"]["hue_range"];
                    definition.sprout_characteristics.hue_range = cv::Scalar(hue_range[0], hue_range[1]);
                }
            }
            
            // Parse plant characteristics
            if (type_data.contains("plant_characteristics")) {
                const auto& plant = type_data["plant_characteristics"];
                definition.plant_characteristics.max_area_pixels = plant.value("min_area_pixels", 8000.0);
                definition.plant_characteristics.max_height_cm = plant.value("min_height_cm", 10.0);
                
                if (plant.contains("disease_markers")) {
                    definition.disease_markers = plant["disease_markers"];
                }
                
                if (plant.contains("flowering_indicators")) {
                    definition.flowering_indicators = plant["flowering_indicators"];
                }
            }
            
            plant_types[type_name] = definition;
        }
    }
}

void ConfigManager::parseProcessingConfig() {
    const auto& global = config_json["processing"]["global"];
    const auto& sprout = config_json["processing"]["sprout_specific"];
    const auto& plant = config_json["processing"]["plant_specific"];
    
    // Global settings
    processing_config.threshold = global.value("threshold", 100);
    processing_config.publish_interval_ms = global.value("publish_interval_ms", 30000);
    processing_config.scale_px_per_cm = global.value("scale_px_per_cm", 4.2);
    processing_config.enable_watershed = global.value("enable_watershed", true);
    processing_config.enable_advanced_health = global.value("enable_advanced_health", true);
    
    // Sprout-specific settings
    processing_config.sprout_sensitivity_multiplier = sprout.value("sensitivity_multiplier", 1.2);
    processing_config.sprout_min_area = sprout.value("min_area_pixels", 50);
    processing_config.sprout_max_area = sprout.value("max_area_pixels", 5000);
    processing_config.sprout_morphology_kernel = sprout.value("morphology_kernel", 3);
    
    if (sprout.contains("hue_range")) {
        auto hue_range = sprout["hue_range"];
        processing_config.sprout_hue_range = cv::Scalar(hue_range[0], hue_range[1]);
    }
    
    // Plant-specific settings
    processing_config.plant_min_area = plant.value("min_area_pixels", 100);
    processing_config.enable_petal_detection = plant.value("enable_petal_detection", true);
    processing_config.enable_fruit_detection = plant.value("enable_fruit_detection", true);
    processing_config.enable_disease_detection = plant.value("disease_detection", true);
    processing_config.plant_morphology_kernel = plant.value("morphology_kernel", 5);
}

void ConfigManager::parseCameras() {
    cameras.clear();
    
    if (config_json.contains("cameras")) {
        for (const auto& cam_data : config_json["cameras"]) {
            CameraConfig config;
            
            config.id = cam_data.value("id", "");
            config.name = cam_data.value("name", "Unknown Camera");
            
            // Location
            if (cam_data.contains("location")) {
                const auto& loc = cam_data["location"];
                config.location.room = loc.value("room", "");
                config.location.area = loc.value("area", "");
                
                if (loc.contains("position")) {
                    auto pos = loc["position"];
                    config.location.position.x = pos.value("x", 0.0);
                    config.location.position.y = pos.value("y", 0.0);
                    config.location.position.z = pos.value("height", 0.0);
                }
            }
            
            // Input configuration
            if (cam_data.contains("input")) {
                const auto& input = cam_data["input"];
                std::string mode_str = input.value("mode", "IMAGE");
                
                if (mode_str == "IMAGE") config.input.mode = CameraConfig::Input::IMAGE;
                else if (mode_str == "CAMERA") config.input.mode = CameraConfig::Input::CAMERA;
                else if (mode_str == "URL") config.input.mode = CameraConfig::Input::URL;
                
                config.input.path = input.value("path", "");
                config.input.url = input.value("url", "");
                config.input.device_id = input.value("device_id", 0);
            }
            
            // Processing overrides
            if (cam_data.contains("processing_overrides")) {
                const auto& overrides = cam_data["processing_overrides"];
                config.processing_overrides.threshold = overrides.value("threshold", processing_config.threshold);
                config.processing_overrides.scale_px_per_cm = overrides.value("scale_px_per_cm", processing_config.scale_px_per_cm);
                config.processing_overrides.sprout_focus = overrides.value("sprout_focus", false);
                
                if (overrides.contains("focus_area")) {
                    const auto& focus = overrides["focus_area"];
                    config.processing_overrides.focus_area = cv::Rect(
                        focus.value("x", 0),
                        focus.value("y", 0),
                        focus.value("width", 640),
                        focus.value("height", 480)
                    );
                }
            }
            
            // Output configuration
            if (cam_data.contains("output")) {
                const auto& output = cam_data["output"];
                config.output.save_images = output.value("save_images", true);
                config.output.image_quality = output.value("image_quality", 90);
                config.output.enable_base64 = output.value("enable_base64", true);
            }
            
            cameras.push_back(config);
        }
    }
}

void ConfigManager::parseMQTTConfig() {
    // Broker configuration
    if (config_json.contains("mqtt") && config_json["mqtt"].contains("broker")) {
        const auto& broker = config_json["mqtt"]["broker"];
        mqtt_config.broker.host = broker.value("host", "localhost");
        mqtt_config.broker.port = broker.value("port", 1883);
        mqtt_config.broker.username = broker.value("username", "");
        mqtt_config.broker.password = broker.value("password", "");
        mqtt_config.broker.client_id = broker.value("client_id", "sproutcast");
    }
    
    // Topic templates
    if (config_json.contains("mqtt") && config_json["mqtt"].contains("topics")) {
        const auto& topics = config_json["mqtt"]["topics"];
        mqtt_config.topics.base = topics.value("base", "sproutcast");
        mqtt_config.topics.system_status = topics.value("system_status", "{base}/{room}/{area}/{camera_id}/system/status");
        mqtt_config.topics.analysis_telemetry = topics.value("analysis_telemetry", "{base}/{room}/{area}/{camera_id}/analysis/telemetry");
        mqtt_config.topics.sprout_telemetry = topics.value("sprout_telemetry", "{base}/{room}/{area}/{camera_id}/sprouts/{id}/telemetry");
        mqtt_config.topics.plant_telemetry = topics.value("plant_telemetry", "{base}/{room}/{area}/{camera_id}/plants/{id}/telemetry");
        mqtt_config.topics.alerts = topics.value("alerts", "{base}/{room}/{area}/{camera_id}/alerts");
    }
    
    // QoS and retain settings
    if (config_json.contains("mqtt")) {
        if (config_json["mqtt"].contains("qos")) {
            for (const auto& [key, value] : config_json["mqtt"]["qos"].items()) {
                mqtt_config.qos[key] = value;
            }
        }
        
        if (config_json["mqtt"].contains("retain")) {
            for (const auto& [key, value] : config_json["mqtt"]["retain"].items()) {
                mqtt_config.retain[key] = value;
            }
        }
    }
}

const PlantTypeDefinition* ConfigManager::getPlantTypeDefinition(const std::string& type) const {
    auto it = plant_types.find(type);
    return (it != plant_types.end()) ? &it->second : nullptr;
}

std::vector<std::string> ConfigManager::getAvailablePlantTypes() const {
    std::vector<std::string> types;
    for (const auto& [type, _] : plant_types) {
        types.push_back(type);
    }
    return types;
}

const ProcessingConfig& ConfigManager::getProcessingConfig() const {
    return processing_config;
}

const CameraConfig* ConfigManager::getCameraConfig(const std::string& camera_id) const {
    auto it = std::find_if(cameras.begin(), cameras.end(),
        [&camera_id](const CameraConfig& cam) { return cam.id == camera_id; });
    return (it != cameras.end()) ? &(*it) : nullptr;
}

const CameraConfig* ConfigManager::getCameraConfig(int camera_index) const {
    return (camera_index >= 0 && camera_index < cameras.size()) ? &cameras[camera_index] : nullptr;
}

const MQTTConfig& ConfigManager::getMQTTConfig() const {
    return mqtt_config;
}

std::string ConfigManager::generateMQTTTopic(const std::string& template_name, 
                                           const CameraConfig& camera, 
                                           const std::string& instance_id) const {
    std::string topic_template;
    
    if (template_name == "system_status") topic_template = mqtt_config.topics.system_status;
    else if (template_name == "analysis_telemetry") topic_template = mqtt_config.topics.analysis_telemetry;
    else if (template_name == "sprout_telemetry") topic_template = mqtt_config.topics.sprout_telemetry;
    else if (template_name == "plant_telemetry") topic_template = mqtt_config.topics.plant_telemetry;
    else if (template_name == "alerts") topic_template = mqtt_config.topics.alerts;
    else return "";
    
    std::map<std::string, std::string> placeholders = {
        {"{base}", mqtt_config.topics.base},
        {"{room}", camera.location.room},
        {"{area}", camera.location.area},
        {"{camera_id}", camera.id},
        {"{id}", instance_id}
    };
    
    return replacePlaceholders(topic_template, placeholders);
}

std::string ConfigManager::replacePlaceholders(const std::string& template_str, 
                                             const std::map<std::string, std::string>& values) const {
    std::string result = template_str;
    
    for (const auto& [placeholder, value] : values) {
        size_t pos = 0;
        while ((pos = result.find(placeholder, pos)) != std::string::npos) {
            result.replace(pos, placeholder.length(), value);
            pos += value.length();
        }
    }
    
    return result;
}

bool ConfigManager::isPlantType(double area_pixels, double height_cm, const std::string& plant_type) const {
    // Get classification thresholds
    double sprout_max_area = 5000.0;
    double sprout_max_height = 8.0;
    
    if (config_json.contains("plant_types") && config_json["plant_types"].contains("classification_thresholds")) {
        const auto& thresholds = config_json["plant_types"]["classification_thresholds"];
        sprout_max_area = thresholds.value("sprout_max_area", 5000.0);
        sprout_max_height = thresholds.value("sprout_max_height_cm", 8.0);
    }
    
    // If specific plant type provided, use its thresholds
    if (!plant_type.empty()) {
        const auto* type_def = getPlantTypeDefinition(plant_type);
        if (type_def) {
            sprout_max_area = type_def->sprout_characteristics.max_area_pixels;
            sprout_max_height = type_def->sprout_characteristics.max_height_cm;
        }
    }
    
    // Return true if it's a plant (exceeds sprout thresholds)
    return (area_pixels >= sprout_max_area) || (height_cm >= sprout_max_height);
}

int ConfigManager::getActiveCameraIndex() const {
    return config_json.value("active_camera_index", 0);
}

bool ConfigManager::isDebugMode() const {
    return config_json.value("debug_mode", false);
}

std::string ConfigManager::getLogLevel() const {
    return config_json.value("log_level", "INFO");
}

bool ConfigManager::validateConfig() const {
    return getValidationErrors().empty();
}

std::vector<std::string> ConfigManager::getValidationErrors() const {
    std::vector<std::string> errors;
    
    // Validate required sections exist
    if (!config_json.contains("processing")) {
        errors.push_back("Missing 'processing' configuration section");
    }
    
    if (!config_json.contains("cameras") || config_json["cameras"].empty()) {
        errors.push_back("No cameras configured");
    }
    
    if (!config_json.contains("mqtt")) {
        errors.push_back("Missing 'mqtt' configuration section");
    }
    
    // Validate camera configurations
    for (size_t i = 0; i < cameras.size(); ++i) {
        const auto& cam = cameras[i];
        if (cam.id.empty()) {
            errors.push_back("Camera " + std::to_string(i) + " missing ID");
        }
        if (cam.input.mode == CameraConfig::Input::IMAGE && cam.input.path.empty()) {
            errors.push_back("Camera " + cam.id + " in IMAGE mode but no path specified");
        }
    }
    
    return errors;
}

bool ConfigManager::saveConfig() {
    if (config_file_path.empty()) {
        std::cerr << "No config file path set for save operation" << std::endl;
        return false;
    }
    
    try {
        std::ofstream config_file(config_file_path);
        config_file << std::setw(2) << config_json << std::endl;
        config_file.close();
        
        std::cout << "Configuration saved to: " << config_file_path << std::endl;
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "Error saving configuration: " << e.what() << std::endl;
        return false;
    }
}
