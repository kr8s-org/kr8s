#!/usr/bin/env python

# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

from ruamel.yaml import YAML

yaml = YAML(typ="rt")
yaml.width = 2**16
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)

DATE_FORMAT = "%Y-%m-%d"


def get_versions():
    print(
        "Loading Kubernetes versions from https://endoflife.date/api/kubernetes.json..."
    )
    with urllib.request.urlopen("https://endoflife.date/api/kubernetes.json") as url:
        data = json.load(url)
        data = [
            {
                "cycle": x["cycle"],
                "latest_version": x["latest"],
                "eol": datetime.strptime(x["eol"], DATE_FORMAT),
            }
            for x in data
            if datetime.strptime(x["eol"], DATE_FORMAT) > datetime.now()
        ]
        data.sort(key=lambda x: x["eol"], reverse=True)

    print("Loading Kubernetes tags from https://hub.docker.com/r/kindest/node/tags...")

    container_tags = []
    next_url = "https://hub.docker.com/v2/repositories/kindest/node/tags"
    while next_url:
        with urllib.request.urlopen(next_url) as url:
            results = json.load(url)
            container_tags += results["results"]
            if "next" in results and results["next"]:
                next_url = results["next"]
            else:
                next_url = None

    for version in data:
        try:
            version["latest_kind_container"] = [
                x["name"]
                for x in container_tags
                if version["cycle"] in x["name"] and "alpha" not in x["name"]
            ][0][1:]
        except IndexError:
            version["latest_kind_container"] = None

    before_length = len(data)
    print("Pruning versions that do not have a kind release yet...")
    data[:] = [x for x in data if x["latest_kind_container"] is not None]
    print(f"Pruned {before_length - len(data)} versions")
    return data


def update_workflow(versions, workflow_path):
    workflow_path = Path(workflow_path)
    workflow = yaml.load(workflow_path)
    workflow["jobs"]["test"]["strategy"]["matrix"]["kubernetes-version"][0] = versions[
        0
    ]["latest_kind_container"]
    workflow["jobs"]["test"]["strategy"]["matrix"]["include"] = []
    for version in versions[1:]:
        workflow["jobs"]["test"]["strategy"]["matrix"]["include"].append(
            {
                "python-version": "3.10",
                "kubernetes-version": version["latest_kind_container"],
            }
        )
    yaml.dump(workflow, workflow_path)


def update_badges(filename, versions):
    readme = Path(filename).read_text()
    # Use regex to replace the badge
    v = [x["cycle"] for x in versions]
    v.sort()
    version_list = "%7C".join(v)
    readme = re.sub(
        r"img.shields.io/badge/Kubernetes%20support.*-blue",
        f"img.shields.io/badge/Kubernetes%20support-{version_list}-blue",
        readme,
    )
    Path(filename).write_text(readme)


def main():
    versions = get_versions()
    print(f"Latest version: {versions[0]['cycle']}")
    print("Supported versions:")
    for version in versions:
        print(
            f"For {version['cycle']} using kindest/node {version['latest_kind_container']} until {version['eol']}"
        )

    update_workflow(versions, ".github/workflows/test-kr8s.yaml")
    update_workflow(versions, ".github/workflows/test-kubectl-ng.yaml")
    update_badges("README.md", versions)
    update_badges("docs/index.md", versions)


if __name__ == "__main__":
    main()
