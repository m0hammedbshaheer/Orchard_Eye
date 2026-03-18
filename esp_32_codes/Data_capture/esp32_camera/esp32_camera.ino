// ============================================================
//  ESP32-CAM  →  Laptop HTTP POST
//  WiFi: Pixel_1438
//  Server: 10.242.101.244:5000
// ============================================================

#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

// ---------- CONFIG ----------
#define WIFI_SSID     "Pixel_1438"
#define WIFI_PASS     "tauhapot"
#define SERVER_URL    "http://10.242.101.244:5000/upload"
#define CAPTURE_INTERVAL_MS  10000   // capture every 10 seconds
// ----------------------------

// ---------- CAMERA PIN MAP (AI-Thinker ESP32-CAM) ----------
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#define LED_GPIO_NUM       4   // onboard flash LED
// -----------------------------------------------------------

#define LOG(msg)        Serial.println(msg)
#define LOGF(fmt, ...)  Serial.printf(fmt "\n", __VA_ARGS__)

// ── LED helpers ─────────────────────────────────────────────
void ledOn()  { digitalWrite(LED_GPIO_NUM, HIGH); }
void ledOff() { digitalWrite(LED_GPIO_NUM, LOW);  }

// ── Camera init ─────────────────────────────────────────────
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_VGA;   // 640x480 — good balance
  config.jpeg_quality = 12;              // 0=best 63=worst
  config.fb_count     = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    LOGF("[CAM][ERROR] Init failed: 0x%x", err);
    return false;
  }
  LOG("[CAM] Camera init OK");
  return true;
}

// ── Your original capture logic (unchanged) ─────────────────
camera_fb_t* captureWithWarmup() {
  LOG("[CAM] LED ON – warmup started");
  ledOn();
  delay(5000);
  for (int i = 0; i < 6; i++) {
    camera_fb_t *tmp = esp_camera_fb_get();
    if (tmp) esp_camera_fb_return(tmp);
    delay(120);
  }
  LOG("[CAM] Capturing final frame");
  camera_fb_t *fb = esp_camera_fb_get();
  ledOff();
  LOG("[CAM] LED OFF");
  return fb;
}

// ── WiFi connect ─────────────────────────────────────────────
bool connectWiFi() {
  LOG("[NET] Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  WiFi.setSleep(false);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    LOG("\n[NET] WiFi connected");
    LOGF("[NET] IP: %s", WiFi.localIP().toString().c_str());
    return true;
  }
  LOG("\n[NET][ERROR] WiFi FAILED");
  return false;
}

// ── HTTP POST image ──────────────────────────────────────────
bool postImage(camera_fb_t *fb) {
  if (!fb) {
    LOG("[HTTP][ERROR] Null frame buffer");
    return false;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "image/jpeg");

  LOGF("[HTTP] POSTing %u bytes to %s", fb->len, SERVER_URL);
  int code = http.POST(fb->buf, fb->len);

  if (code == 200) {
    LOG("[HTTP] Upload OK (200)");
    http.end();
    return true;
  } else {
    LOGF("[HTTP][ERROR] Response code: %d", code);
    http.end();
    return false;
  }
}

// ── Setup ────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(LED_GPIO_NUM, OUTPUT);
  ledOff();

  if (!initCamera()) {
    LOG("[FATAL] Camera init failed – halting");
    while (true) delay(1000);
  }

  if (!connectWiFi()) {
    LOG("[FATAL] WiFi failed – halting");
    while (true) delay(1000);
  }
}

// ── Loop ─────────────────────────────────────────────────────
void loop() {
  // Re-check WiFi, reconnect if dropped
  if (WiFi.status() != WL_CONNECTED) {
    LOG("[NET] WiFi lost – reconnecting");
    connectWiFi();
    return;
  }

  camera_fb_t *fb = captureWithWarmup();

  if (fb) {
    postImage(fb);
    esp_camera_fb_return(fb);
  } else {
    LOG("[CAM][ERROR] Capture returned null");
  }

  LOG("[LOOP] Waiting for next capture");
  delay(CAPTURE_INTERVAL_MS);
}
