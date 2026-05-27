const int LED_REAR_PIN = A0;
const int LED_FRONT_PIN = A2;
const int TOUCH_PIN = 2;

// Thresholds LED
const int LED_REAR_REMOVED_THRESHOLD = 850;
const int LED_FRONT_REMOVED_THRESHOLD = 850;

// Impact sensor timing
const unsigned long MIN_TOUCH_TIME = 40;
const unsigned long MAX_TOUCH_TIME = 200;
const unsigned long IMPACT_COOLDOWN_MS = 1000;

bool rearFaultActive = false;
bool frontFaultActive = false;

bool lastTouchState = LOW;
unsigned long touchStartTime = 0;
unsigned long lastImpactTime = 0;

int readAnalogAverage(int pin) {
  long sum = 0;

  for (int i = 0; i < 10; i++) {
    sum += analogRead(pin);
    delay(2);
  }

  return sum / 10;
}

void checkLed(
  int pin,
  int threshold,
  bool &faultActive,
  const char* ledName
) {
  int ledValue = readAnalogAverage(pin);

  bool ledRemoved = ledValue > threshold;

  if (ledRemoved && !faultActive) {
    faultActive = true;
    Serial.print(ledName);
    Serial.println(":FAULT");
  }

  if (!ledRemoved && faultActive) {
    faultActive = false;
    Serial.print(ledName);
    Serial.println(":OK");
  }
}

void checkImpactSensor() {
  bool touchState = digitalRead(TOUCH_PIN);
  unsigned long now = millis();

  // Flanco de subida: empieza la detección
  if (touchState == HIGH && lastTouchState == LOW) {
    touchStartTime = now;
  }

  // Flanco de bajada: termina la detección
  if (touchState == LOW && lastTouchState == HIGH) {
    unsigned long touchDuration = now - touchStartTime;

    bool validImpact =
      touchDuration >= MIN_TOUCH_TIME &&
      touchDuration <= MAX_TOUCH_TIME;

    bool cooldownPassed =
      now - lastImpactTime >= IMPACT_COOLDOWN_MS;

    if (validImpact && cooldownPassed) {
      lastImpactTime = now;

      Serial.print("CRASH:FAULT:");
      Serial.println(touchDuration);
    }
  }

  lastTouchState = touchState;
}

void setup() {
  Serial.begin(9600);

  pinMode(TOUCH_PIN, INPUT);

  delay(500);

  int rearValue = readAnalogAverage(LED_REAR_PIN);

  if (rearValue > LED_REAR_REMOVED_THRESHOLD) {
    rearFaultActive = true;
    Serial.println("LED_REAR:FAULT");
  } else {
    rearFaultActive = false;
    Serial.println("LED_REAR:OK");
  }

  int frontValue = readAnalogAverage(LED_FRONT_PIN);

  if (frontValue > LED_FRONT_REMOVED_THRESHOLD) {
    frontFaultActive = true;
    Serial.println("LED_FRONT:FAULT");
  } else {
    frontFaultActive = false;
    Serial.println("LED_FRONT:OK");
  }
}

void loop() {
  checkLed(
    LED_REAR_PIN,
    LED_REAR_REMOVED_THRESHOLD,
    rearFaultActive,
    "LED_REAR"
  );

  checkLed(
    LED_FRONT_PIN,
    LED_FRONT_REMOVED_THRESHOLD,
    frontFaultActive,
    "LED_FRONT"
  );

  checkImpactSensor();

  delay(2);
}