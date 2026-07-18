#include <ESP8266WiFi.h>
#include <WebSocketsClient.h>
#include <SoftwareSerial.h>
#include <ArduinoJson.h>

#if __has_include("config.h")
#include "config.h"
#else
#error "Please copy config.example.h to config.h and fill in your credentials."
#endif

// Hardware configuration
SoftwareSerial arduinoSerial(14, 12); // RX (D5), TX (D6)

// WebSocket configuration
WebSocketsClient webSocket;

// State
static unsigned long lastHeartbeat = 0;
static const unsigned long HEARTBEAT_INTERVAL = 10000; // 10 seconds

static unsigned long lastStatus = 0;
static const unsigned long STATUS_INTERVAL = 30000; // 30 seconds

// Offline Queue
#define MAX_QUEUE_SIZE 10
#define MAX_JSON_LEN 256
static char offlineQueue[MAX_QUEUE_SIZE][MAX_JSON_LEN];
static int queueHead = 0;
static int queueTail = 0;
static int queueSize = 0;

void enqueueMessage(const char* msg) {
    if (queueSize < MAX_QUEUE_SIZE) {
        strncpy(offlineQueue[queueTail], msg, MAX_JSON_LEN - 1);
        offlineQueue[queueTail][MAX_JSON_LEN - 1] = '\0';
        queueTail = (queueTail + 1) % MAX_QUEUE_SIZE;
        queueSize++;
    } else {
        Serial.println("[QUEUE] Full, dropping oldest message.");
        // Overwrite oldest (head)
        strncpy(offlineQueue[queueHead], msg, MAX_JSON_LEN - 1);
        offlineQueue[queueHead][MAX_JSON_LEN - 1] = '\0';
        queueHead = (queueHead + 1) % MAX_QUEUE_SIZE;
        queueTail = (queueTail + 1) % MAX_QUEUE_SIZE;
    }
}

void flushQueue() {
    while (queueSize > 0) {
        Serial.print("[QUEUE] Flushing message: ");
        Serial.println(offlineQueue[queueHead]);
        webSocket.sendTXT(offlineQueue[queueHead]);
        queueHead = (queueHead + 1) % MAX_QUEUE_SIZE;
        queueSize--;
    }
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.printf("[WS] Disconnected!\n");
            break;
        case WStype_CONNECTED: {
            Serial.printf("[WS] Connected to url: %s\n", payload);
            
            // Send Gateway Registration
            StaticJsonDocument<256> doc;
            doc["typ"] = "gateway_register";
            doc["gateway_id"] = "aeon-esp-01";
            doc["device_id"] = "sentinel-01";
            doc["transport"] = "uart_wifi";
            doc["firmware_version"] = "1.0.0";
            
            char buffer[256];
            serializeJson(doc, buffer);
            webSocket.sendTXT(buffer);
            
            // Flush any offline messages
            flushQueue();
            break;
        }
        case WStype_TEXT: {
            Serial.printf("[WS] Received: %s\n", payload);
            // Forward directly to Arduino via UART
            arduinoSerial.println((char*)payload);
            break;
        }
        case WStype_PING:
        case WStype_PONG:
        case WStype_BIN:
        case WStype_ERROR:
        case WStype_FRAGMENT_TEXT_START:
        case WStype_FRAGMENT_BIN_START:
        case WStype_FRAGMENT:
        case WStype_FRAGMENT_FIN:
            break;
    }
}

void setup() {
    // Debug console
    Serial.begin(115200);
    
    // UART to Arduino
    arduinoSerial.begin(9600);
    
    Serial.println("\n[AEON-GATEWAY] Booting...");

    // Connect to Wi-Fi
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    Serial.print("[WIFI] Connecting");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();
    Serial.printf("[WIFI] Connected! IP: %s\n", WiFi.localIP().toString().c_str());

    // Connect WebSocket
    webSocket.begin(BACKEND_HOST, BACKEND_PORT, BACKEND_WS_PATH);
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000); // 5s auto reconnect
}

static char rx_buffer[MAX_JSON_LEN];
static uint16_t rx_index = 0;
static unsigned long lastArduinoMsg = 0;

void processArduinoUART() {
    while (arduinoSerial.available() > 0) {
        char b = arduinoSerial.read();
        
        if (b == '\n' || b == '\r') {
            if (rx_index > 0) {
                rx_buffer[rx_index] = '\0';
                
                // Validate basic JSON format
                if (rx_buffer[0] == '{' && rx_buffer[rx_index - 1] == '}') {
                    Serial.printf("[UART] Received valid JSON: %s\n", rx_buffer);
                    
                    if (webSocket.isConnected()) {
                        webSocket.sendTXT(rx_buffer);
                    } else {
                        enqueueMessage(rx_buffer);
                    }
                    
                    lastArduinoMsg = millis();
                } else {
                    Serial.println("[UART] Error: Invalid JSON received from Arduino.");
                }
                rx_index = 0;
            }
        } else {
            if (rx_index < MAX_JSON_LEN - 1) {
                rx_buffer[rx_index++] = b;
            } else {
                Serial.println("[UART] Error: Buffer overflow, dropping message.");
                rx_index = 0;
            }
        }
    }
}

void loop() {
    webSocket.loop();
    processArduinoUART();

    // Check Wi-Fi reconnection is handled automatically by ESP8266, 
    // but just in case, WebSocketsClient reconnectInterval handles WS reconnect.
    
    unsigned long now = millis();
    
    // Send Gateway Status periodically
    if (now - lastStatus >= STATUS_INTERVAL) {
        lastStatus = now;
        if (webSocket.isConnected()) {
            bool arduinoConnected = (now - lastArduinoMsg) < 60000; // 1 min timeout
            
            StaticJsonDocument<256> doc;
            doc["typ"] = "gateway_status";
            doc["gateway_id"] = "aeon-esp-01";
            doc["wifi_rssi"] = WiFi.RSSI();
            doc["arduino_connected"] = arduinoConnected;
            doc["uptime_ms"] = now;
            
            char buffer[256];
            serializeJson(doc, buffer);
            webSocket.sendTXT(buffer);
        }
    }
}
