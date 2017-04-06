# Traffic-Replay

Replay client to replay session logs.

Usage: 
python3.5 trafficreplay_v2/ -type <ssl|h2|random> -log_dir /path/to/log -v

Session Log format (in JSON): 

 {"version": "0.1", 
  "txns": [
        {"request": {"headers": "POST ……\r\n\r\n", "timestamp": "..", "body": ".."}, 
        "response": {"headers": "HTTP/1.1..\r\n\r\n", "timestamp": "..", "body": ".."},
         "uuid": "1"}, 
        {"request": {"headers": "POST ..….\r\n\r\n", "timestamp": "..", "body": ".."}, 
        "response": {"headers": "HTTP/1.1..\r\nr\n", "timestamp": "..", "body": ".."}, 
        "uuid": "2"}
  ], 
  "timestamp": "....", 
  "encoding": "...."}
