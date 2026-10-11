import sys
try:
    import google.protobuf
    class DummyDomain: PUBLIC = 1
    class DummyRuntimeVersion:
        Domain = DummyDomain
        def ValidateProtobufRuntimeVersion(self, *args, **kwargs): pass
    google.protobuf.runtime_version = DummyRuntimeVersion()
    sys.modules['google.protobuf.runtime_version'] = DummyRuntimeVersion()
except Exception: pass

import mediapipe as mp
print('MediaPipe OK!')
