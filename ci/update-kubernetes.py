#!/usr/bin/env python

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
                "version": x["latest"],
                "eol": datetime.strptime(x["eol"], DATE_FORMAT),
            }
            for x in data
            if datetime.strptime(x["eol"], DATE_FORMAT) > datetime.now()
        ]
        data.sort(key=lambda x: x["eol"], reverse=True)
        return data


def update_test_workflow(versions):
    workflow = yaml.load(Path(".github/workflows/test.yaml"))
    workflow["jobs"]["test"]["strategy"]["matrix"]["kubernetes-version"][0] = versions[
        0
    ]["version"]
    workflow["jobs"]["test"]["strategy"]["matrix"]["include"] = []
    for version in versions[1:]:
        workflow["jobs"]["test"]["strategy"]["matrix"]["include"].append(
            {"python-version": "3.10", "kubernetes-version": version["version"]}
        )
    yaml.dump(workflow, Path(".github/workflows/test.yaml"))


def update_readme_badge(versions):
    readme = Path("README.md").read_text()
    # Use regex to replace the badge
    v = [x["cycle"] for x in versions]
    v.sort()
    version_list = "%7C".join(v)
    readme = re.sub(
        r"img.shields.io/badge/Kubernetes%20support.*-blue",
        f"img.shields.io/badge/Kubernetes%20support-{version_list}-blue",
        readme,
    )
    Path("README.md").write_text(readme)


def main():
    versions = get_versions()
    print(f"Latest version: {versions[0]['version']}")
    print("Supported versions:")
    for version in versions:
        print(f"{version['version']} until {version['eol']}")

    update_test_workflow(versions)
    update_readme_badge(versions)


if __name__ == "__main__":
    main()
