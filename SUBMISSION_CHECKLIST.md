# Day26 MCP Tools Integration — Submission Checklist

Trạng thái được đối chiếu với code trong repo và các lệnh test đã chạy. Các file
`.env` thật không nằm trong Git; chỉ các file `.env.example` được commit.

## Bài Dễ

| Yêu cầu | Trạng thái | Minh chứng |
| --- | --- | --- |
| MCP Server khởi động được | PASS | [`my-mcp-server/server.py`](my-mcp-server/server.py#L286-L296); [`legacy_client.py`](my-mcp-server/legacy_client.py) tự spawn server qua stdio. |
| Có ít nhất 1–2 tools | PASS | `search_workspace`, `search_workspace_v2`, `read_workspace_file` tại [`server.py`](my-mcp-server/server.py#L162-L229). |
| Tool giải quyết việc thực tế | PASS | Use case tra cứu tài liệu/mã nguồn trong [`my-mcp-server/README.md`](my-mcp-server/README.md#L1-L15). |
| Tool không trả hard-code vô nghĩa | PASS | Server quét file thật bằng `rglob`, đọc nội dung thật và giới hạn workspace tại [`server.py`](my-mcp-server/server.py#L108-L160). |
| Claude Code nhận ra server | PASS | `claude mcp get workspace-search` đã báo `Status: Connected`; cấu hình chạy được mô tả tại [`README.md`](my-mcp-server/README.md#L38). |
| Claude Code nhìn thấy tools | PARTIAL | MCP client test đã list đủ tools tại [`legacy_client.py`](my-mcp-server/legacy_client.py#L15-L30). Claude Code CLI chưa đăng nhập nên chưa có phiên UI để chụp bằng chứng trực tiếp. |
| Claude Code tự gọi tool bằng câu tự nhiên | NOT VERIFIED | Cần chạy sau `/login`; hướng dẫn prompt nằm tại [`README.md`](my-mcp-server/README.md#L45-L50). |
| Tool nhận đúng arguments | PASS | Client truyền `keyword`, `limit`, `relative_path`, `start_line`, `max_lines`; xem [`legacy_client.py`](my-mcp-server/legacy_client.py#L20-L29). |
| Tool trả dữ liệu đúng | PASS | `legacy_client.py` và `versioned_client.py` đã trả đường dẫn, số dòng, nội dung thật và JSON match. |

### Lệnh kiểm tra Bài Dễ

```powershell
$root = "D:\Downloads_D\P-088\Day26-MCP-Tools-Integration-Namngo-uxiuer"
& "$root\.venv\Scripts\python.exe" "$root\my-mcp-server\legacy_client.py"
& "$root\.venv\Scripts\python.exe" "$root\my-mcp-server\versioned_client.py"
```

Sau khi đăng nhập Claude Code, chạy:

```powershell
cd $root
& "C:\Users\Acer\AppData\Roaming\npm\claude.cmd"
```

Rồi hỏi bằng ngôn ngữ tự nhiên:

```text
Tìm trong repository các file nói về authentication của MCP, sau đó đọc phần hướng dẫn chạy auth server.
```

## Bài Trung bình

| Yêu cầu | Trạng thái | Minh chứng |
| --- | --- | --- |
| Server chạy Streamable HTTP | PASS | [`server.py`](my-mcp-server/server.py#L286-L296). |
| Client kết nối qua HTTP | PASS | [`http_client.py`](my-mcp-server/http_client.py#L42-L55); đã chạy thành công. |
| Authentication được bật | PASS | `EnvironmentTokenVerifier` và `AuthSettings` tại [`server.py`](my-mcp-server/server.py#L52-L80). |
| Token hợp lệ gọi được tool | PASS | [`http_client.py`](my-mcp-server/http_client.py#L57-L67); kết quả test: `valid token: MCP call succeeded`. |
| Thiếu token bị từ chối | PASS | Kết quả test: `missing token: HTTP 401`. |
| Token sai bị từ chối | PASS | Kết quả test: `invalid token: HTTP 401`. |
| Truy cập từ LAN | OPTIONAL / NOT RUN | README có hướng dẫn bind `0.0.0.0`, mở firewall và dùng IP LAN tại [`README.md`](my-mcp-server/README.md#L82). Không bắt buộc nếu không có máy thứ hai. |

### Lệnh kiểm tra Auth

Terminal 1:

```powershell
$env:MCP_TRANSPORT = "streamable-http"
$env:MCP_AUTH_TOKEN = "day26-local-test-token"
$env:MCP_HOST = "127.0.0.1"
$env:MCP_PORT = "8765"
python .\my-mcp-server\server.py
```

Terminal 2:

```powershell
$env:MCP_AUTH_TOKEN = "day26-local-test-token"
$env:MCP_SERVER_URL = "http://127.0.0.1:8765/mcp"
python .\my-mcp-server\http_client.py
```

## Bài Khó

| Yêu cầu | Trạng thái | Minh chứng |
| --- | --- | --- |
| Có thay đổi thật về response/tool | PASS | v1 trả text, v2 trả JSON có `api_version`, `matches`, `extensions`; [`server.py`](my-mcp-server/server.py#L162-L216). |
| Client cũ vẫn hoạt động | PASS | [`legacy_client.py`](my-mcp-server/legacy_client.py#L15-L30); đã chạy thành công. |
| Client mới dùng capability mới | PASS | [`versioned_client.py`](my-mcp-server/versioned_client.py#L20-L39); tự chọn `search_workspace_v2`. |
| Có `server://info` | PASS | [`server.py`](my-mcp-server/server.py#L260-L284). |
| Metadata có version/deprecation/migration | PASS | `server_info()` công bố version `2.0.0`, tool versions và replacement tool. |
| Client đọc metadata trước khi gọi tool | PASS | [`versioned_client.py`](my-mcp-server/versioned_client.py#L20-L29). |

## Lab 04 Weather Agent

Phần weather đã đổi sang Open-Meteo live, không cần WeatherAPI key:

- Server: [`weather.py`](04-lab/mcp-server/weather.py#L10-L74).
- Client smoke test: [`test_local_mcp.py`](04-lab/mcp-client/test_local_mcp.py).
- Đã test live: `get_current_weather("Hanoi")` trả dữ liệu từ Open-Meteo.
- ADK setup verification đã pass tại [`verify_setup.py`](04-lab/mcp-client/verify_setup.py).

Phần ADK chat vẫn cần `GOOGLE_API_KEY` hợp lệ. Key hiện tại trước đó trả lỗi
`403 API_KEY_IP_ADDRESS_BLOCKED`, nên cần bỏ giới hạn IP hoặc thêm IP máy trước
khi kiểm thử model thật.

## Có cần ảnh minh chứng không?

Đề bài yêu cầu **bằng chứng hoặc hướng dẫn kiểm tra**, không ghi bắt buộc ảnh.
README và các client test tái lập được là đủ về mặt repository. Nếu hệ thống
nộp bài cho phép đính kèm ảnh, nên chụp 3 ảnh tùy chọn:

1. `claude mcp get workspace-search` có `Status: Connected`.
2. Terminal chạy `legacy_client.py`/`versioned_client.py`.
3. Terminal chạy `http_client.py` có `401`, `401` và `valid token: MCP call succeeded`.

Ảnh Claude tự gọi tool chỉ chụp được sau khi chạy `/login` và gửi prompt tự nhiên.

## Link nộp bài

```text
https://github.com/Namngo-uxiuer/Day26-MCP-Tools-Integration
```

Không upload `.env`, API key, token hoặc secret thật.
