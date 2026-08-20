from loguru import logger

log = logger.info


def weblog():
    """Currently the weblog CLI only runs the test case as this code is meant to run in server loop."""
    return test_weblog()


def test_weblog():
    return weblog_from_labels_dict(
        {
            "mc3": "Server URL: mc3.olsonsky.com | Minecraft Version: 1.21.11 | Modpack: NA | Mods: NA | Port: 25567 | Description: Simple minecraft world no mods. Joint this if in doubt. | Test: test"
        }
    )


def weblog_from_labels_dict(
    labels: dict[str, str],
    html_filepath: str = "/shared/volumes/html/index.html",
) -> str:
    """A tool for generating an html file that lists all the public
    exposed servers (Minecraft) via container labels.
    """

    log("Running with (kwarg, var, type):")
    log(("labels", labels, type(labels)))
    log(("html_filepath", html_filepath, type(html_filepath)))

    htmls = []
    for name in labels:
        label = labels[name]

        defaults = {
            "name": "",
            "Server URL": "",
            "Minecraft Version": "NA",
            "Modpack": "NA",
            "Mods": "NA",
            "Port": "NA",
            "Description": "NA",
        }

        ld = defaults.copy()

        ld["name"] = name
        for label_ in label.split("|"):
            label__ = label_.strip()

            kvs = label__.split(":")

            if len(kvs) != 2:
                raise ValueError(
                    f"Invalid html label pattern, use 'key: value | key: value' given: {label}'"
                )

            k, v = kvs[0], kvs[1]
            k, v = k.strip(), v.strip()

            ld[k] = v

        if ld["Server URL"] == "":
            raise ValueError(
                f"Invalid label pattern 'Server URL' required given {label}"
            )

        unlisted_kv_str = "\n".join(
            [
                f"                <li>{k}: {v}</li>"
                for k, v in ld.items()
                if k not in defaults
            ]
        )

        list_html = f"""<li>Server: {ld["name"]}
            <ul>
                <li>Server URL: <a href="{ld["Server URL"]}">{ld["Server URL"]}</a></li>
                <li>Minecraft Version: {ld["Minecraft Version"]}</li>
                <li>Modpack: {ld["Modpack"]}</li>
                <li>Mods: {ld["Mods"]}</li>
                <li>Port: {ld["Port"]}</li>
                <li>Description: {ld["Description"]}</li>{'\n' + unlisted_kv_str if unlisted_kv_str else ''}
            </ul>
        </li>"""

        htmls.append(list_html)

    htmls_insert = "\n".join(htmls)

    template_str = f"""
<!DOCTYPE html>
<html>

<head>
    <title>Olsonsky.com Minecraft Directory</title>
</head>

<body>

    <h2>Olsonsky.com Minecraft Directory</h2>

    <p>List of all running Minecraft Servers and required Minecraft Version and Mods.</p>

    <ul>
        {htmls_insert}
        <li>Server URL: <a href="mc2.olsonsky.com">mc2.olsonsky.com</a>
            <ul>
                <li>Minecraft Version: NA</li>
                <li>Modpack: <a
                        href="https://www.curseforge.com/minecraft/modpacks/fantasy-minecraft-fabric/files/7269069">https://www.curseforge.com/minecraft/modpacks/fantasy-minecraft-fabric/files/7269069</a>
                </li>
                <li>Mods: NA</li>
                <li>Port: 25566</li>
                <li>Description: Beta Fantisy modpack. Do not join unless instructed server is unstable.</li>
            </ul>
        </li>
        <li>Server URL: <a href="mc1.olsonsky.com">mc1.olsonsky.com</a>
            <ul>
                <li>Minecraft Version: 1.21.11</li>
                <li>Modpack: <a
                        href="https://www.curseforge.com/minecraft/modpacks/all-in-one-create/files/6251041">https://www.curseforge.com/minecraft/modpacks/all-in-one-create/files/6251041</a>
                </li>
                <li>Mods: NA</li>
                <li>Port: 25565</li>
                <li>Description: Modpack with lots of optional goodies. Stable Server.</li>
            </ul>
        </li>
    </ul>

</body>

</html>
"""

    return template_str
