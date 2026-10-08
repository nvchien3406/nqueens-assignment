# N-Queens Assignment

Project so sánh năm SAT encoding tự viết trên Glucose3 và CaDiCaL
với bốn phương pháp đối chứng: OR-Tools CP-SAT, IBM CP Optimizer,
IBM CPLEX MIP và Gurobi MIP.

Bài toán là tìm một cách đặt N quân hậu không tấn công nhau
trên bàn cờ N × N, hoặc chứng minh không có nghiệm.
Project không liệt kê hay đếm toàn bộ nghiệm trong benchmark.

Repository: https://github.com/nvchien3406/nqueens-assignment

## Phạm vi so sánh

| Nhóm | Phương pháp | Solver |
|---|---|---|
| SAT | Binomial / Pairwise | Glucose3, CaDiCaL 1.9.5 |
| SAT | Binary / Bitwise | Glucose3, CaDiCaL 1.9.5 |
| SAT | Commander | Glucose3, CaDiCaL 1.9.5 |
| SAT | Product đệ quy | Glucose3, CaDiCaL 1.9.5 |
| SAT | Sequential Counter | Glucose3, CaDiCaL 1.9.5 |
| CP-SAT | Biến nguyên và AllDifferent | OR-Tools CP-SAT |
| CP | Biến nguyên và AllDifferent | IBM CP Optimizer |
| MIP | Biến nhị phân theo ô | IBM CPLEX MIP |
| MIP | Biến nhị phân theo ô | Gurobi |

Tổng cộng: **5 encoding × 2 SAT solver + 4 đối chứng = 14 cấu hình**.

Các encoder AMO được tự viết bằng hàm Python.
PySAT được dùng để gọi SAT solver, không dùng CardEnc để sinh các encoding.

## Trạng thái hiện tại

- Đã triển khai năm encoder, validator và bộ test encoding.
- Đã chuyển Product sang phiên bản đệ quy và bổ sung test cho nhóm lớn.
- SAT, CP-SAT và Gurobi đã vượt qua các kiểm tra N-Queens nhỏ
  trước lần cập nhật Product và mở rộng cấu hình gần nhất.
- Gurobi đã giải được N = 64 và nghiệm đã qua validator.
- Đã triển khai worker chạy tiến trình riêng và bộ giám sát thời gian/RAM.
- Đã có correctness runner; cần chạy lại sau thay đổi encoding.
- Hai module CPLEX đã có code, nhưng chưa xác nhận chạy trong project mới;
  phần môi trường IBM đang chờ hoàn tất.
- Đã có cấu hình pilot.
- `main_experiment.py` và `evaluation/comparator.py` đang chờ triển khai.
- Chưa có kết quả benchmark chính thức.
- Docker, W&B và notebook phân tích là các phần tùy chọn chưa triển khai.

Các kiểm tra nhỏ đã chạy chưa đủ để xác nhận cơ chế dừng khi vượt
timeout hoặc RAM. Cần kiểm tra riêng các cơ chế này trước benchmark lớn.

## Cấu trúc

```text
src/
├── __init__.py
├── encodings/
│   ├── __init__.py
│   ├── common.py
│   ├── binomial.py
│   ├── binary.py
│   ├── commander.py
│   ├── product.py
│   └── sequential_counter.py
├── solvers/
│   ├── __init__.py
│   ├── sat_solvers.py
│   ├── cp_sat.py
│   ├── cplex_cp.py
│   ├── cplex_mip.py
│   └── gurobi_mip.py
├── evaluation/
│   ├── __init__.py
│   ├── correctness.py
│   ├── worker.py
│   └── comparator.py
├── utils/
│   ├── __init__.py
│   ├── validation.py
│   ├── resource_monitor.py
│   └── wandb_logger.py
└── main_experiment.py

tests/
└── test_encodings.py

configs/
└── pilot.json

results/
notebooks/
README.md
requirements.txt
.gitignore
.env.example
Dockerfile
```

Các file có trong cây thư mục không đồng nghĩa với việc đã triển khai
hoặc kiểm thử đầy đủ; xem mục trạng thái hiện tại.

## Trách nhiệm các phần

