from setuptools import setup
setup(
    name="vpx",
    version="1.0.0",
    description="VPN Proxy Exchange",
    py_modules=["vpx_cli"],
    entry_points={"console_scripts": ["vpx=vpx_cli:main"]},
    python_requires=">=3.8",
)
