# Pipeline huấn luyện online v0

Pipeline chạy được từ video/feature tới train, validation, checkpoint và replay ra interval. Đây là **baseline hạ tầng**, chưa tái lập MATR/OnPoint và chưa có kết quả huấn luyện trên IKEA/IndustReal. Mặc định một task đã định nghĩa, một người/lượt mục tiêu đang mở, không hỗ trợ các lượt chồng lấp. Miền đích exocentric; dùng ego phải ghi rõ trong config.

## 1. Luồng và cấu trúc

```text
Video + nhãn toàn lượt đã kiểm tra
  → manifest JSONL
  → frozen frame-wise RGB encoder → features.npy + timestamps.npy
  → FeatureDataset / DataLoader (recordings)
  → chunks tuần tự, giữ hidden state
  → LayerNorm + projection + unidirectional GRU
  → membership / start / completion logits
  → masked weighted BCE → optimizer → scheduler
  → checkpoint last/best + validation replay
  → decoder online → events start/end + observed_until/emitted_at
```

| Module | Trách nhiệm |
| --- | --- |
| [train.py](../train.py) / [training/cli.py](../videosegmentation/training/cli.py) | Runner `fit`, `validate-data`, `extract-features`, `evaluate`, `predict`, `make-demo` |
| [config.py](../videosegmentation/training/config.py) | Dataclass config YAML, kiểm tra key/giá trị, đường dẫn tương đối theo config |
| [data.py](../videosegmentation/training/data.py) | Manifest, split/group validation, memory-mapped Dataset, targets/masks, collate/chunks |
| [features.py](../videosegmentation/training/features.py) | Video PTS → feature RGB theo frame; cache theo recording |
| [model.py](../videosegmentation/training/model.py) | Baseline GRU causal, nhận/trả hidden state |
| [losses.py](../videosegmentation/training/losses.py) | Objective factory; weighted BCE ba head với ignore mask |
| [optim.py](../videosegmentation/training/optim.py) | AdamW/SGD; cosine/step/none scheduler |
| [trainer.py](../videosegmentation/training/trainer.py) | TBPTT, AMP CUDA, gradient clipping, validation, logging và lựa chọn best theo val loss |
| [checkpoint.py](../videosegmentation/training/checkpoint.py) | Save qua file tạm rồi replace; optimizer/scheduler/scaler/RNG và epoch resume |
| [streaming.py](../videosegmentation/training/streaming.py) | Giữ lượt qua pause, confirmation và replay theo thời gian |
| [metrics.py](../videosegmentation/training/metrics.py) | Single-task interval AP/F1, completion/timely recall, delay và false completions/phút |

Downloader hiện có giữ nguyên vai trò tải/giải nén. Parser nhãn native của mỗi dataset sẽ xuất manifest chung; không đặt nhánh IKEA/IndustReal vào trainer.

## 2. Chạy thử toàn pipeline trên Colab

Mount Drive trong cell Python:

```python
from google.colab import drive
drive.mount('/content/drive')
```

Clone/cài từ notebook, hoặc `git pull --ff-only` nếu repo đã clone:

```python
!git clone https://github.com/khaihoang004/VideoSegmentation.git /content/VideoSegmentation
%cd /content/VideoSegmentation
%pip install -q -e '.[train,video]'
```

Lệnh dưới là **shell**; khi dùng cell Colab thêm `!` trước `python`:

```bash
python train.py make-demo --output-dir /content/drive/MyDrive/Datasets/pipeline_demo_v0
python train.py validate-data --config /content/drive/MyDrive/Datasets/pipeline_demo_v0/config.yaml
python train.py fit --config /content/drive/MyDrive/Datasets/pipeline_demo_v0/config.yaml
python train.py evaluate --checkpoint /content/drive/MyDrive/Datasets/pipeline_demo_v0/run/best.pt --split test --output /content/drive/MyDrive/Datasets/pipeline_demo_v0/test_report.json
```

Demo có feature giả, positive/negative recordings và tín hiệu dễ học; chỉ kiểm tra luồng thực thi. Không dùng điểm demo để kết luận chất lượng video model. Không ghi đè thư mục demo đã có; chọn tên mới khi cần tạo lại. `.[train]` đủ nếu đã có feature, không cần `video` extras.

## 3. Dữ liệu thật: cần nhãn đúng cấp trước

**Chưa có converter tự động từ atomic action của IKEA/IndustReal sang task-instance.** Cần xác định task và gán/kiểm tra toàn lượt theo [datasets.md](datasets.md). [examples/task_manifest.jsonl](../examples/task_manifest.jsonl) là mẫu minh họa chứa đường dẫn/mốc giả phải thay, không phải nhãn đã đọc từ Drive.

Mỗi dòng JSONL là một recording/view:

