# SPDX-FileCopyrightText: Copyright (c) 2023-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""
Examples of using resource.popen, which exposes the pod exec call using a subprocess.Popen
like object, with support for both binary and text data.


kr8s.objects.APIObject.popen method:

  command    - The remote command to executem, not executed within a shell.
  container  - Optional container to execute the command in.
  tty        - Enable tty mode for the exec call.
  buffer     - Enable buffering stdout and stderr
  text       - Enable text mode, stdin, stdout, and stderr will be strings, rather than bytes.
  encoding   - Text encoding format if text mode.
  errors     - Text encoding error strictness if text mode.
  stdin      - Redirect the standard input stream of the pod for this call.
  stdout     - Redirect the standard output stream of the pod for this call.
  stderr     - Redirect the standard error stream of the pod for this call.
  stderr2out - Redirect the standard error stream of the pod to stdout for this call.
  timeout    - Timeout in seconds.

kr8s._exec.AsyncPopen fields:

  resource   - APIObject popen called on
  pod        - Pod used to run exec on
  container  - Pod container use to run exec on
  command    - Exec command run
  tty        - tty enabled
  buffer     - buffering stdout and stdin enabled
  text       - if text mode enabled for stdin, stdout, and stderr
  encodning  - text mode encoding
  errors     - text mode errors strictness
  stdin      - if enabled, an io.RawIOBase
  stdout     - if enabled, an io.RawIOBase
  stderr     - if enabled, an io.RawIOBase
  result     - full result object returned by kubernetes
  returncode - exec process return code when complete
  closed     - flag if the exec connecition is closed
  timeout    - timeout setting

kubernetes.stream.Popen Methods

  resize      - resize the tty width and height
  communicate - same as subprocess.Popen.communicate
  wait        - same as subprocess.Popen.wait
  close       - close the kubernetes connection

"""

import os
import select
import sys
import tarfile
import termios
import time
import tty

import kr8s


##############################################################################
# Provision the test pod
def provision_pod(api):
    pod = kr8s.objects.Pod("busybox-example", "default", api)
    if pod.exists():
        pod.refresh()
    else:
        print(f"Pod {pod.name} does not exist. Creating it...")
        pod.spec = {
            "containers": [
                {
                    "image": "busybox",
                    "name": "sleep",
                    "tty": True,
                    "args": [
                        "/bin/cat",
                    ],
                }
            ]
        }
        pod.create()
        while not pod.ready():
            time.sleep(1)
            print("Done.")
    return pod


##################################################################
# Calling exec and waiting for response
def simple_response(pod):
    command = [
        "/bin/sh",
        "-c",
        "echo This message goes to stdout;echo This message goes to stderr >&2",
    ]

    ex = pod.exec(command)
    print(f"STDOUT: {ex.stdout.decode()}", end="", flush=True)
    print(f"STDERR: {ex.stderr.decode()}", end="", flush=True)

    with pod.popen(*command, text=True, stdout=True, stderr=True) as popen:
        stdout, stderr = popen.communicate()
        print(f"STDOUT: {stdout}", end="", flush=True)
        print(f"STDERR: {stderr}", end="", flush=True)


##################################################################
# stdin handling
def stdin_sent(pod):
    with pod.popen(
        "sh",
        "-c",
        'printf ">>>";cat;printf "<<<"',
        text=True,
        stdin=True,
        stdout=True,
        stderr=True,
    ) as popen:
        stdout, stderr = popen.communicate("test")
        print(f"STDOUT: {stdout}", flush=True)
    if stderr:
        print(f"STDERR: {stderr}", flush=True)


##################################################################
# Calling a process interactively
def interactive(pod):
    with pod.popen("/bin/sh", text=True, stdin=True, stdout=True, stderr=True) as popen:
        commands = [
            "echo This message goes to stdout",
            "echo This message goes to stderr >&2",
        ]
        # Do non-blocking stdout and stderr reads.
        popen.timeout = 0
        while commands and not popen.closed:
            line = commands.pop(0)
            print("Running command... %s" % line, flush=True)
            popen.stdin.write(line + "\n")
            time.sleep(1)
            try:
                line = popen.stdout.readline()
                print("STDOUT: %s" % line, end="", flush=True)
            except TimeoutError:
                pass
            try:
                line = popen.stderr.readline()
                print("STERR: %s" % line, end="", flush=True)
            except TimeoutError:
                pass
            popen.timeout = 3
            popen.stdin.write("date\n")
            line = popen.stdout.readline()
            print("Server date command returns: %s" % line, end="", flush=True)
            popen.timeout = 3
            popen.stdin.write("whoami\n")
            line = popen.stdout.readline()
            print("Server user is: %s" % line, end="", flush=True)


##################################################################
# tar example
def cp_files(pod):
    with pod.popen("/bin/tar", "cf", "-", "/etc", stdout=True) as popen:
        with tarfile.TarFile.open(mode="r|", fileobj=popen.stdout) as archive:
            archive.extractall("/tmp/popen")


##################################################################
# Full TTY integration running top, uses local posix apis and raw i/o.
def top(pod):
    with pod.popen("/bin/top", tty=True, stdin=True, stdout=True) as popen:
        # Enable raw tty mode with no echoing or buffering
        stdin = sys.stdin.fileno()
        stdout = sys.stdout.fileno()
        tcattr = termios.tcgetattr(stdin)
        try:
            tty.setraw(stdin)
            size = None
            # Do non-blocking stdout reads
            popen.timeout = 0
            while True:
                resize = os.get_terminal_size()
                if (
                    not size
                    or resize.columns != size.columns
                    or resize.lines != size.lines
                ):
                    popen.resize(resize.columns, resize.lines)
                    size = resize
                    # Check if there is anything from our stdin
                r, _, _ = select.select([stdin], [], [], 0)
                if r:
                    # Read from our stdin
                    data = os.read(stdin, 1024)
                    # Write it to remote top's stdin
                    popen.stdin.write(data)
                try:
                    # Try to read from top's stdout
                    data = popen.stdout.read(1024)
                    # If a zero length data, then stdout has been closed
                    if not data:
                        # stdout was closed, now wait for top to finish.
                        break
                    # Write remote top's stdout to our stdout
                    os.write(stdout, data)
                except TimeoutError:
                    # Nothing from stdout available at this time
                    pass
        finally:
            # Restore the original tty attributes from raw mode
            termios.tcsetattr(stdin, termios.TCSANOW, tcattr)
        popen.timeout = None
        popen.wait()


def main():
    pod = provision_pod(kr8s.api())
    simple_response(pod)
    stdin_sent(pod)
    interactive(pod)
    cp_files(pod)
    top(pod)


if __name__ == "__main__":
    main()
