from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

from nexgen_erp_reports import __version__ as version

setup(
    name="nexgen_erp_reports",
    version=version,
    description="Custom statutory and business reports for ERPNext",
    author="NexGen ERP Technologies",
    author_email="info@nexgenerptechnologies.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
