# Migrate

This program is used to migrate the collections and history to another server.

# Quick Start

1. Create the config file

`config.json`

```json
{
  "fromEmail": "myemail@example.com",
  "fromPassword": "password",
  "fromEndpoint": {
    "authScheme": "Token",
    "token": "http://old.example.com/token",
    "collection": "http://old.example.com/collections",
    "history": "http://old.example.com/histories"
  },
  "toEmail": "myemail@example.com",
  "toPassword": "password",
  "toEndpoint": {
    "authScheme": "Bearer",
    "token": "http://new.example.com/token",
    "collection": "http://new.example.com/collections",
    "history": "http://new.example.com/history"
  }
}
```

2. Start the program

```bash
python3 migrate.py
```

Make sure that `requests` is installed.
