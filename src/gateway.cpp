// Optional loopback HTTP adapter. TLS terminates at an operator-owned proxy or
// outbound tunnel. Bearer credentials are never accepted in URLs or forwarded.
#include "symphony/bridge.hpp"
#include <httplib.h>
#include <mutex>
#include <memory>
#include <sys/socket.h>

namespace {
constexpr const char* protocol = "2025-11-25";
std::string private_file(const std::string& path, size_t limit = request_limit) {
  require(fs::path(path).is_absolute(), "Private file path must be absolute");
  int fd = open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
  require(fd >= 0, "Cannot open private file");
  struct Guard { int fd; ~Guard() { close(fd); } } guard{fd};
  struct stat st{};
  require(fstat(fd, &st) == 0 && S_ISREG(st.st_mode) && st.st_uid == geteuid() &&
          (st.st_mode & 0077) == 0, "Private file must be owned and mode 0600 or stricter");
  std::string value; char buf[4096]; ssize_t n;
  while ((n = read(fd, buf, sizeof(buf))) > 0) {
    value.append(buf, static_cast<size_t>(n)); require(value.size() <= limit, "Private file too large");
  }
  require(n == 0, "Private file read failed"); return value;
}
bool equal_secret(const std::string& a, const std::string& b) {
  size_t diff = a.size() ^ b.size();
  for (size_t i = 0; i < b.size(); ++i) diff |= (i < a.size() ? a[i] : 0) ^ b[i];
  return diff == 0;
}
void respond(httplib::Response& r, int status, const std::string& error) {
  r.status = status; r.set_content(json{{"error", error}}.dump(), "application/json");
}
struct Principal {
  std::string name, token_file;
  std::set<std::string> tools, commands;
};
struct Session {
  std::string principal, credential;
  std::unique_ptr<Bridge> core;
  int socket = -1;
  Clock::time_point used = Clock::now();
  std::map<std::string, std::pair<std::string, json>> replies;
  size_t reply_bytes = 0;
  ~Session() { if (socket >= 0) close(socket); }
  std::optional<json> handle(const json& req) {
    if (core) return core->handle(req);
    const auto wire = req.dump() + "\n";
    size_t offset = 0;
    while (offset < wire.size()) {
      auto n = send(socket, wire.data()+offset, wire.size()-offset, 0);
      if (n < 0 && errno == EINTR) continue;
      require(n > 0, "IPC send failed"); offset += static_cast<size_t>(n);
    }
    if (!req.contains("id")) return std::nullopt;
    std::string line;
    const auto deadline = Clock::now()+std::chrono::seconds(70);
    while (Clock::now() < deadline) {
      pollfd p{socket, POLLIN, 0};
      int ready = poll(&p, 1, 1000);
      if (ready < 0 && errno == EINTR) continue;
      require(ready >= 0, "IPC poll failed"); if (!ready) continue;
      char ch; auto n = recv(socket, &ch, 1, 0);
      if (n < 0 && errno == EINTR) continue;
      require(n == 1, "IPC response lost");
      if (ch == '\n') {
        auto result = parse_json(line);
        require(result.value("id", json()) == req["id"], "IPC response ID mismatch"); return result;
      }
      line += ch; require(line.size() <= 32*1024*1024, "IPC response exceeds limit");
    }
    throw std::runtime_error("IPC response deadline exceeded");
  }
};
}

