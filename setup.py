from setuptools import setup, find_packages

setup(
    name="lobster-cli",
    version="1.1.0",
    description="Lobster - 低Token AI自动化执行系统 CLI + MCP",
    packages=find_packages(include=["cli*"]),
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "lobster=cli.lobster:main",
            "lobster-mcp=cli.lobster_mcp:main",
        ],
    },
)
