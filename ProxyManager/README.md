# Proxy Manager

This program is used to check if a proxy is online and if it is still usable.

# Quick Start

1. Create the config file

`config.json`

```json
{
  // Required, links to test if the proxy is working
  "testLinks": ["http://example.com"],
  // Required, proxies information
  "proxies": [
    {
      // Required, the proxy address
      "address": "socks5://proxy.example.com:1080",
      // Optional, the command to restart the proxy
      "restartCMD": "docker restart example_proxy"
    }
  ],
  // Optional, set log level to debug
  "debug": true,
  // Optional, set the maximum timeout for the second select
  "secondaryTimeout": 1.5,
  // Optional, set the maximum timeout for the remaining select
  "primaryTimeout": 10
}
```

2. Start the program

```bash
sudo docker-compose up -d
```
