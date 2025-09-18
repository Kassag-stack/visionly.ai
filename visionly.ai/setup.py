from setuptools import setup, find_packages

setup(
    name="backend_api",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "colorama",
        "fastapi",
        "uvicorn",
        "python-multipart",
        "python-dotenv",
        "pandas",
        "matplotlib",
        "seaborn",
        "textblob",
        "wordcloud",
        "numpy",
        "supabase"
    ],
    author="Visionly.ai",
    description="Backend API package for data analysis and insights",
    python_requires=">=3.8",
) 