#ifndef CONFIG_MANAGER_HPP
#define CONFIG_MANAGER_HPP

#include <string>
#include <map>
#include <vector>
#include <memory>
#include <opencv2/opencv.hpp>
#include <nlohmann/json.hpp>

struct PlantTypeDefinition {
    struct Characteristics {
        double max_area_pixels;
        double max_height_cm;
        std::string leaf_shape;
        cv::Scalar hue_range;
        double saturation_min;
    };
    
    Characteristics sprout_characteristics;
    Characteristics plant_characteristics;
    std::vector<std::string> disease_markers;
    std::vector<std::string> flowering_indicators;
};

struct ProcessingConfig {
    int threshold;
    int publish_interval_ms;
    double scale_px_per_cm;
    bool enable_watershed;
    bool enable_advanced_health;
    
    // Sprout-specific
    double sprout_sensitivity_multiplier;
    int sprout_min_area;
    int sprout_max_area;
    cv::Scalar sprout_hue_range;
    int sprout_morphology_kernel;
    
    // Plant-specific  
    int plant_min_area;
    bool enable_petal_detection;
    bool enable_fruit_detection;
    bool enable_disease_detection;
    int plant_morphology_kernel;
};

struct CameraConfig {
    std::string id;
    std::string name;
    
    struct Location {
        std::string room;
        std::string area;
        cv::Point3d position;
    } location;
    
    struct Input {
        enum Mode { IMAGE, CAMERA, URL } mode;
        std::string path;
        std::string url;
        int device_id;
    } input;
    
    struct ProcessingOverrides {
        int threshold;
        double scale_px_per_cm;
        bool sprout_focus;
        cv::Rect focus_area;
    } processing_overrides;
    
    struct Output {
        bool save_images;
        int image_quality;
        bool enable_base64;
    } output;
};

struct MQTTConfig {
    struct Broker {
        std::string host;
        int port;
        std::string username;
        std::string password;
        std::string client_id;
    } broker;
    
    struct Topics {
        std::string base;
        std::string system_status;
        std::string analysis_telemetry;
        std::string sprout_telemetry;
        std::string plant_telemetry;
        std::string alerts;
    } topics;
    
    std::map<std::string, int> qos;
    std::map<std::string, bool> retain;
};

class ConfigManager {
private:
    nlohmann::json config_json;
    std::string config_file_path;
    
    // Cached configurations
    std::map<std::string, PlantTypeDefinition> plant_types;
    ProcessingConfig processing_config;
    std::vector<CameraConfig> cameras;
    MQTTConfig mqtt_config;
    
    bool is_loaded;
    
public:
    ConfigManager();
    ~ConfigManager();
    
    // Configuration loading and validation
    bool loadConfig(const std::string& config_path);
    bool reloadConfig();
    bool validateConfig() const;
    std::vector<std::string> getValidationErrors() const;
    
    // Plant type management
    const PlantTypeDefinition* getPlantTypeDefinition(const std::string& type) const;
    std::vector<std::string> getAvailablePlantTypes() const;
    bool addPlantType(const std::string& type, const PlantTypeDefinition& definition);
    
    // Configuration access
    const ProcessingConfig& getProcessingConfig() const;
    const CameraConfig* getCameraConfig(const std::string& camera_id) const;
    const CameraConfig* getCameraConfig(int camera_index) const;
    const MQTTConfig& getMQTTConfig() const;
    
    // Dynamic updates
    bool updateProcessingConfig(const ProcessingConfig& new_config);
    bool updateCameraConfig(const std::string& camera_id, const CameraConfig& new_config);
    
    // MQTT topic generation
    std::string generateMQTTTopic(const std::string& template_name, 
                                 const CameraConfig& camera, 
                                 const std::string& instance_id = "") const;
    
    // Utility methods
    int getActiveCameraIndex() const;
    bool isDebugMode() const;
    std::string getLogLevel() const;
    
    // Configuration persistence
    bool saveConfig();
    bool exportConfig(const std::string& export_path) const;
    
    // Plant classification helpers
    bool isPlantType(double area_pixels, double height_cm, 
                    const std::string& plant_type = "") const;
    double getClassificationConfidence(double area_pixels, double height_cm,
                                     const std::string& plant_type = "") const;
    
private:
    void parseConfig();
    void parsePlantTypes();
    void parseProcessingConfig();
    void parseCameras();
    void parseMQTTConfig();
    
    std::string replacePlaceholders(const std::string& template_str, 
                                   const std::map<std::string, std::string>& values) const;
};

// Global configuration instance
extern std::unique_ptr<ConfigManager> g_config_manager;

// Helper macros for easy access
#define CONFIG_GET_PROCESSING() (g_config_manager->getProcessingConfig())
#define CONFIG_GET_CAMERA(id) (g_config_manager->getCameraConfig(id))
#define CONFIG_GET_MQTT() (g_config_manager->getMQTTConfig())
#define CONFIG_GET_PLANT_TYPE(type) (g_config_manager->getPlantTypeDefinition(type))

#endif // CONFIG_MANAGER_HPP
