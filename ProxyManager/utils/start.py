import os
import subprocess


for i in os.listdir("./output/docker-compose"):
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            f"./output/docker-compose/{i}/docker-compose.yml",
            "up",
            "-d",
        ]
    )
