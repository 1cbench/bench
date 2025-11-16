from setuptools import setup, find_packages

setup(
    name="onec-syntax-parser",
    version="0.1.0",
    description="A syntax parser and type inference engine for 1C language",
    author="1C Bench Team",
    packages=find_packages(),
    install_requires=[
        # No external parser libraries - we're building from scratch
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "mypy>=1.5.0",
        ]
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
