# `ssheval`

A cross-platform pure Python script for executing remote commands over SSH and streaming raw stdout/stderr.

## 🚀 Features

- **Works on NT & POSIX:** Requires only Python 2+ and [`paramiko`](https://www.paramiko.org/) - no OpenSSH or PuTTY needed.
- **Flexible authentication:** Supports password, Ed25519 key, or RSA key via command-line arguments.
- **Faithfully streams stdout & stderr:** Outputs both streams in real time, preserving all bytes (works for text and binary data!).
- **Remote exit codes:** Exits with the same code as the remote command.
- **SSH-like stdin behavior:**  
  - Pipes stdin from your console or parent process **only if** input is provided (matches `ssh` behavior).
  - If nothing is piped, remote stdin is closed immediately.

## ⚡️ Why use this instead of plain ssh?

- **No SSH client required on Windows:** Works even where ssh is missing (ex: vanilla Windows).
- **Great for automation:** Integrates seamlessly with scripts and tools that need to provide credentials non-interactively.
- **Binary-safe:** Most SSH client wrappers mishandle binary data or don't stream both stdout and stderr in real time.
- **Stdin-pipes like ssh:** Remote command's stdin is hooked up only when data is piped in - just like the real `ssh`.

## 🛠️ Installation

```sh
pip install ssheval
```

After installation, run it as `ssheval`.

[paramiko](https://pypi.org/project/paramiko/) required.


## 💻 Usage

Basic example:

```sh
ssheval \
  --host example.com \
  --username youruser \
  --password 'yourpassword' \
  --command 'ls -lh /tmp'
```

With an Ed25519 or RSA key:
```sh
ssheval \
  --host example.com \
  --username youruser \
  --ed25519-key ~/.ssh/id_ed25519 \
  --command 'ls -lh /tmp'

ssheval \
  --host example.com \
  --username youruser \
  --rsa-key ~/.ssh/id_rsa \
  --command 'ls -lh /tmp'
```

Pipe something into the remote process:
```sh
echo "Hello remote world!" | ssheval --host foo --username bar --password baz --command 'cat -'
```

Download a remote file (binary-safe):
```sh
ssheval --host foo --username bar --password baz --command 'cat /usr/bin/ls' > local_ls_copy
```

### Arguments

| Argument        | Description                                          |
|-----------------|------------------------------------------------------|
| `--host`        | Hostname or IP of the remote server                  |
| `--username`    | SSH username                                         |
| `--password`    | SSH password                                         |
| `--ed25519-key` | Path to an Ed25519 private key for SSH authentication |
| `--rsa-key`     | Path to an RSA private key for SSH authentication    |
| `--port`        | SSH port (default: 22)                               |
| `--command`     | The remote command to execute                        |


## 🔄 Stdin Handling

This script **matches SSH's behavior**:

- **If you pipe input in**, local stdin is streamed to the remote command.
- **If not**, remote stdin is immediately closed - remote commands like `cat` will finish (not hang).

**Examples:**

```sh
ssheval ... --command 'cat -'         # stdin closed immediately
echo foo | ssheval ... --command 'cat -'   # 'foo' is sent
```

## ⚠️ Limitations

- No PTY/interactive shell allocation.
- Basic error handling and no advanced SSH features (X11, port forwarding).

## 🛠️ Contributing

Contributions are welcome! Please submit pull requests or open issues on the GitHub repository.

## 📄 License

This project is licensed under the [MIT License](LICENSE).