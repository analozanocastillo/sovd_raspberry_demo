const int LED_REAR_PIN = A0;
const int LED_FRONT_PIN = A2;

// Ajustables (quizá el frontal necesite otro threshold)
const int LED_REAR_REMOVED_THRESHOLD = 850;
const int LED_FRONT_REMOVED_THRESHOLD = 850;

bool rearFaultActive = false;
bool frontFaultActive = false;

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

void setup() {
  Serial.begin(9600);

  delay(500);

  // Estado inicial rear
  int rearValue = readAnalogAverage(LED_REAR_PIN);

  if (rearValue > LED_REAR_REMOVED_THRESHOLD) {
    rearFaultActive = true;
    Serial.println("LED_REAR:FAULT");
  } else {
    rearFaultActive = false;
    Serial.println("LED_REAR:OK");
  }

  // Estado inicial front
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

  delay(100);
}