| Thành phần | Vai trò |
|---|---|
| `encodings/common.py` | Đánh số biến ô, cấp biến phụ, tạo nhóm và ghép CNF |
| Các file encoder | Sinh clause cho ràng buộc AMO |
| `solvers/sat_solvers.py` | Gọi Glucose3/CaDiCaL, giải mã và kiểm tra nghiệm |
| Các solver CP/MIP | Xây dựng mô hình native và gọi solver tương ứng |
| `evaluation/worker.py` | Chạy một cấu hình trong tiến trình riêng, lưu log và kết quả |
| `evaluation/correctness.py` | Kiểm tra trạng thái và nghiệm trên các ca nhỏ |
| `evaluation/comparator.py` | Dự kiến tổng hợp và so sánh kết quả đã lưu |
| `utils/validation.py` | Kiểm tra nghiệm độc lập với mô hình solver |
| `utils/resource_monitor.py` | Theo dõi thời gian và RSS của cây tiến trình |
| `main_experiment.py` | Dự kiến điều phối các lượt chạy theo cấu hình |
| `configs/` | Cấu hình thí nghiệm |
| `results/` | Kết quả và log |
| `notebooks/` | Dự kiến phân tích và vẽ biểu đồ |

## Mô hình và quy ước

Một nghiệm là danh sách `q` có độ dài N:

```python
q[row] = col
```

Chỉ số hàng và cột bắt đầu từ 0. Mỗi nghiệm phải được kiểm tra bằng
`validate(q)`; các solver không cần trả về cùng một bàn cờ.

### SAT

Biến ô tại hàng `row`, cột `col` có ID:

```python
1 + row * n + col
```

- Mỗi hàng và mỗi cột có ALO và AMO: đúng một hậu.
- Mỗi đường chéo chỉ có AMO: nhiều nhất một hậu.
- Biến phụ được cấp sau N² và không dùng chung giữa các nhóm.
- Interface của mỗi encoder:

```python
encode_amo(variables, top_id) -> (clauses, new_top_id)
```

Các phiên bản được triển khai:

| Encoder | Quy tắc |
|---|---|
| Binomial / Pairwise | Một clause cấm cùng đúng cho mỗi cặp biến |
| Binary | Gán mã nhị phân riêng cho vị trí của mỗi biến trong nhóm |
| Commander | Nhóm tối đa 3 biến; liên kết hai chiều với commander; AMO commander bằng đệ quy |
| Product | Lưới hai chiều; đệ quy trên biến phụ hàng/cột; dùng pairwise khi nhóm có tối đa 4 biến |
| Sequential Counter | Chuỗi biến phụ truyền thông tin về các biến đúng ở phía trước |

### CP và CP-SAT

Dùng N biến nguyên `q[row]` trong miền từ 0 đến N − 1:

```text
AllDifferent(q[row])
AllDifferent(q[row] + row)
AllDifferent(q[row] - row)
```

### MIP

Dùng N² biến nhị phân theo ô:

- Tổng mỗi hàng bằng 1.
- Tổng mỗi cột bằng 1.
- Tổng mỗi đường chéo không quá 1.
- Mục tiêu là hằng 0; chỉ cần tìm nghiệm khả thi.

Các mô hình không thêm ràng buộc phá đối xứng thủ công.
Các cơ chế nội bộ của solver được giữ theo cấu hình thực tế của từng wrapper.

## Môi trường và cài đặt

Môi trường phát triển hiện tại: Windows, Python 3.12.10,
virtual environment `.venv`.

Chạy từ thư mục gốc project:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Các phụ thuộc hiện tại:

```text
python-sat==1.9.dev15
pytest==9.1.1
ortools==9.15.6755
gurobipy==13.0.3
psutil==7.2.2
```

Gurobi cần giấy phép phù hợp. Project sử dụng giấy phép Academic WLS.

Phụ thuộc và engine CPLEX sẽ được bổ sung khi hoàn tất môi trường IBM.
Cài thư viện `docplex` đơn lẻ chưa bảo đảm có CP Optimizer engine.
Module CP Optimizer hỗ trợ biến môi trường `CPO_EXECUTABLE`
để chỉ định đường dẫn executable.

Không đưa file giấy phép, API key hoặc thông tin xác thực vào repository.

## Kiểm tra tính đúng

