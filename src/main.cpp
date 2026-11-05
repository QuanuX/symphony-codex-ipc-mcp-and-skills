#include "symphony/bridge.hpp"
static volatile sig_atomic_t stopping=0;
static void on_signal(int) { stopping=1; }
static bool write_all(int fd,const std::string& data) {
  const int original=fcntl(fd,F_GETFL,0);if(original<0||fcntl(fd,F_SETFL,original|O_NONBLOCK)<0)return false;
  struct Restore { int fd,flags; ~Restore(){fcntl(fd,F_SETFL,flags);} } restore{fd,original};
  const auto deadline=Clock::now()+std::chrono::seconds(30);size_t offset=0;
  while(offset<data.size()&&!stopping) {
    const auto remaining=std::chrono::duration_cast<std::chrono::milliseconds>(deadline-Clock::now()).count();if(remaining<=0)return false;
    pollfd p{fd,POLLOUT,0};int n=poll(&p,1,static_cast<int>(remaining));if(n<0&&errno==EINTR)continue;if(n<=0)return false;
    auto wrote=write(fd,data.data()+offset,std::min<size_t>(data.size()-offset,16384));
    if(wrote<0&&(errno==EINTR||errno==EAGAIN||errno==EWOULDBLOCK))continue;if(wrote<=0)return false;offset+=static_cast<size_t>(wrote);
  }
  return offset==data.size();
}
static void session(Bridge& bridge,int input,int output,bool idle_timeout) {
  std::string line;std::array<char,8192> buffer{};
  while(!stopping) {
    pollfd p{input,POLLIN,0};auto n=poll(&p,1,idle_timeout?60000:1000);if(n<0&&errno==EINTR)continue;if(n<0||(!n&&idle_timeout))return;if(!n)continue;
    auto count=read(input,buffer.data(),buffer.size());if(count<0&&errno==EINTR)continue;if(count<=0)return;
    for(ssize_t i=0;i<count;++i) {
      if(buffer[i]=='\n') {
        if(line.empty())continue;
        std::optional<json> response;
        try {response=bridge.handle(parse_json(line));}catch(...) {response=json{{"jsonrpc","2.0"},{"id",nullptr},{"error",{{"code",-32700},{"message","Parse error"}}}};}
        line.clear();if(response&&!write_all(output,response->dump(-1,' ',false,json::error_handler_t::replace)+"\n"))return;
      }else {line.push_back(buffer[i]);if(line.size()>request_limit)return;}
    }
  }
}
static void relay(int fd) {
  std::array<char,16384> buffer{};
  while(!stopping) {
    pollfd p[2]={{STDIN_FILENO,POLLIN,0},{fd,POLLIN,0}};auto n=poll(p,2,1000);if(n<0&&errno==EINTR)continue;if(n<0)return;
    for(int i=0;i<2;++i)if(p[i].revents&(POLLIN|POLLHUP|POLLERR)) {auto count=read(p[i].fd,buffer.data(),buffer.size());if(count<=0)return;if(!write_all(i==0?fd:STDOUT_FILENO,std::string(buffer.data(),static_cast<size_t>(count))))return;}
  }
}
int main(int argc,char** argv) {
  signal(SIGPIPE,SIG_IGN);signal(SIGINT,on_signal);signal(SIGTERM,on_signal);
  std::string config,listen_path,connect_path;
  if(const char* p=getenv("SYMPHONY_MCP_CONFIG"))config=p;
  try {
    for(int i=1;i<argc;++i) {
      const std::string arg=argv[i];
      if(arg=="--version") {std::cout<<"symphony-mcp 0.1.0-alpha.1\n";return 0;}
      if(arg=="--help") {std::cout<<"symphony-mcp --config ABS_CONNECTION.json [--listen ABS_SOCKET]\nsymphony-mcp --connect-socket ABS_SOCKET\nDefault transport: MCP stdio. SYMPHONY_MCP_CONFIG supplies the default profile.\n";return 0;}
      require(i+1<argc,"Missing option value");auto value=std::string(argv[++i]);
      if(arg=="--config")config=value;else if(arg=="--listen")listen_path=value;else if(arg=="--connect-socket")connect_path=value;else throw std::runtime_error("Unknown option");
    }
    require(listen_path.empty()||connect_path.empty(),"Select listener or connector, not both");
    if(!connect_path.empty()) {int fd=symphony::connect_local_socket(connect_path);relay(fd);close(fd);return 0;}
    require(!config.empty()&&fs::path(config).is_absolute(),"Set --config to an absolute protected connection profile");
    if(listen_path.empty()) {Bridge bridge(config);session(bridge,STDIN_FILENO,STDOUT_FILENO,false);}
    else {
      {Bridge validation(config);} // validate before listening
      int fd=symphony::listen_local_socket(listen_path);
      try {
        while(!stopping) {pollfd p{fd,POLLIN,0};auto n=poll(&p,1,1000);if(n<0&&errno==EINTR)continue;if(n<0)break;if(!n)continue;
          int client=-1;try {client=symphony::accept_local_socket(fd);Bridge bridge(config);session(bridge,client,client,true);}catch(...){std::cerr<<"Local session rejected\n";}if(client>=0)close(client);
        }
      }catch(...) {close(fd);symphony::remove_local_socket(listen_path);throw;}
      close(fd);symphony::remove_local_socket(listen_path);
    }
    return 0;
  }catch(const std::exception& e) {std::cerr<<"symphony-mcp: "<<e.what()<<"\n";return 2;}
}
