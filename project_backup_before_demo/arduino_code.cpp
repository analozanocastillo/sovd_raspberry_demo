const int LED_REAR_PIN = A0;
 
const int LED_REMOVED_THRESHOLD = 850;
 
bool faultActive = false;
 
int readAnalogAverage(int pin) {
  long sum = 0;
 
  for (int i = 0; i < 10; i++) {
    sum += analogRead(pin);
    delay(2);
  }
 
  return sum / 10;
}
 
void setup() {
  Serial.begin(9600);
 
  delay(500);
 
  int ledValue = readAnalogAverage(LED_REAR_PIN);
 
  if (ledValue > LED_REMOVED_THRESHOLD) {
    faultActive = true;
    Serial.println("LED_REAR:FAULT");
  } else {
    faultActive = false;
    Serial.println("LED_REAR:OK");
  }
}
 
void loop() {
  int ledValue = readAnalogAverage(LED_REAR_PIN);
 
  bool ledRemoved = ledValue > LED_REMOVED_THRESHOLD;
 
  if (ledRemoved && !faultActive) {
    faultActive = true;
    Serial.println("LED_REAR:FAULT");
  }
 
  if (!ledRemoved && faultActive) {
    faultActive = false;
    Serial.println("LED_REAR:OK");
  }
 
  delay(100);
}
