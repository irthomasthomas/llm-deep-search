from setuptools import setup, find_packages

setup(
    name="llm-websearch",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
        "beautifulsoup4>=4.9.0",
        "html2text>=2020.1.16",
        "pdfminer.six>=20200726",
        "diskcache>=5.2.1",
        "python-dotenv>=0.19.0",
        "requests-html>=0.10.0",
        "llm>=0.5.0",
    ],
    author="Thomas Thomas",
    author_email="irthomasthomas@gmail.com",
    description="A web search and analysis plugin for llm CLI",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/llm-websearch",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)
