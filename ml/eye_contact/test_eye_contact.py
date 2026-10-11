from calibrate_eye_contact import gaze_to_eye_contact

print("--- Testing Eye Contact Interpretation Layer ---")

# Define some test predictions (Pitch, Yaw)
test_cases = [
    {"name": "1. Center Gaze", "pitch": -0.05, "yaw": 0.0},
    {"name": "2. Moderate Left", "pitch": -0.05, "yaw": -0.15},
    {"name": "3. Moderate Right", "pitch": -0.05, "yaw": 0.15},
    {"name": "4. Moderate Up/Down (Looking at keyboard)", "pitch": -0.25, "yaw": 0.0},
    {"name": "5. Extreme Gaze", "pitch": 0.3, "yaw": 0.4}
]

for tc in test_cases:
    res = gaze_to_eye_contact(tc["pitch"], tc["yaw"])
    print(f"\n{tc['name']} -> Pitch: {tc['pitch']}, Yaw: {tc['yaw']}")
    print(f"   Looking at camera: {res['looking_at_camera']}")
    print(f"   Gaze Score:        {res['gaze_score']}/100")
