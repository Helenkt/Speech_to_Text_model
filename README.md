# Speech_to_Text_model

Faster Whisper Medium model files for local Vietnamese and English speech recognition.

## Download

Download both release assets into this repository directory:

- `model.bin.part01`
- `model.bin.part02`

Rebuild the model weights on Windows:

```powershell
cmd /c copy /b model.bin.part01+model.bin.part02 model.bin
```

On Linux or macOS:

```bash
cat model.bin.part01 model.bin.part02 > model.bin
```

The complete model directory contains:

- `model.bin`
- `config.json`
- `tokenizer.json`
- `vocabulary.txt`

## Integrity

- `model.bin` SHA-256: `9b45e1009dcc4ab601eff815b61d80e60ce3fd8c74c1a14f4a282258286b51ae`
- `model.bin.part01` SHA-256: `89f6ca9320855872ef7c4fa0533efb94e3a0edef794c2c84668273bd49896d2a`
- `model.bin.part02` SHA-256: `af505a8aced835f5cd94d9a74bc943551f452a651b325d1a75a78e69734a4b68`
