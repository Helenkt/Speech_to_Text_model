# Speech_to_Text_model

Faster Whisper Medium model files for local Vietnamese and English speech recognition.

## Download

Download all eight release assets into this repository directory:

- `model.bin.part01`
- `model.bin.part02`
- `model.bin.part03`
- `model.bin.part04`
- `model.bin.part05`
- `model.bin.part06`
- `model.bin.part07`
- `model.bin.part08`

Rebuild the model weights on Windows:

```powershell
cmd /c copy /b model.bin.part01+model.bin.part02+model.bin.part03+model.bin.part04+model.bin.part05+model.bin.part06+model.bin.part07+model.bin.part08 model.bin
```

On Linux or macOS:

```bash
cat model.bin.part{01..08} > model.bin
```

The complete model directory contains:

- `model.bin`
- `config.json`
- `tokenizer.json`
- `vocabulary.txt`

## Integrity

- `model.bin` SHA-256: `9b45e1009dcc4ab601eff815b61d80e60ce3fd8c74c1a14f4a282258286b51ae`
- `model.bin.part01` SHA-256: `5f898fc5a90e1ca242a5bafc5f79752f407c5d291e0558fd801ab67c82ff6453`
- `model.bin.part02` SHA-256: `1d81c5cfd5e87693a7780c6d4025287047c85323f3537613809c57669dda2e8d`
- `model.bin.part03` SHA-256: `379f7d960071a378439297b3e7c332c7dc72df569e63de55a9fef8028980092d`
- `model.bin.part04` SHA-256: `21cd264970235e5282f9a98f5d68b44a0b69696c3c0cd5eab1a4f14296740888`
- `model.bin.part05` SHA-256: `d50283e7939559a5610b3b705fa56aabc6b2af61cb671225c89fcd6b496c6188`
- `model.bin.part06` SHA-256: `7d9b8f6a0462893d12aa230f47b8e24b31ce99f940cc2aecc15d884bcbff0fd1`
- `model.bin.part07` SHA-256: `0fde01fc198efe5416aa0a344792e24583e2e04c806caf8b1e9b4e4a2dcc4d34`
- `model.bin.part08` SHA-256: `75982cdd26ccf058bfdc3e1179c01182a86ec83ee3acd09718e998387100a6f3`
