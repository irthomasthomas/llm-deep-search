from setuptools import setup, find_packages

setup(
    name='llm-search',
    version='0.1.0a1',  # Alpha version
    packages=find_packages(),
    install_requires=[],
    author='Your Name',
    author_email='your.email@example.com',
    description='A Python package for LLM-based search functionality',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/irthomasthomas/llm-search',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',  # Choose an appropriate license
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
