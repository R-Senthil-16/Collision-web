from setuptools import setup, find_packages

setup(
    name="collision-detection-server",
    version="1.0.0",
    description="Raspberry Pi server for collision detection with computer vision and IoT control",
    author="Collision Detection Team",
    author_email="team@collisiondetection.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "Flask>=3.0.0",
        "Flask-SocketIO>=5.3.6",
        "Flask-CORS>=4.0.0",
        "opencv-python>=4.8.1",
        "numpy>=1.24.3",
        "torch>=2.1.1",
        "torchvision>=0.16.1",
        "ultralytics>=8.0.206",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "psutil>=5.9.6",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "hypothesis>=6.88.1",
            "pytest-mock>=3.12.0",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ]
    },
    entry_points={
        "console_scripts": [
            "collision-server=collision_server.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)