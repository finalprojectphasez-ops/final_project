import google.protobuf
class Mock:
    def ValidateProtobufRuntimeVersion(self, *args, **kwargs): pass
google.protobuf.runtime_version = Mock()
import tensorflow as tf
print('TF OK')

