# setup.py

import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    required = f.read().splitlines()

# Function to process requirements
def process_requirements(req_list):
    processed = []
    for req in req_list:
        if req.startswith('protobuf'):
            # Use a more flexible version for protobuf
            processed.append('protobuf>=3.19.5,<6.0.0.dev0')
        elif '==' in req:
            # Replace fixed versions with minimum versions
            package, version = req.split('==')
            processed.append(f'{package}>={version}')
        else:
            processed.append(req)
    return processed

setup(
    name="ella-ai",
    version="0.1.0",
    author="Greg Lindberg",
    author_email="greglindberg@gmail.com",
    description="AI Assistant",
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    url="https://github.com/glindberg2000/ella-ai",
    packages=find_packages(),
    install_requires=process_requirements(required),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires='>=3.7',
    # entry_points={
    #     'console_scripts': [
    #         'ella-ai=ella_ai.cli:main',
    #     ],
    # },
    include_package_data=True,
    package_data={
        'ella_ai': ['memgpt_tools/credentials/*.json'],
    },
)