int main(int argc, char** argv) {
  signal(SIGPIPE, SIG_IGN);
  try {
    if (argc == 2 && std::string(argv[1]) == "--version") {
      std::cout << "symphony-mcp-gateway 0.1.0-dev (MCP 2025-11-25)\n"; return 0;
    }
    if (argc == 2 && std::string(argv[1]) == "--help") {
      std::cout << "symphony-mcp-gateway --config ABS_GATEWAY.json\n"
                   "Loopback-only /mcp; expose with an authenticated HTTPS tunnel/proxy.\n"; return 0;
    }
    require(argc == 3 && std::string(argv[1]) == "--config", "Expected --config ABS_GATEWAY.json");
    auto cfg = parse_json(private_file(argv[2]));
    only_keys(cfg, {"schema", "installation_id", "connection_profile", "connect_socket", "port",
                   "allowed_hosts", "allowed_origins", "clients", "audit_file", "session_ttl_seconds", "max_sessions"});
    require(cfg.value("schema", "") == "symphony.agent.gateway.v1", "Unsupported gateway profile");
    auto installation = string_field(cfg, "installation_id");
    require(std::regex_match(installation, std::regex("[A-Za-z0-9_-]{1,64}")), "Invalid installation ID");
    const auto profile = cfg.value("connection_profile", std::string());
    const auto socket_path = cfg.value("connect_socket", std::string());
    require(profile.empty() != socket_path.empty(), "Select exactly one connection profile or IPC socket");
    if (!profile.empty()) { private_file(profile); Bridge validate(profile); }
    else require(fs::path(socket_path).is_absolute(), "IPC path must be absolute");
    const auto hosts = cfg.at("allowed_hosts").get<std::set<std::string>>();
    const auto origins = cfg.at("allowed_origins").get<std::set<std::string>>();
    require(!hosts.empty() && !hosts.contains("*"), "Explicit allowed Hosts required");
    require(!origins.contains("*") && !origins.contains("null"), "Wildcard/null Origin is not allowed");
    int port = cfg.value("port", 8765), ttl = cfg.value("session_ttl_seconds", 600), max_sessions = cfg.value("max_sessions", 8);
    require(port >= 1024 && port <= 65535 && ttl >= 1 && ttl <= 3600 && max_sessions >= 1 && max_sessions <= 32, "Invalid listener limits");
    require(socket_path.empty() || max_sessions == 1, "Existing IPC listener supports one session; set max_sessions=1");
    const std::set<std::string> known_tools = {"symphony_connection", "symphony_discover", "symphony_describe", "symphony_read", "symphony_prepare", "symphony_apply"};
    std::vector<Principal> principals;
    std::set<std::string> names, tokens;
    for (const auto& c : cfg.at("clients")) {
      only_keys(c, {"id", "token_file", "allowed_tools", "allowed_commands"});
      Principal p{string_field(c, "id"), string_field(c, "token_file"), c.at("allowed_tools").get<std::set<std::string>>(), c.at("allowed_commands").get<std::set<std::string>>()};
      require(std::regex_match(p.name, std::regex("[A-Za-z0-9_-]{1,64}")) && names.insert(p.name).second, "Invalid/duplicate client ID");
      for (const auto& tool : p.tools) require(known_tools.contains(tool), "Unknown allowed tool");
      require(!p.tools.contains("symphony_apply") || p.tools.contains("symphony_prepare"), "Apply requires prepare");
      auto token = private_file(p.token_file, 256);
      require(std::regex_match(token, std::regex("[A-Za-z0-9_-]{43,128}")) && tokens.insert(token).second, "Use unique random tokens, without newline");
      principals.push_back(std::move(p));
    }
    require(!principals.empty() && principals.size() <= 32, "Configure 1 to 32 clients");
    const auto audit_path = string_field(cfg, "audit_file");
    require(fs::path(audit_path).is_absolute(), "Audit path must be absolute");
    int audit = open(audit_path.c_str(), O_WRONLY | O_APPEND | O_CREAT | O_NOFOLLOW | O_CLOEXEC, 0600);
    require(audit >= 0, "Cannot open audit file");
    struct AuditGuard { int fd; ~AuditGuard() { close(fd); } } audit_guard{audit};
    struct stat ast{};
    require(fstat(audit, &ast) == 0 && S_ISREG(ast.st_mode) && ast.st_uid == geteuid() && (ast.st_mode & 0077) == 0, "Unsafe audit file");
    auto record = [&](const json& entry) {
      auto line = entry.dump()+"\n"; size_t offset = 0;
      while (offset < line.size()) { auto n = write(audit, line.data()+offset, line.size()-offset); if (n < 0 && errno == EINTR) continue; require(n > 0, "Audit write failed"); offset += static_cast<size_t>(n); }
      require(fsync(audit) == 0, "Audit sync failed");
    };
    std::mutex mutex;
    std::map<std::string, std::unique_ptr<Session>> sessions;
    httplib::Server server;
    server.new_task_queue = [] { return new httplib::ThreadPool(2, 16); };
    server.set_payload_max_length(request_limit);
    server.set_read_timeout(10, 0); server.set_write_timeout(75, 0); server.set_keep_alive_max_count(10);
    server.set_default_headers({{"Cache-Control", "no-store"}, {"X-Content-Type-Options", "nosniff"}});
    server.set_pre_routing_handler([&](const httplib::Request& req, httplib::Response& res) {
      if (req.get_header_value_count("Host") != 1 || !hosts.contains(req.get_header_value("Host"))) { respond(res, 403, "Host rejected"); return httplib::Server::HandlerResponse::Handled; }
      if (req.get_header_value_count("Origin") > 1 || (req.has_header("Origin") && !origins.contains(req.get_header_value("Origin")))) { respond(res, 403, "Origin rejected"); return httplib::Server::HandlerResponse::Handled; }
      return httplib::Server::HandlerResponse::Unhandled;
    });
    auto route = [&](const httplib::Request& req, httplib::Response& res) {
      std::lock_guard lock(mutex); // serialization also protects single-use previews
      try {
        if (!req.params.empty() || req.get_header_value_count("Authorization") != 1) { respond(res, 401, "Bearer authentication required; URL credentials forbidden"); return; }
        const Principal* principal = nullptr; std::string credential; size_t matches = 0;
        const auto auth = req.get_header_value("Authorization");
        for (const auto& p : principals) {
          try {
            auto token = private_file(p.token_file, 256);
            if (std::regex_match(token, std::regex("[A-Za-z0-9_-]{43,128}")) && equal_secret(auth, "Bearer "+token)) { principal = &p; credential = token; ++matches; }
          } catch (...) {} // removed/unreadable credential is revoked
        }
        if (!principal || matches != 1) { res.set_header("WWW-Authenticate", "Bearer"); respond(res, 401, "Credential rejected"); return; }
        if (req.path != "/mcp") { respond(res, 404, "Not found"); return; }
        for (auto it = sessions.begin(); it != sessions.end();) {
          if (Clock::now()-it->second->used > std::chrono::seconds(ttl)) it = sessions.erase(it); else ++it;
        }
        if (req.get_header_value_count("Mcp-Session-Id") > 1 || req.get_header_value_count("MCP-Protocol-Version") > 1) { respond(res, 400, "Duplicate protocol header"); return; }
        auto sid = req.get_header_value("Mcp-Session-Id");
        auto found = sessions.find(sid);
        if (!sid.empty() && (found == sessions.end() || found->second->principal != principal->name || found->second->credential != credential)) { respond(res, 404, "Session unavailable; initialize a new session, do not replay writes"); return; }
        if (req.has_header("MCP-Protocol-Version") && req.get_header_value("MCP-Protocol-Version") != protocol) { respond(res, 400, "Unsupported protocol version"); return; }
        if (req.method == "GET") { res.set_header("Allow", "POST, DELETE"); respond(res, 405, "No unsolicited SSE stream"); return; }
        if (req.method == "DELETE") {
          if (sid.empty()) { respond(res, 400, "Session ID required"); return; }
          sessions.erase(sid); res.status = 204; return;
        }
        const auto content_type = req.get_header_value("Content-Type");
        if (content_type != "application/json" && content_type != "application/json; charset=utf-8") { respond(res, 415, "Expected application/json"); return; }
        const auto accept = req.get_header_value("Accept");
        if (accept.find("application/json") == std::string::npos || accept.find("text/event-stream") == std::string::npos) { respond(res, 406, "Accept application/json and text/event-stream"); return; }
        json rpc;
        try { rpc = parse_json(req.body); } catch (...) { respond(res, 400, "Invalid JSON"); return; }
        if (!rpc.is_object() || rpc.value("jsonrpc", "") != "2.0" || !rpc.contains("method") || !rpc["method"].is_string()) { respond(res, 400, "Expected one JSON-RPC message"); return; }
        const auto method = rpc["method"].get<std::string>();
        const bool init = method == "initialize";
        if (init) {
          if (!sid.empty() || !rpc.contains("id")) { respond(res, 400, "Initialize once without a session ID"); return; }
          if (sessions.size() >= static_cast<size_t>(max_sessions)) { respond(res, 429, "Session capacity reached"); return; }
          auto state = std::make_unique<Session>(); state->principal = principal->name; state->credential = credential;
          if (!profile.empty()) state->core = std::make_unique<Bridge>(profile);
          else {
            state->socket = symphony::connect_local_socket(socket_path);
            timeval timeout{5, 0}; setsockopt(state->socket, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
          }
          sid = symphony::random_token(); sessions.emplace(sid, std::move(state)); found = sessions.find(sid);
        } else if (sid.empty()) { respond(res, 400, "Session ID required"); return; }
        auto& session = *found->second; session.used = Clock::now();
        auto params = rpc.value("params", json::object());
        if (!params.is_object()) { respond(res, 400, "Invalid params"); return; }
        if (method == "resources/read" && params.value("uri", "") == "symphony://connection" && !principal->tools.contains("symphony_connection")) { respond(res, 403, "Connection resource outside scope"); return; }
        // Notifications cannot dispatch commands, consume previews or spoof calls.
        if (!rpc.contains("id") && method != "notifications/initialized" && method != "notifications/cancelled") { respond(res, 400, "Unsupported notification"); return; }
        std::string tool;
        if (method == "tools/call") {
          tool = params.value("name", std::string());
          if (!principal->tools.contains(tool)) { respond(res, 403, "Tool outside connection scope"); return; }
          if (tool == "symphony_read" || tool == "symphony_prepare" || tool == "symphony_describe") {
            auto args = params.value("arguments", json::object());
            const auto command = args.value("command_id", std::string());
            if (!principal->commands.contains("*") && !principal->commands.contains(command)) { respond(res, 403, "Command outside connection scope"); return; }
          }
        }
        const auto key = rpc.contains("id") ? rpc["id"].dump() : std::string();
        const auto body = rpc.dump();
        if (!key.empty()) {
          auto previous = session.replies.find(key);
          if (previous != session.replies.end()) {
            if (previous->second.first != body) { respond(res, 409, "Request ID reused with different content"); return; }
            res.set_content(previous->second.second.dump(), "application/json"); res.set_header("Mcp-Session-Id", sid); return;
          }
          if (session.replies.size() >= 256 || session.reply_bytes >= 16*1024*1024) { respond(res, 429, "Session reply budget reached; reconcile pending writes before reconnecting"); return; }
        }
        const auto operation = symphony::random_token();
        record({{"event", "dispatch"}, {"operation_id", operation}, {"installation", installation}, {"client", principal->name}, {"method", method}, {"tool", tool}});
        std::optional<json> reply;
        try { reply = session.handle(rpc); }
        catch (...) {
          sessions.erase(sid);
          record({{"event", "unknown_requires_owner_reconciliation"}, {"operation_id", operation}, {"retry_automatically", false}});
          respond(res, 502, "Local response lost; outcome unknown. Reconcile with owner; do not replay writes"); return;
        }
        if (reply && method == "tools/list" && reply->contains("result")) {
          auto& tools = (*reply)["result"]["tools"];
          tools.erase(std::remove_if(tools.begin(), tools.end(), [&](const json& t) { return !principal->tools.contains(t.at("name").get<std::string>()); }), tools.end());
        }
        // Keep discovery useful without advertising commands outside this grant.
        if (reply && tool == "symphony_discover" && !principal->commands.contains("*") && (*reply).contains("result")) {
          auto& result = (*reply)["result"];
          if (result.contains("structuredContent")) {
            auto& data = result["structuredContent"];
            auto& commands = data["commands"];
            commands.erase(std::remove_if(commands.begin(), commands.end(), [&](const json& c) { return !principal->commands.contains(c.at("command_id").get<std::string>()); }), commands.end());
            data["scope_filtered"] = true;
            result["content"] = json::array({{{"type", "text"}, {"text", data.dump()}}});
          }
        }
        if (reply && !key.empty()) { session.reply_bytes += body.size()+reply->dump().size(); session.replies.emplace(key, std::make_pair(body, *reply)); }
        record({{"event", "response_ready"}, {"operation_id", operation}, {"semantic_success", "not_asserted"}});
        res.set_header("Mcp-Session-Id", sid); res.set_header("MCP-Protocol-Version", protocol);
        if (reply) res.set_content(reply->dump(-1, ' ', false, json::error_handler_t::replace), "application/json"); else res.status = 202;
        if (init && (!reply || reply->contains("error"))) { sessions.erase(sid); res.headers.erase("Mcp-Session-Id"); }
      } catch (...) { respond(res, 500, "Gateway rejected request; never automatically retry a possible write"); }
    };
    server.Post("/mcp", route); server.Get("/mcp", route); server.Delete("/mcp", route);
    std::cerr << "Symphony gateway listening on loopback port " << port << " for installation " << installation << "\n";
    require(server.listen("127.0.0.1", port), "Cannot bind loopback listener");
  } catch (const std::exception& e) { std::cerr << "symphony-mcp-gateway: " << e.what() << "\n"; return 2; }
}
