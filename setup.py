from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in farm_i9/__init__.py
from farm_i9 import __version__ as version

setup(
    name="farm_i9",
    version=version,
    description="I-9 employment eligibility verification workflow for farm ERPNext installations. Configurable audit posture per farm.",
    author="Polehn Farm",
    author_email="polehntim@gmail.com",
    license="MIT",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
