# N-Queens Assignment

So sánh năm SAT encoding tự viết trên Glucose3 và CaDiCaL
với OR-Tools CP-SAT, IBM CP Optimizer, IBM CPLEX MIP và Gurobi MIP.

Repository: https://github.com/nvchien3406/nqueens-assignment

Bài toán là tìm một nghiệm N-Queens hoặc chứng minh vô nghiệm.
Benchmark không liệt kê hoặc đếm tất cả nghiệm.

## Phạm vi

| Phương pháp | Solver |
|---|---|
| Binomial / Pairwise | Glucose3, CaDiCaL 1.9.5 |
| Binary / Bitwise | Glucose3, CaDiCaL 1.9.5 |
| Commander | Glucose3, CaDiCaL 1.9.5 |
| Product đệ quy | Glucose3, CaDiCaL 1.9.5 |
| Sequential Counter | Glucose3, CaDiCaL 1.9.5 |
| CP-SAT | Google OR-Tools |
| CP | IBM CP Optimizer |
| MIP | IBM CPLEX |
| MIP | Gurobi |

Tổng cộng: **5 encoding × 2 SAT solver + 4 đối chứng = 14 cấu hình**.

Các encoder được viết bằng hàm Python.
PySAT chỉ được dùng để gọi solver, không dùng CardEnc để sinh CNF.

## Trạng thái

- Đã triển khai năm encoder và năm module solver.
- Correctness runner đã đạt 98/98 ca, không bỏ qua cấu hình.
- Đã hoàn thành benchmark gồm 756 lượt.
- Đã có comparator và notebook phân tích.
- Đã xuất bảng CSV và biểu đồ PNG/PDF.
- Báo cáo đang được chuẩn bị.
- Docker và W&B chưa nằm trong quy trình thực nghiệm đã kiểm chứng.

## Cấu trúc

```text
src/
├── encodings/
│   ├── common.py
│   ├── binomial.py
│   ├── binary.py
│   ├── commander.py
│   ├── product.py
│   └── sequential_counter.py
├── solvers/
│   ├── sat_solvers.py
│   ├── cp_sat.py
│   ├── cplex_cp.py
│   ├── cplex_mip.py
│   └── gurobi_mip.py
├── evaluation/
│   ├── correctness.py
│   ├── worker.py
│   └── comparator.py
├── utils/
│   ├── validation.py
│   ├── resource_monitor.py
│   └── wandb_logger.py
└── main_experiment.py

configs/
├── main.json
└── pilot.json

notebooks/
└── data_analysis.ipynb

tests/
results/
resume_experiment.py
requirements.txt
requirements-analysis.txt
README.md
```

Các thư mục package có thêm `__init__.py`.

| Thành phần | Vai trò |
|---|---|
| `encodings/common.py` | Biến ô, biến phụ, nhóm ràng buộc và ghép CNF |
| Các encoder | Sinh clause AMO |
| Các solver | Dựng mô hình, gọi solver và giải mã nghiệm |
| `validation.py` | Kiểm tra nghiệm độc lập |
| `worker.py` | Chạy một cấu hình trong tiến trình riêng |
| `resource_monitor.py` | Giám sát thời gian và RSS, dọn tiến trình |
| `correctness.py` | Kiểm tra các cấu hình trên bàn cờ nhỏ |
| `main_experiment.py` | Điều phối và lưu từng lượt benchmark |
| `comparator.py` | Tổng hợp dữ liệu đã lưu |
| `data_analysis.ipynb` | Kiểm tra dữ liệu, tạo bảng và biểu đồ |
| `resume_experiment.py` | Tiếp tục thí nghiệm cụ thể bị gián đoạn |

## Mô hình

Một nghiệm là danh sách `q`, trong đó `q[row] = col`.
Hàng và cột được đánh số từ 0.
Mọi nghiệm SAT được kiểm tra bằng cùng hàm `validate(q)`.

### SAT

Biến ô:

```python
x[row, col] = 1 + row * n + col
```

- Hàng và cột: ALO và AMO, tức đúng một hậu.
- Đường chéo: chỉ AMO.
- Biến phụ được cấp liên tục sau N², không trùng giữa các nhóm.
- Interface encoder:

```python
encode_amo(variables, top_id) -> (clauses, new_top_id)
```