```json
{
  "schema_version": 1,
  "recording_id": "trial001_top",
  "group_id": "trial001_all_views",
  "split": "train",
  "dataset": "IKEA_ASM",
  "view_domain": "exo",
  "task_definition_version": "ikea_pilot_v1",
  "video_path": "/content/drive/MyDrive/Datasets/IKEA_ASM/extracted/REPLACE/video.avi",
  "duration": 60.0,
  "coverage": [[0.0, 60.0]],
  "instances": [
    {"instance_id": "trial001_001", "start": 5.0, "end": 35.0, "status": "completed"}
  ]
}
```

- Thời gian là giây từ frame đầu đã decode, interval `[start,end)`. `duration` chỉ phục vụ kiểm tra/evaluator, không đưa vào model hay decoder.
- `coverage` là vùng **đã gán đầy đủ nhãn cho task mục tiêu**. Chỉ đặt `[0,duration)` nếu thực sự đã kiểm tra cả background và tất cả lượt. Vùng ngoài coverage không là negative.
- `instances: []` với coverage đầy đủ là negative recording. Với video chưa gán nhãn để `predict`, dùng `coverage: []`, `instances: []`.
- `completed` có start/end rõ được dùng để học membership/start/completion. `aborted` học membership/start nhưng không có completed target ở end.
- `unknown`, `ongoing` hoặc bất kỳ lượt bị censor đều được ignore trên phần quan sát của lượt ở v0; không coi là background. `null start` cần `left_censored: true`; `null end` cần ongoing/unknown hoặc `right_censored: true`. V0 chưa tận dụng nhãn completion riêng của lượt mất start.
- `group_id` phải gom mọi view/copy của lần quay gốc, và có thể gom theo participant nếu muốn subject-disjoint. Trình kiểm tra từ chối group hoặc cùng media/features path nằm ở nhiều split; không tự nhận ra hai file copy đổi tên nếu metadata nhóm sai.
- Một manifest có các dòng `train`, `val`, `test`. Cùng `task_definition_version` phải biểu diễn cùng một mục tiêu trong một lần chạy; không dùng một model đơn task để ngầm trộn nhiều công việc khác nhau.

### 3.1. Trích feature RGB

Chuẩn bị manifest nhãn thật, rồi chạy:

```bash
python train.py extract-features --manifest /content/drive/MyDrive/Datasets/IKEA_ASM/processed/v0/video_manifest.jsonl --output-manifest /content/drive/MyDrive/Datasets/IKEA_ASM/processed/v0/features_manifest.jsonl --output-dir /content/drive/MyDrive/Datasets/IKEA_ASM/processed/v0/features --sample-hz 2 --device auto
```

Encoder là ResNet18 ImageNet **đóng băng**, xử lý từng frame độc lập ở eval mode. Full-frame letterbox 224 giữ toàn vùng quan sát; không dùng center crop mặc định. Feature dimension 512. Đây là encoder đơn giản để pilot, chưa chọn backbone cuối. `--weights none` chỉ cho debug, không phải pretrained feature.

PyAV đọc presentation timestamp, không suy thời gian bằng FPS trung bình. Frame đầu được quy về 0; gán nhãn phải dùng cùng gốc thời gian. Từ chối PTS thiếu, trùng/đảo. Mốc feature là frame cuối được quan sát; không center-window hay pooling cả video. Sampling là cấu hình thí nghiệm, **2 Hz chưa phải yêu cầu chốt của bài toán**.

Feature/timestamps/cache weights và file tạm đều nằm trong `--output-dir` (đặt trên Drive). Chạy lại dùng cache các recording hoàn tất; recording đang dở phải trích lại. Đổi source/weights/sampling cần output mới hoặc `--overwrite`. Không tự sửa raw video/nhãn. Nếu có feature đã kiểm tra, tự khai báo `features`:

```json
"features": {
  "path": "features/trial001.npy",
  "timestamps_path": "features/trial001.timestamps.npy",
  "encoder": "name_and_version_of_audited_encoder",
  "causal": true,
  "timestamp_semantics": "last_observed_frame"
}
```

`.npy` feature có shape `[T,D]`, timestamps `[T]` tăng chặt. Đường dẫn tương đối theo manifest hoặc `data.root`. `causal: true` là khai báo provenance cần audit thật; validator không thể chứng minh tính causal của feature bên ngoài chỉ từ cờ này.

### 3.2. Huấn luyện

Sửa [configs/online_gru.yaml](../configs/online_gru.yaml) theo task và manifest thật, chọn output mới:

```bash
python train.py validate-data --config configs/online_gru.yaml
python train.py fit --config configs/online_gru.yaml
```

Membership là **thuộc toàn lượt**, kể cả pause; không phải đang chuyển động. Boundary target được đặt ở feature đầu tại/sau mốc, có thể mở rộng **về sau** theo `boundary_width_seconds`. Không làm nhãn completion dương trước GT. Nếu một boundary nằm sau feature cuối, validator báo lỗi: cần kiểm tra sampling/censoring và guideline, không tự gán EOF thành completed.

