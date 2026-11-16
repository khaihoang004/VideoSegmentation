# Train full IKEA_ASM on Colab T4

[Open training notebook in Colab](https://colab.research.google.com/github/khaihoang004/VideoSegmentation/blob/codex/ikea-full-colab/notebooks/ikea_asm_full_colab.ipynb)

[Open account/runtime check](https://colab.research.google.com/github/khaihoang004/VideoSegmentation/blob/codex/ikea-full-colab/notebooks/colab_account_check.ipynb)

Select a Colab T4 runtime, then **Run all**. Grant Google Drive access when Google requests it. The training notebook contains its own checksummed runtime; no source ZIP upload or manual clone is required.

The account check refuses a local kernel. It reports the authorized Drive API account/storage and the currently assigned GPU. Drive authorization may use a different account from Colab's GPU allocation. Free GPU hours remaining cannot be determined from this cell.

## Protocol and stages

- Camera `dev3`, original cross-environment split: **254 training /117 test videos**, 33 classes including NA. Missing videos are errors, not an automatic subset.
- Dataset is expected under `MyDrive/Datasets/IKEA_ASM/extracted`, with native SQLite annotations, indexing files and extracted RGB top-view videos. The notebook also supports bounded discovery of equivalent directory layouts.
- Section 6 copies **one video at a time** to the Colab VM and caches frozen I3D features on Drive. It completes all 371 feature caches before temporal training. The first pass can require multiple Colab sessions.
- Section 7 trains the pinned ProTAS temporal model for **50 epochs /12700 optimizer updates**. The per-invocation training time budget is 5400 seconds, checked after a recording; reconnect and Run all to resume when needed.
- Section 8 evaluates the fixed-final checkpoint on all 117 test videos: frame accuracy, accuracy excluding NA, Edit and F1@10/25/50. It also exports predictions and action intervals `[start_frame,end_frame)`.

Original RGB files stay on Drive. Cache/checkpoint/log/results live under:

```text
MyDrive/VideoSegmentationRuns/IKEA_ProTAS/
  i3d_rgb_cache_stride2/
  full/stride2/full_v2_50epochs/
    console.log
    model/last.pt
    model/test.json
    model/predictions/
    model/segments/
```

Checkpointing to Drive is intentional. This release saves every **50 training recordings**, at every epoch end, and at a controlled time-budget stop. After abrupt VM reclamation, work since the last committed checkpoint can be repeated; an interrupted feature recording is recomputed. This is runner resume policy, not the author's original every-five-epoch policy. No guaranteed runtime availability or completion within one free session is assumed.

## Sources and limits

The readable runtime is in `colab_runtime/`; its manifest verifies the exact embedded source files. It is a separate minimal Python project so it does not change the existing downloader/training package.

- ProTAS: `Yuhan-Shen/ProTAS`, commit `0f04ee6b3c4370ce22f9230bca42e9aabe47b428`.
- IKEA I3D implementation: `IkeaASM/IKEA_ASM_Dataset`, commit `6fc2d9ea67557ca748b43257e99e3beb6d3cf069`.
- Pretrained RGB weights are downloaded and SHA256-verified; vendor source, weights, datasets and user notebook outputs are not published here.

This is an IKEA adaptation with frozen RGB-only I3D **1024-dimensional features**, rather than the paper's 2048-dimensional representation. Architecture/objective follow pinned ProTAS. Graph reference storage is cloned for correct CPU checkpoint loading; CUDA already separated the original reference in the runtime previously tested. This does not claim to reproduce paper benchmark scores or establish IKEA SOTA. Full Colab training has not been completed by this release; this notebook is the executable setup for that experiment.
