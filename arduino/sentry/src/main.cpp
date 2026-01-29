#include <Arduino.h>
#include <AccelStepper.h>

// --- PIN DEFINITIONS (Adjust for your CNC Shield/Driver) ---
// Standard CNC Shield mappings:
#define X_STEP_PIN 2
#define X_DIR_PIN  3
#define Y_STEP_PIN 4
#define Y_DIR_PIN  5
#define EN_PIN     8  // Stepper Enable (Active LOW)

// --- CONFIGURATION ---
#define MAX_SPEED 2000.0f    // Max steps per second
#define BAUD_RATE 115200     // Fast serial
#define CMD_TIMEOUT 2000     // Stop motors if no cmd for 2 seconds (Safety)

// --- OBJECTS ---
// 1 = Driver Interface (Step + Dir)
AccelStepper panMotor(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
AccelStepper tiltMotor(AccelStepper::DRIVER, Y_STEP_PIN, Y_DIR_PIN);

// --- STATE VARIABLES ---
unsigned long lastCmdTime = 0;
char serialBuffer[64];
int bufferIndex = 0;
bool isEnabled = false;

// --- FUNCTION PROTOTYPES ---
void processCommand(char* cmd);
void parseVelocityCmd(char* cmd);

void setup() {
    // 1. Init Serial
    Serial.begin(BAUD_RATE);
    while (!Serial) {}; // Wait for connection

    // 2. Init Pins
    pinMode(EN_PIN, OUTPUT);
    digitalWrite(EN_PIN, HIGH); // Disable motors initially (Safety)

    // 3. Init Motors
    panMotor.setMaxSpeed(MAX_SPEED);
    tiltMotor.setMaxSpeed(MAX_SPEED);
    
    // Default to 0 speed
    panMotor.setSpeed(0);
    tiltMotor.setSpeed(0);

    lastCmdTime = millis();
    Serial.println("SENTRY_READY");
}

void loop() {
    // --- 1. FAST LOOP: Step the motors ---
    // runSpeed() returns true if a step occurred, but we don't care here.
    // We only step if motors are enabled.
    if (isEnabled) {
        panMotor.runSpeed();
        tiltMotor.runSpeed();
    }

    // --- 2. SERIAL INPUT (Non-blocking) ---
    while (Serial.available() > 0) {
        char c = Serial.read();
        if (c == '\n') {
            serialBuffer[bufferIndex] = '\0'; // Null terminate
            processCommand(serialBuffer);
            bufferIndex = 0; // Reset
        } else if (bufferIndex < 63) {
            serialBuffer[bufferIndex++] = c;
        }
    }

    // --- 3. SAFETY WATCHDOG ---
    // If Jetson crashes/disconnects, stop the sentry.
    if (millis() - lastCmdTime > CMD_TIMEOUT) {
        if (isEnabled) {
            panMotor.setSpeed(0);
            tiltMotor.setSpeed(0);
            digitalWrite(EN_PIN, HIGH); // Cut power to coils
            isEnabled = false;
            Serial.println("ERR:TIMEOUT_STOP");
        }
    }
}

// --- PARSER LOGIC ---
// Protocol: 
// "V 100.5 -50"  -> Set Velocities (Pan=100.5, Tilt=-50)
// "E 1"          -> Enable Motors
// "E 0"          -> Disable Motors
void processCommand(char* cmd) {
    lastCmdTime = millis(); // Reset watchdog timer

    if (cmd[0] == 'V') {
        parseVelocityCmd(cmd);
    } else if (cmd[0] == 'E') {
        int state = atoi(cmd + 2);
        isEnabled = (state == 1);
        digitalWrite(EN_PIN, !isEnabled); // Active LOW logic
        Serial.println(isEnabled ? "MSG:ENABLED" : "MSG:DISABLED");
    }
}

void parseVelocityCmd(char* cmd) {
    // cmd format: "V <float> <float>"
    char* ptr = cmd + 2; // Skip "V "
    
    // Parse first float (Pan)
    float panSpeed = atof(ptr);
    
    // Find next space
    while (*ptr && *ptr != ' ') ptr++;
    
    // Parse second float (Tilt)
    float tiltSpeed = 0;
    if (*ptr == ' ') {
        tiltSpeed = atof(ptr + 1);
    }

    // Apply safely
    // Constrain to hardware limits
    panSpeed = constrain(panSpeed, -MAX_SPEED, MAX_SPEED);
    tiltSpeed = constrain(tiltSpeed, -MAX_SPEED, MAX_SPEED);

    panMotor.setSpeed(panSpeed);
    tiltMotor.setSpeed(tiltSpeed);

    // Ack (Optional - keep minimal to save bandwidth)
    // Serial.println("ACK"); 
}