| Encoder | Phiên bản |
|---|---|
| Binomial | Clause cấm cùng đúng cho mỗi cặp biến |
| Binary | Mã nhị phân cho vị trí biến trong nhóm |
| Commander | Nhóm tối đa 3 biến; liên kết hai chiều; đệ quy trên commander |
| Product | Lưới hai chiều; đệ quy trên biến phụ; pairwise khi nhóm có tối đa 4 biến |
| Sequential | Chuỗi biến phụ biểu diễn thông tin các biến đúng phía trước |

### CP và CP-SAT

N biến nguyên `q[row]` thuộc miền `[0, N−1]`, cùng ba ràng buộc:

```text
AllDifferent(q[row])
AllDifferent(q[row] + row)
AllDifferent(q[row] - row)
```

### MIP

N² biến nhị phân theo ô:

- Tổng mỗi hàng bằng 1.
- Tổng mỗi cột bằng 1.
- Tổng mỗi đường chéo có ít nhất hai ô không quá 1.
- Mục tiêu hằng 0.

Không thêm ràng buộc phá đối xứng thủ công.
Các cơ chế nội bộ của solver được giữ theo cấu hình wrapper.

## Cài đặt trên Windows

Môi trường thực nghiệm sử dụng Python 3.12.10 và `.venv`.

Từ thư mục gốc repository:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Để chạy notebook:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-analysis.txt
```

### Gurobi

Cần giấy phép phù hợp để chạy mô hình lớn.
Thực nghiệm sử dụng Academic WLS và cần kết nối internet.

File giấy phép được lưu ngoài repository.

### IBM CPLEX và CP Optimizer

Thực nghiệm sử dụng IBM ILOG CPLEX Optimization Studio 22.2,
cài tại:

```text
C:\Program Files\IBM\ILOG\CPLEX_Studio222
```

Sau khi cài các Python package và có quyền sử dụng Studio,
cấu hình engine cho môi trường ảo:

```powershell
.\.venv\Scripts\docplex.exe config --upgrade "C:\Program Files\IBM\ILOG\CPLEX_Studio222"
```

Chỉ định CP Optimizer cho terminal hiện tại:

```powershell
$env:CPO_EXECUTABLE = (Resolve-Path ".\.venv\Scripts\cpoptimizer.exe").Path
```

Cần thực hiện lại bước cấu hình engine nếu tạo lại `.venv`.
Đường dẫn Studio có thể khác trên máy khác.

Không đưa file giấy phép hoặc thông tin xác thực vào Git.

## Kiểm tra tính đúng

Kiểm tra encoder:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_encodings.py -q -p no:cacheprovider
```

Kiểm tra toàn bộ 14 cấu hình qua worker:

```powershell
$env:CPO_EXECUTABLE = (Resolve-Path ".\.venv\Scripts\cpoptimizer.exe").Path
.\.venv\Scripts\python.exe -B -m src.evaluation.correctness --include-cplex
```

Các kích thước: `1, 2, 3, 4, 5, 6, 8`.

Kết quả đã lưu:

```text
Passed: 98/98
Failed: 0; Skipped: 0
```

N=2 và N=3 phải UNSAT; các kích thước còn lại phải SAT
với nghiệm hợp lệ.

## Benchmark chính

Cấu hình: `configs/main.json`.

| Thông số | Giá trị |
|---|---|
| N | 4, 8, 9, 16, 25, 27, 36, 49, 64, 81, 100, 125, 216, 343, 512, 729, 1000, 1331 |
| Số cấu hình | 14 |
| Số lần lặp | 3 |
| Tổng số lượt | 756 |
| Giới hạn toàn tiến trình | 100 giây/lượt |
| Ngưỡng RSS lấy mẫu | 8192 MiB/lượt |
| Chu kỳ lấy mẫu | 50 ms |
| Chạy đồng thời | Một lượt tại một thời điểm |
| Solver CP/MIP | Một worker/thread |
| Seed | Mặc định của solver |

Đây là thông số thực nghiệm tự chọn.

Chạy một thí nghiệm mới:

```powershell
$env:CPO_EXECUTABLE = (Resolve-Path ".\.venv\Scripts\cpoptimizer.exe").Path
.\.venv\Scripts\python.exe -B -m src.main_experiment --config configs/main.json
```

Mỗi lần gọi tạo một thư mục kết quả mới.

Hiện `configs/pilot.json` có cùng nội dung với `main.json`;
không dùng file này với kỳ vọng chạy thử nhanh.
Cấu hình của các pilot trước được giữ trong thư mục kết quả tương ứng.

## Kết quả đã hoàn thành

Thí nghiệm chính:

```text
results/experiments/20261008T102037Z_10c488e7/
```

| Trạng thái | Số lượt |
|---|---:|
| SAT, nghiệm hợp lệ | 612 |
| TIMEOUT | 101 |
| MEMORY_LIMIT | 42 |
| ERROR | 1 |
| Tổng | 756 |

Không thiếu hoặc trùng lượt chạy.
Glucose3 + Commander và CPLEX CP đều giải thành công 54/54 lượt.

Đây là kết quả của cấu hình, phiên bản và môi trường đã lưu;
không phải khẳng định hiệu năng chung cho mọi máy hoặc mọi thiết lập.

### Quy ước số đo

- `build_s`: dựng mô hình theo wrapper.
- `solve_s`: thời gian quanh lời gọi API; có thể gồm presolve,
  chuyển dữ liệu và khởi động engine.
- `solver_call_wall_s`: thời gian toàn bộ hàm solver.
- `total_wall_s`: toàn bộ tiến trình, gồm khởi động Python,
  import, dựng mô hình, giải, xử lý kết quả và dọn dẹp.
- `peak_rss_mib`: đỉnh tổng RSS quan sát được của cây tiến trình.

### Gián đoạn và giới hạn nghiên cứu

Sau 239 lượt đầu, thực nghiệm bị gián đoạn do áp lực bộ nhớ Windows.
Paging file được cấu hình thêm trên ổ E và phần dọn tiến trình
của bộ giám sát được sửa. Sau đó chạy tiếp 517 lượt.

Dấu vết phiên chạy được lưu qua `resume_session`
và metadata trong `resume_backups/`.

Một lượt CaDiCaL + Binary tại N=1000, repeat=1 kết thúc bất thường.
Bản ghi ERROR được giữ nguyên.

Giới hạn cần xét khi diễn giải:

- Chỉ ba lần lặp mỗi nhóm, seed mặc định.
- Giám sát RSS theo chu kỳ có thể bỏ sót đỉnh ngắn.
- RSS có thể tính trùng bộ nhớ dùng chung giữa tiến trình.
- Ngưỡng RAM không phải giới hạn cứng do hệ điều hành áp đặt.
- Môi trường thay đổi giữa hai giai đoạn chạy.
- Thống kê thời gian/RAM chỉ xét lượt thành công;
  phải đọc cùng số lượt thất bại.

Script `resume_experiment.py` hiện gắn với đường dẫn thí nghiệm
trên máy phát triển. Cần kiểm tra đường dẫn và phiên bản mã
trước khi dùng trên máy khác.

## Tổng hợp và notebook

Tổng hợp thí nghiệm chính:

```powershell
.\.venv\Scripts\python.exe -B -m src.evaluation.comparator "results/experiments/20261008T102037Z_10c488e7"
```

Lệnh tạo `analysis.json` và `analysis.csv`.

Mở `notebooks/data_analysis.ipynb` trong VS Code,
chọn kernel của `.venv`, rồi Run All.

Trên máy khác, sửa biến `ROOT` trong notebook cho đúng đường dẫn.

Notebook xuất vào `notebook_analysis/` của thí nghiệm:

| File | Nội dung |
|---|---|
| `status_summary.csv` | Số lượt theo trạng thái và tỷ lệ thành công |
| `group_statistics.csv` | Median, IQR và số mẫu từng nhóm |
| `errors.csv` | Các lượt ERROR |
| `success_counts.csv` | Số lượt thành công theo N/phương pháp |
| `cnf_sizes.csv` | Kích thước 90 mô hình SAT |
| `runtime.png/pdf` | Median thời gian và vùng Q1–Q3 |
| `memory.png/pdf` | Median RAM và vùng Q1–Q3 |
| `success_counts.png/pdf` | Heatmap số lượt thành công |
| `cnf_sizes.png/pdf` | Số biến và clause |

Q1–Q3 không phải khoảng tin cậy.
Nhóm không có lượt thành công để trống số đo thời gian/RAM.

Kích thước CNF được tính bằng cách cộng chi phí AMO theo độ dài nhóm,
không dựng toàn bộ CNF lớn. Kết quả khớp 420 bản ghi có thông số CNF.
Đây là kích thước trước tiền xử lý của solver.

## Công việc còn lại

- Viết báo cáo theo mẫu cas-sc.
- Đưa bảng, hình và giới hạn thực nghiệm vào báo cáo.
- Hoàn thiện trích dẫn và mục Data Availability.