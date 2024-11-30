# setup_nltk.py
import nltk

def download_nltk_data():
    """Download required NLTK data packages."""
    packages = [
        'punkt_tab',
        'stopwords',
        'wordnet',
        'averaged_perceptron_tagger'
    ]
    
    for package in packages:
        print(f"Downloading {package}...")
        nltk.download(package)

if __name__ == "__main__":
    download_nltk_data()