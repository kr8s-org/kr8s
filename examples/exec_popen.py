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
  stdin      - if enabled, an anyio.ByteSendStream
  stdout     - if enabled, an anyio.ByteReceiveStream
  stderr     - if enabled, an anyio.ByteReceiveStream
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
import termios
import time
import tty

import anyio

import kr8s


##############################################################################
# Provision the test pod
async def provision_pod(api):
    pod = await kr8s.asyncio.objects.Pod("busybox-example", "default", api)
    if await pod.exists():
        await pod.refresh()
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
        await pod.create()
        while not await pod.ready():
            await anyio.sleep(1)
        print("Done.")
    return pod


##################################################################
# Calling exec and waiting for response
async def simple_response(pod):
    command = [
        "/bin/sh",
        "-c",
        "echo This message goes to stdout;echo This message goes to stderr >&2",
    ]

    ex = await pod.exec(command)
    print(f"STDOUT: {ex.stdout.decode()}", end="", flush=True)
    print(f"STDERR: {ex.stderr.decode()}", end="", flush=True)

    async with pod.popen(*command, text=True, stdout=True, stderr=True) as popen:
        stdout, stderr = await popen.communicate()
    print(f"STDOUT: {stdout}", end="", flush=True)
    print(f"STDERR: {stderr}", end="", flush=True)


##################################################################
# stdin handling
async def stdin_sent(pod):
    async with pod.popen(
        "sh",
        "-c",
        'printf ">>>";cat;printf "<<<"',
        text=True,
        stdin=True,
        stdout=True,
        stderr=True,
    ) as popen:
        stdout, stderr = await popen.communicate("test")
    print(f"STDOUT: {stdout}", flush=True)
    if stderr:
        print(f"STDERR: {stderr}", flush=True)


##################################################################
# Calling a process interactively
async def interactive(pod):
    async with pod.popen(
        "/bin/sh", text=True, stdin=True, stdout=True, stderr=True
    ) as popen:
        commands = [
            "echo This message goes to stdout",
            "echo This message goes to stderr >&2",
        ]
        # Do non-blocking stdout and stderr reads.
        popen.timeout = 0
        while commands and not popen.closed:
            line = commands.pop(0)
            print("Running command... %s" % line, flush=True)
            await popen.stdin.send(line + "\n")
            time.sleep(1)
            try:
                line = await popen.stdout.receive()
                print("STDOUT: %s" % line, end="", flush=True)
            except TimeoutError:
                pass
            try:
                line = await popen.stderr.receive()
                print("STERR: %s" % line, end="", flush=True)
            except TimeoutError:
                pass
        popen.timeout = 3
        await popen.stdin.send("date\n")
        line = await popen.stdout.receive()
        print("Server date command returns: %s" % line, end="", flush=True)
        popen.timeout = 3
        await popen.stdin.send("whoami\n")
        line = await popen.stdout.receive()
        print("Server user is: %s" % line, end="", flush=True)


##################################################################
# Full TTY integration running top, uses local posix apis and raw i/o.
#
# There is probably a better way to handle stdin and resize using anyio.


async def top(pod):

    async def stdin_handler(popen, stdin):
        while not popen.closed:
            # Check if there is anything from our stdin
            r, _, _ = select.select([stdin], [], [], 0)
            if r:
                # Read from our stdin
                data = os.read(stdin, 1024)
                # Write it to remote top's stdin
                await popen.stdin.send(data)
            await anyio.sleep(0)

    async def stdout_handler(popen):
        stdout = sys.stdout.fileno()
        async for data in popen.stdout:
            os.write(stdout, data)

    async def resize_handler(popen):
        size = None
        while not popen.closed:
            resize = os.get_terminal_size()
            if not size or resize.columns != size.columns or resize.lines != size.lines:
                # Inform remote top of the size of the terminal.
                await popen.resize(resize.columns, resize.lines)
                size = resize
            await anyio.sleep(0)

    async with pod.popen("/bin/top", tty=True, stdin=True, stdout=True) as popen:
        # Enable raw tty mode with no echoing or buffering
        stdin = sys.stdin.fileno()
        tcattr = termios.tcgetattr(stdin)
        tty.setraw(stdin)
        try:
            async with anyio.create_task_group() as group:
                group.start_soon(stdin_handler, popen, stdin)
                group.start_soon(stdout_handler, popen)
                group.start_soon(resize_handler, popen)
            await popen.wait()
        finally:
            # Restore the original tty attributes from raw mode
            termios.tcsetattr(stdin, termios.TCSANOW, tcattr)


async def main():
    pod = await provision_pod(await kr8s.asyncio.api())
    await simple_response(pod)
    await stdin_sent(pod)
    await interactive(pod)
    await top(pod)


if __name__ == "__main__":
    anyio.run(main)