DataLoader shuffle các recording độc lập. Trong recording, chunk luôn theo thứ tự; hidden state giữ qua chunk và detach giữa các bước TBPTT. GPU chỉ nhận chunk hiện tại; feature lớn đọc memory-map. Không reset state ở mỗi window. Mặc định batch=1/num_workers=0 phù hợp bắt đầu trên Drive; tăng theo RAM/I/O đã đo.

```text
output_dir/
├── run.json                    # config đã resolve, manifest fingerprint
├── last.pt                     # epoch hoàn tất gần nhất
├── best.pt                     # val loss tốt nhất; chưa tune trên test
├── epoch_0005.pt               # tùy save_epoch_every
├── metrics/epoch_0001.json
└── validation_events.json      # event log replay và summary recording
```

Checkpoint chứa model, optimizer, scheduler, AMP scaler, epoch/global step, best loss và RNG Python/NumPy/Torch/DataLoader. Ghi qua file tạm rồi replace, giữ file cũ tới khi file mới ghi xong. Fingerprint hiện kiểm tra manifest/nhãn/path, chưa hash toàn bộ payload feature; thay feature phải coi là thí nghiệm mới.

Resume sau khi Colab gián đoạn:

```bash
python train.py fit --config configs/online_gru.yaml --resume /content/drive/MyDrive/Datasets/experiments/ikea_pilot_v1/online_gru_run01/last.pt
```

Resume **từ cuối epoch**, phần epoch đang dở chạy lại. Giữ output, config/schedule horizon và dữ liệu; không đổi tổng epochs của cosine schedule âm thầm. Có thể đổi device/logging, nhưng không bảo đảm bitwise reproducibility khi đổi phần cứng/CUDA. CPU epoch-resume được kiểm tra so với chạy liền.

Với objective/schedule mới, tạo config/output mới và dùng `--warm-start PATH` để chỉ lấy weights, reset optimizer/scheduler. Đây là đường để fine-tune student sau này. **Chưa có teacher/distillation loss kiểu OnPoint trong v0**; thêm objective ở loss factory và training stage tương ứng, không bật một cờ chưa có tác dụng.

## 4. Evaluate và predict

```bash
python train.py evaluate --checkpoint /path/to/best.pt --split test --output /path/to/test_report.json
python train.py predict --checkpoint /path/to/best.pt --manifest /path/to/unlabelled_features.jsonl --split predict --output /path/to/predictions.json
```

Decoder mở lượt bằng start signal, giữ lượt khi membership giảm, và chỉ đóng bằng completion signal. Có thể yêu cầu nhiều feature xác nhận; end là mốc candidate đầu tiên còn `emitted_at` muộn tương ứng. Một start mới có thể thay candidate chưa hoàn thành; số lần thay được báo trong stream summary, không tự kết luận GT aborted. Hỗ trợ start lượt mới đúng lúc end lượt cũ. EOF không đóng lượt; candidate còn mở được báo riêng.

Events lưu `event_id`, start/end, confidence, `observed_until`, `emitted_at`, task version. Confidence chỉ là score head, chưa calibration. Decoder threshold/patience/min-duration phải chọn trên validation; không chỉnh theo test.

**Đồng hồ v0 là feature replay mô phỏng:** chunk chỉ sẵn sàng ở timestamp cuối chunk, cộng thời gian temporal head/transfer/decoder theo virtual clock. Vì vậy event của frame trước không được ghi lùi thời gian phát. `inference_chunk_size: 1` cho từng feature; chunk lớn có thêm thời gian chờ. Báo rõ `feature_extraction_cost_included: false`; chưa phải latency camera→clip thực. Chưa có live camera service hoặc xuất/encode clip.

Metric là single-task interval AP/F1 theo tIoU, start/end MAE trên TP; completion-event matching one-to-one theo end tolerance; timely recall theo latency budget; early false completion, late TP và báo giả/phút vùng thời gian đã annotate. Metric AP chỉ đo hình học có thể vẫn cao khi emit quá sớm: completion metrics phạt riêng. Predictions/GT chạm vùng chưa gán/unknown bị ignore và **báo số lượng cùng coverage**, không coi là negative hoặc âm thầm bỏ. Test có thể vượt ngân sách báo giả đã chọn trên validation.

Các metric hiện là baseline v0, chưa đủ bộ WARI/SMS, timing-only controls, calibration hay mọi trường hợp trong [protocol nghiên cứu](related_work_and_evaluation.md). Không gọi mean AP một task là mAP nhiều lớp. Không dùng điểm pipeline này để tuyên bố đã giải quyết toàn yêu cầu ứng dụng.

## 5. Kiểm tra

```bash
python -m pytest -q
```

Kiểm tra causal prefix/chunk equivalence, targets qua pause/unknown/aborted, group leakage, clock của replay, EOF/duplicate, adjacent instances, metric phản ánh delay/early completion, checkpoint resume, và optional video PTS/cache test khi có `video` extras. Demo, feature và checkpoint sinh trong chạy thử không được commit vào repo.