### Kiểm tra encoder

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_encodings.py -q -p no:cacheprovider
```

Bộ test kiểm tra:

- AMO bằng vét cạn các phép gán biến gốc ở những nhóm nhỏ.
- Product đệ quy với nhóm lớn hơn: không biến đúng, một biến đúng
  và mọi cặp biến cùng đúng.
- N-Queens với N = 1, 2, 3, 4, 5, 6, 8 trên cả hai SAT solver.
- Mỗi nghiệm SAT được giải mã và kiểm tra độc lập.

### Kiểm tra qua worker

Mặc định chạy các cấu hình SAT, CP-SAT và Gurobi:

```powershell
.\.venv\Scripts\python.exe -B -m src.evaluation.correctness
```

Nếu tất cả ca được chọn đều đạt, kết quả dự kiến là:

```text
Passed: 84/84
Failed: 0; Skipped: 14
```

Chạy thêm CPLEX khi môi trường đã sẵn sàng:

```powershell
.\.venv\Scripts\python.exe -B -m src.evaluation.correctness --include-cplex
```

Khi đó có 98 ca kiểm tra. Các con số trên là số ca dự kiến,
không phải tuyên bố tất cả đã chạy thành công.

`NOT_RUN/SKIP` không được tính là PASS. Timeout, lỗi giấy phép
và lỗi thực thi không được coi là UNSAT.

Kết quả được lưu trong:

```text
results/correctness/<id>/
├── checks.jsonl
├── summary.json
└── runs/
```

## Cấu hình pilot

`configs/pilot.json` hiện khai báo:

| Thông số | Giá trị |
|---|---|
| N | 16, 32, 64, 128 |
| Số lần lặp | 1 |
| Giới hạn toàn tiến trình mỗi lượt | 30 giây |
| Ngưỡng giám sát RAM | 8192 MiB |
| Cấu hình | 14, trong đó hai CPLEX đang tạm tắt |

Có 48 vị trí kết quả: 40 lượt được chọn chạy và 8 lượt ghi `NOT_RUN`.

Đây là thông số pilot tự chọn, chưa phải cấu hình benchmark chính thức
và không phải yêu cầu bắt buộc của đề bài.

Chưa chạy pilot cho đến khi hoàn thiện chương trình điều phối
và kiểm tra cơ chế giới hạn tài nguyên.

## Quy ước đo và lưu kết quả

- Chạy một cấu hình tại một thời điểm.
- Mỗi lượt chạy trong tiến trình Python riêng.
- Solver CP/MIP được cấu hình một worker/thread.
- Hiện chưa đặt seed riêng; các solver dùng mặc định.
- `build_s`: khoảng thời gian dựng mô hình theo wrapper.
- `solve_s`: thời gian quanh lời gọi API giải, có thể gồm khởi động
  engine, chuyển dữ liệu và presolve.
- `solver_call_wall_s`: thời gian toàn bộ hàm solver.
- `total_wall_s` trong kết quả worker: thời gian toàn bộ tiến trình,
  gồm khởi động Python, import và dọn dẹp.
- `peak_rss_mib`: đỉnh tổng RSS quan sát được của tiến trình và các
  tiến trình con được phát hiện, lấy mẫu mỗi 50 ms.
- Giám sát RAM bằng lấy mẫu không phải giới hạn cứng của hệ điều hành.
- RSS giữa các tiến trình có thể tính trùng bộ nhớ dùng chung.
- Mỗi lượt có thư mục riêng chứa `solver.log`, `result.json` và
  `solver.json` nếu tiến trình con ghi được kết quả.
- Kết quả của các phiên bản encoder khác nhau phải được phân biệt.

Các trạng thái có thể gặp gồm `SAT`, `UNSAT`, `UNKNOWN`, `TIMEOUT`,
`MEMORY_LIMIT`, `LICENSE_ERROR`, `INSTALL_ERROR`, `INVALID_MODEL`,
`ERROR` và `NOT_RUN`.

## Công việc tiếp theo

- Xác nhận lại bộ test sau khi chuyển sang Product đệ quy.
- Hoàn thiện `main_experiment.py`.
- Kiểm tra thực tế cơ chế timeout và dừng cây tiến trình.
- Hoàn thiện `evaluation/comparator.py`.
- Hoàn tất môi trường và kiểm tra hai solver CPLEX.
- Chạy pilot, sau đó chốt cấu hình benchmark chính.
- Tổng hợp kết quả, vẽ biểu đồ và viết báo cáo.