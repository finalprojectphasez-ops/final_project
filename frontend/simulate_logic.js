let activeWarning = null;
let consecutiveNoFace = 0;
let consecutiveNoEyeContact = 0;
let noFaceViolationCounted = false;
let multipleFaceViolationCounted = false;
let eyeContactViolationCounted = false;
let eyeContactViolationsRef = 0;
let faceDetectionViolationsRef = 0;

function simulateFrame(data, frameNum) {
    if (data.error) return;

    if (data.face_count && data.face_count > 1) {
        activeWarning = "⚠️ Only one person should be in the camera frame.";
        if (!multipleFaceViolationCounted) {
            faceDetectionViolationsRef++;
            multipleFaceViolationCounted = true;
        }
        consecutiveNoFace = 0; noFaceViolationCounted = false;
        consecutiveNoEyeContact = 0; eyeContactViolationCounted = false;
    } else if (data.face_present === false) {
        consecutiveNoFace += 1;
        if (consecutiveNoFace >= 2) {
            activeWarning = "⚠️ Please stay in the camera frame.";
            if (!noFaceViolationCounted) {
                faceDetectionViolationsRef++;
                noFaceViolationCounted = true;
            }
        } else {
            // Note: If consecutive is 1, we don't set warning yet, but we shouldn't clear eye contact warning immediately?
            // Wait, if face is missing, it should clear eye contact warning eventually, but right now it doesn't clear until frame 2.
            // Let's just clear it if we transition to no face.
            activeWarning = null;
        }
        multipleFaceViolationCounted = false;
        consecutiveNoEyeContact = 0; eyeContactViolationCounted = false;
    } else if (data.face_present === true) {
        consecutiveNoFace = 0; noFaceViolationCounted = false;
        multipleFaceViolationCounted = false;
        
        if (data.looking_at_camera === false) {
            consecutiveNoEyeContact += 1;
            if (consecutiveNoEyeContact >= 2) {
                activeWarning = "⚠️ Please look at the camera.";
                if (!eyeContactViolationCounted) {
                    eyeContactViolationsRef++;
                    eyeContactViolationCounted = true;
                }
            } else {
                activeWarning = null;
            }
        } else if (data.looking_at_camera === true) {
            consecutiveNoEyeContact = 0; eyeContactViolationCounted = false;
            activeWarning = null;
        } else {
            // null
            if (activeWarning && (activeWarning.includes("camera frame") || activeWarning.includes("Only one person"))) {
                activeWarning = null;
            }
        }
    }
    console.log(`Frame ${frameNum}: activeWarning = ${activeWarning}, faceViolations = ${faceDetectionViolationsRef}, eyeViolations = ${eyeContactViolationsRef}`);
}

console.log("--- Test 1: One person looking at camera ---");
simulateFrame({ face_present: true, face_count: 1, looking_at_camera: true }, 1);
simulateFrame({ face_present: true, face_count: 1, looking_at_camera: true }, 2);

console.log("\n--- Test 2: One person looking away ---");
simulateFrame({ face_present: true, face_count: 1, looking_at_camera: false }, 3);
simulateFrame({ face_present: true, face_count: 1, looking_at_camera: false }, 4);
simulateFrame({ face_present: true, face_count: 1, looking_at_camera: false }, 5);
simulateFrame({ face_present: true, face_count: 1, looking_at_camera: true }, 6); // looks back

console.log("\n--- Test 3: Face outside frame ---");
simulateFrame({ face_present: false, face_count: 0 }, 7);
simulateFrame({ face_present: false, face_count: 0 }, 8);
simulateFrame({ face_present: true, face_count: 1, looking_at_camera: true }, 9); // returns

console.log("\n--- Test 4: Two people in frame ---");
simulateFrame({ face_present: true, face_count: 2 }, 10);
simulateFrame({ face_present: true, face_count: 1, looking_at_camera: true }, 11); // returns to 1 person
