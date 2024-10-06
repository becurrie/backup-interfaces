from setuptools import find_packages, setup

setup(
    name="backup",
    version="0.0.1",
    description="A backup application for backing up files and directories using various configurable interfaces.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/becurrie/backup-interfaces",
    author="Brett Currie",
    author_email="brettecurrie@gmail.com",
    packages=find_packages(),
    install_requires=[
        "PyYAML==6.0.2",
        "python-dotenv==1.0.1",
        "azure-core==1.31.0",
        "azure-identity==1.18.0",
        "azure-keyvault-secrets==4.8.0",
        "azure-storage-blob==12.23.1",
        "paramiko==3.5.0",
        "pydantic==2.9.2",
        "tqdm==4.66.5",
    ],
    extras_require={
        "dev": [
            "pytest==8.3.3",
            "pytest-cov==5.0.0",
            "black==24.8.0",
            "isort==5.13.2",
            "Sphinx==7.4.7",
            "sphinx-rtd-theme==2.0.0",
            "autodoc_pydantic==2.2.0",
        ],
        "test": [
            "pytest==8.3.3",
            "pytest-cov==5.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "backup=backup.app.main:run",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
