from setuptools import setup
setup(
    name="vpnx-cli",
    version="2.0.0",
    description="VPN Proxy Exchange — CLI wrapper for the VPNX Docker container",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    py_modules=["vpnx_cli"],
    entry_points={"console_scripts": ["vpnx=vpnx_cli:main"]},
    python_requires=">=3.8",
    license="MIT",
    url="https://github.com/mocasus/vpnx",
    author="mocasus",
)
