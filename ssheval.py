# Copyright (c) 2025 Jifeng Wu
# Licensed under the MIT License. See LICENSE file in the project root for full license information.
from __future__ import print_function

import argparse
import os
import sys
import threading
from typing import Union

import paramiko

try:
    import readline  # noqa: F401
except ImportError:
    readline = None

if sys.version_info < (3,):
    sys_stdin_buffer = sys.stdin
    sys_stdout_buffer = sys.stdout
    sys_stderr_buffer = sys.stderr
else:
    sys_stdin_buffer = sys.stdin.buffer
    sys_stdout_buffer = sys.stdout.buffer
    sys_stderr_buffer = sys.stderr.buffer

AuthValue = Union[str, paramiko.PKey]


READ_CHUNK_SIZE = 32768


def read_stdin_chunk(size):
    # Return as soon as some data is available instead of blocking until `size`
    # bytes have been read, so piped stdin keeps streaming in real time.
    read1 = getattr(sys_stdin_buffer, 'read1', None)
    if read1 is not None:
        return read1(size)
    try:
        return os.read(sys_stdin_buffer.fileno(), size)
    except Exception:
        return sys_stdin_buffer.read(size)


def stream_pipe(read, dst, write_lock, close_dst=False):
    try:
        while True:
            data = read(READ_CHUNK_SIZE)
            if not data:
                break
            # Serialize writes so chunks from stdout and stderr are not
            # interleaved byte-by-byte when they share the same terminal.
            write_lock.acquire()
            try:
                dst.write(data)
                dst.flush()
            finally:
                write_lock.release()
    except Exception:
        pass  # Optionally log thread errors
    finally:
        if close_dst:
            try:
                dst.close()
            except Exception:
                pass


if sys.version_info < (2, 6):
    def set_daemon(thread):
        thread.setDaemon()
else:
    def set_daemon(thread):
        thread.daemon = True


def prompt_for_command():
    if sys.version_info < (3,):
        return raw_input('ssheval> ')
    return input('ssheval> ')


def stream_command_output(client, command, pipe_stdin):
    stdin, stdout, stderr = client.exec_command(command, get_pty=False)

    threads = []
    write_lock = threading.Lock()

    # Stream stdout and stderr in real time. Read from the channels directly:
    # unlike ChannelFile.read(n), recv()/recv_stderr() return as soon as any
    # data is available instead of waiting for a full chunk.
    threads.append(threading.Thread(
        target=stream_pipe, args=(stdout.channel.recv, sys_stdout_buffer, write_lock)))
    threads.append(threading.Thread(
        target=stream_pipe, args=(stderr.channel.recv_stderr, sys_stderr_buffer, write_lock)))

    if pipe_stdin:
        threads.append(threading.Thread(
            target=stream_pipe, args=(read_stdin_chunk, stdin, write_lock, True)))
    else:
        stdin.close()

    for thread in threads:
        set_daemon(thread)
        thread.start()

    exit_status = stdout.channel.recv_exit_status()

    for thread in threads:
        thread.join()

    return exit_status


def main():
    parser = argparse.ArgumentParser(description="Run a remote SSH command and output raw bytes to stdout/stderr.")
    parser.add_argument('--host', required=True, help='Remote host to connect to')
    parser.add_argument('--username', required=True, help='Username for SSH')
    auth = parser.add_mutually_exclusive_group(required=True)
    auth.add_argument('--password', help='Password for SSH')
    auth.add_argument('--ed25519-key', help='Path to Ed25519 private key for SSH')
    auth.add_argument('--rsa-key', help='Path to RSA private key for SSH')
    parser.add_argument('--port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('--command', help='Command to execute on remote host')
    args = parser.parse_args()

    if args.password is not None:
        auth_kind = "password"
        auth_value = args.password  # type: AuthValue
    elif args.rsa_key is not None:
        auth_kind = "rsa"
        auth_value = paramiko.RSAKey.from_private_key_file(args.rsa_key)
    elif args.ed25519_key is not None:
        auth_kind = "ed25519"
        auth_value = paramiko.Ed25519Key.from_private_key_file(args.ed25519_key)
    else:
        raise ValueError("exactly one auth method is required")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if auth_kind == "password":
            client.connect(args.host, port=args.port, username=args.username, password=auth_value)
        else:
            client.connect(args.host, port=args.port, username=args.username, pkey=auth_value)

        if args.command is None:
            while True:
                try:
                    command = prompt_for_command()
                except EOFError:
                    print()
                    return 0

                stream_command_output(client, command, False)

        exit_status = stream_command_output(client, args.command, not sys.stdin.isatty())
        return exit_status
    except Exception as e:
        print(e, file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
