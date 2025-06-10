import pandas as pd

class NSpostprocessor:
    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path

    def load_data(self):
        self.df = pd.read_csv(self.input_path)

    def clean_data(self):
        self.df = self.df[self.df['business_status'] != 'CLOSED_TEMPORARILY']
        self.df = self.df.dropna(subset=['lat', 'long', 'rating', 'reviews', 'business_status'])
        self.df = self.df[self.df['reviews'] >= 30]

    def save_cleaned_data(self):
        self.df.to_csv(self.output_path, index=False)

    def run(self):
        self.load_data()
        self.clean_data()
        self.save_cleaned_data()


if __name__ == "__main__" and "NSpostprocessor" in globals():
    import argparse

    parser = argparse.ArgumentParser(description="Run NSpostprocessor")
    parser.add_argument("--input", type=str, required=True, help="Input CSV path")
    parser.add_argument("--output", type=str, required=True, help="Output CSV path")

    args = parser.parse_args()
    processor = NSpostprocessor(input_path=args.input, output_path=args.output)
    processor.run()
