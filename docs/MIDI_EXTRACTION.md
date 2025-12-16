# MIDI Extraction Pipeline

Extract piano MIDI from audio or video files using Spotify's [basic-pitch](https://github.com/spotify/basic-pitch) AI model.

## Overview

This pipeline analyzes audio using a neural network trained on piano music and outputs a MIDI file containing the detected notes. It works with:
- **Video files**: MP4, MOV, AVI, MKV, WebM, etc. (audio is extracted automatically)
- **Audio files**: MP3, WAV, FLAC, AAC, M4A, OGG

## Installation

1. Open **Settings** (Cmd+,)
2. Go to **Optional Pipelines** tab
3. Click **Install Dependencies** (~500MB download)
4. Restart the app when prompted
5. Enable the **MIDI Extraction Pipeline** checkbox

## Usage

1. Enable "Extract MIDI" in the pipeline list
2. Click the ⚙️ gear icon to configure options (optional)
3. Drop audio/video files or use "Browse Files"
4. Click "Process Files"

Output: `{filename}_midi.mid` saved to the same folder as the source file.

---

## Presets

| Preset | Best For | Settings |
|--------|----------|----------|
| **Clean** (default) | Most use cases - piano tutorials, solo piano | onset=0.6, frame=0.5, min_length=127ms, melodia=on |
| **Default** | Balanced detection | onset=0.5, frame=0.3, min_length=58ms, melodia=on |
| **Sensitive** | Capturing quiet notes, complex pieces | onset=0.3, frame=0.2, min_length=30ms, melodia=off |
| **Custom** | Manual fine-tuning | User-defined values |

---

## Parameters Explained

### Onset Threshold (0.0 - 1.0)

Controls detection of note **attacks** (when a note starts).

```
Low (0.3)  → Detects more note starts, including weak attacks
High (0.7) → Only detects strong, clear note attacks
```

**Symptoms & Fixes:**
- Too many short ghost notes → **Increase** onset threshold
- Missing note attacks → **Decrease** onset threshold

### Frame Threshold (0.0 - 1.0)

Controls detection of note **sustain** (whether a note is still playing).

```
Low (0.2)  → Notes sustain longer, detects quieter sustained tones
High (0.6) → Notes cut off sooner, only strong sustained tones detected
```

**Symptoms & Fixes:**
- Notes ringing/bleeding too long → **Increase** frame threshold
- Notes cutting off too early → **Decrease** frame threshold

### Min Note Length (10 - 500 ms)

Minimum duration for a note to be included in the output.

```
Low (30ms)  → Includes very short notes (staccato, ornaments)
High (200ms) → Filters out short notes, keeps only sustained notes
```

**Symptoms & Fixes:**
- Too many tiny spurious notes → **Increase** min note length
- Missing staccato/grace notes → **Decrease** min note length

### Melodia Cleanup (on/off)

Applies post-processing algorithm to remove spurious notes.

```
On  → Cleaner output, may remove some legitimate quiet notes
Off → Raw detection output, more notes but potentially noisier
```

**Recommendation:** Keep **on** for most use cases. Turn **off** only if you're missing notes and have already lowered thresholds.

---

## Tuning Guide

### Start with Presets

1. Try **Clean** preset first (default)
2. If missing notes, try **Default**
3. If still missing notes, try **Sensitive**
4. If too noisy, switch to **Custom** and fine-tune

### Fine-Tuning Strategy

```
Too noisy?                      Missing notes?
    │                               │
    ▼                               ▼
┌─────────────────┐         ┌─────────────────┐
│ Increase onset  │         │ Decrease onset  │
│ threshold (+0.1)│         │ threshold (-0.1)│
└────────┬────────┘         └────────┬────────┘
         │                           │
    Still noisy?               Still missing?
         │                           │
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│ Increase frame  │         │ Decrease frame  │
│ threshold (+0.1)│         │ threshold (-0.1)│
└────────┬────────┘         └────────┬────────┘
         │                           │
    Still noisy?               Still missing?
         │                           │
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│ Increase min    │         │ Decrease min    │
│ note length     │         │ note length     │
└────────┬────────┘         └────────┬────────┘
         │                           │
    Still noisy?               Still missing?
         │                           │
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│ Enable melodia  │         │ Disable melodia │
│ cleanup         │         │ cleanup         │
└─────────────────┘         └─────────────────┘
```

### Recommended Settings by Content Type

| Content Type | Onset | Frame | Min Length | Melodia |
|--------------|-------|-------|------------|---------|
| Piano tutorial (clear audio) | 0.6 | 0.5 | 127 | On |
| Solo piano recording | 0.5 | 0.4 | 100 | On |
| Piano with accompaniment | 0.7 | 0.6 | 150 | On |
| Fast/complex pieces | 0.4 | 0.3 | 50 | On |
| Noisy/low quality audio | 0.7 | 0.6 | 150 | On |
| Capture everything (post-edit) | 0.3 | 0.2 | 30 | Off |

---

## Limitations

- **Optimized for piano**: Works best with piano and similar pitched instruments
- **Polyphonic but limited**: Dense chords may not be fully captured
- **Audio quality matters**: Clean audio produces better results
- **Not real-time**: Processing takes time depending on file length

## Tips for Better Results

1. **Use clean audio sources** - Less background noise = better detection
2. **Solo instrument preferred** - Multiple instruments confuse the model
3. **Normalize audio** - Very quiet recordings may need volume boost
4. **Start strict, then loosen** - Begin with Clean preset, lower thresholds if needed
5. **Post-process in DAW** - Use a MIDI editor to clean up remaining artifacts

---

## Technical Details

- **Model**: Spotify basic-pitch (ICASSP 2022)
- **Backend**: CoreML (optimized for Apple Silicon)
- **Output format**: Standard MIDI file (.mid)
- **Dependencies**: basic-pitch, scipy, coremltools, setuptools
