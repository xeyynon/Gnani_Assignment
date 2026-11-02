from . import envfile as _envfile

_envfile.load()      # .env first: STT_PROVIDER and TTS_PROVIDER are read the moment their modules are imported
