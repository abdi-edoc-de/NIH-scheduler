from setuptools import setup, find_packages

setup(
    name="scheduler",
    version="0.1.1",
    packages=find_packages(),
    install_requires=[
        "SQLAlchemy==2.0.35"],
    entry_points={
        'console_scripts': [
            'scheduler=mytool.main:main',  # This sets 'scheduler' as the command
        ],
    },
    description="A tool to run scheduled jobs",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author="Abdulfeta Yusuf",
    author_email="abdulfeta.yusuff@example.com",
    url="https://github.com/abdi-edoc-de/scheduler",
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
