# Kết quả chạy lại ca CaDiCaL + Binary, N=1000

Ngày chẩn đoán: **15/10/2026**, múi giờ Việt Nam (UTC+7).

Đây là kết quả bổ sung để phân tích lượt ERROR trong benchmark
`20261008T102037Z_10c488e7`. Hai lượt chẩn đoán không thuộc kế hoạch
756 lượt ban đầu và không được dùng thay thế kết quả, tính median/IQR,
tỷ lệ thành công hoặc vẽ lại biểu đồ của benchmark chính.

## Điều kiện và kết quả

- Mã nguồn encoder và solver không thay đổi so với benchmark gốc.
- Python 3.12.10; python-sat 1.9.dev15; psutil 7.2.2.
- Giới hạn mỗi lượt: 100 giây toàn tiến trình, 8192 MiB RSS.
- RSS được lấy mẫu mỗi 50 ms; giới hạn có thể bị vượt nhẹ giữa các lần lấy mẫu.
- Cả hai lượt bật Python faulthandler. Lượt chẩn đoán stack còn xuất stack
  định kỳ 15 giây; thời gian của lượt này không dùng làm kết quả benchmark thay thế.

| Lượt | Trạng thái | Tổng thời gian (giây) | RSS cao nhất (MiB) | Exit code |
|---|---|---:|---:|---:|
| Lượt gốc, repeat=1 | ERROR | 54.31523360009305 | 8133.86328125 | 3221226505 |
| Chạy lại bằng runner hiện tại | MEMORY_LIMIT | 54.76177950000056 | 8196.34765625 | 15 |
| Chẩn đoán thêm bằng stack định kỳ | MEMORY_LIMIT | 34.35661339999933 | 8199.8125 | 15 |

Lượt gốc có ID `8434701e4c7449ecbe0bc40bbf0b6ed9`.
Lượt chạy lại có ID `8e6183c0758441a3a37a1b42db67e01d`.
Lượt chẩn đoán stack không được cấp run_id bởi worker; trong bảng bổ sung,
`diagnostic_id` là nhãn nhận diện, còn `run_id` để trống.

Cả hai lượt mới đều bị bộ giám sát dừng khi RSS vượt ngưỡng cấu hình;
không có nghiệm SAT được trả về. Exit code 15 đi cùng việc dừng bởi bộ
giám sát ở hai lượt mới, không phải sự tái xuất hiện của mã crash gốc
`0xc0000409`.

## Bằng chứng xác định giai đoạn sử dụng bộ nhớ

Stack được ghi ở khoảng giây thứ 15 nằm trong `binary.encode_amo()`,
được gọi từ `build_cnf()` tại `src/solvers/sat_solvers.py:57`.

Stack ở khoảng giây thứ 30 nằm trong `CaDiCaL195.new()` của PySAT,
tại vòng lặp gọi `add_clause(clause)` để nạp CNF. Điểm gọi trong project
là `src/solvers/sat_solvers.py:59`:

```python
with Solver(name=solver_name, bootstrap_with=clauses) as solver:
```

Đây là giai đoạn dựng solver và nạp clause. Stack cuối được ghi chưa nằm
trong `solver.solve()`. Vì stack được lấy định kỳ, dữ liệu này không phải
stack chính xác tại thời điểm tiến trình bị dừng.

Binary tại N=1000 có kích thước CNF dự kiến **39.300.904 clause** và
**1.055.888 biến**, theo bảng kích thước mô hình đã được kiểm tra.
Đây là số đếm từ cấu trúc encoding, không phải số clause đã nạp thành công
trong hai lượt bị dừng. Cách triển khai hiện tại giữ danh sách CNF Python
trong lúc CaDiCaL xây dựng cấu trúc dữ liệu riêng, tạo áp lực bộ nhớ đáng kể.

Thông báo `Timeout (0:00:15)!` trong log là thông báo xuất stack định kỳ
của faulthandler, không phải trạng thái TIMEOUT của benchmark.

## Kết luận và cách sử dụng trong báo cáo

Hai lượt mới xác nhận ca này chạm giới hạn RSS 8192 MiB trong môi trường
chạy lại. Crash gốc không tái xuất hiện; chưa xác nhận được nguyên nhân
chính xác của crash đó. Không suy ra rằng bản ghi ERROR gốc thực chất
phải được đổi thành MEMORY_LIMIT.

Benchmark chính giữ nguyên **756 lượt: 612 SAT, 101 TIMEOUT,
42 MEMORY_LIMIT và 1 ERROR**. Hai lượt MEMORY_LIMIT mới được công bố
riêng dưới dạng chẩn đoán bổ sung. Không cộng chúng vào số lần lặp hoặc
các thống kê hiệu năng của benchmark chính.

Đoạn mô tả có thể sử dụng trong báo cáo:

> Một lượt CaDiCaL kết hợp Binary encoding tại N=1000 kết thúc bất thường
> trong benchmark ban đầu. Khi chạy lại riêng ca này với cùng giới hạn
> 100 giây và 8192 MiB, cả lượt chạy lại và lượt chẩn đoán stack bổ sung
> đều bị dừng do vượt giới hạn RSS. Stack định kỳ cuối cùng ghi nhận quá
> trình nạp clause vào CaDiCaL. Kết quả này cho thấy áp lực bộ nhớ là một
> yếu tố cần xem xét, nhưng chưa xác nhận nguyên nhân của crash ban đầu.
> Vì vậy, bản ghi ERROR gốc được giữ nguyên và các kết quả chẩn đoán được
> công bố riêng, không đưa vào thống kê benchmark chính.

## Các file dữ liệu và bằng chứng

- [Bảng chạy lại CSV](../rerun_results.csv)
- [Bản ghi chạy lại JSONL](../rerun_results.jsonl)
- [Tóm tắt thí nghiệm, mục diagnostic_reruns](../summary.json)
- [Chẩn đoán gốc](../../../diagnostics/cadical_binary_n1000_20261015T033339Z/diagnosis.json)
- [Kết quả lượt chạy lại](../../../diagnostics/cadical_binary_n1000_20261015T033339Z/runs/8e6183c0758441a3a37a1b42db67e01d/result.json)
- [Log stack](../../../diagnostics/cadical_binary_n1000_20261015T033339Z/stack_trace/solver.log)
- [Số đo lượt chẩn đoán stack](../../../diagnostics/cadical_binary_n1000_20261015T033339Z/stack_trace/metrics.json)

Các trường `source_result_path`, `source_log_path` trong CSV/JSONL và
`source_diagnosis_path` trong summary được tính tương đối từ thư mục gốc
repository. Các đường dẫn output còn lại trong mục `diagnostic_reruns`
được tính tương đối từ thư mục thí nghiệm.
